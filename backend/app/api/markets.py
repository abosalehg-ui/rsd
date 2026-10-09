"""رصد - نقاط API لشريط الطاقة والأسواق ومخطط التزامن.

- `/latest`       آخر قيمة وسابقتها والتغيّر وتاريخ الملاحظة لكل سلسلة
- `/series`       السلاسل اليومية لعدد من الأيام (للخطوط المصغّرة)
- `/correlation`  مؤشر الخطر النووي ومؤشر الأثر على المملكة يومًا بيوم،
                  مصفوفين مع برنت على التواريخ نفسها

كل شيء يُقرأ من قاعدة البيانات لا من FRED، فآخر القيم المعروفة تُعرض دون
اتصال وبلا مفتاح. `enabled` يخبر الواجهة هل الجامع مفعّل (FRED_API_KEY)
فتعرض تلميح التفعيل بدل شريط فارغ بلا تفسير.

**قراءة تزامن لا تنبؤ:** معامل الارتباط في `/correlation` وصفي على أيام
النافذة، لا يدلّ على سببية ولا يُبنى عليه قرار مالي. المنهجية وحدودها:
docs/markets-sync-methodology.md.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import and_, desc, func, select

from .. import cache
from ..config import get_settings
from ..models.database import Event, MarketQuote, get_session_factory
from ..processors.impact_index import load_impact_rows
from ..processors.impact_index import snapshot as impact_snapshot
from ..processors.markets import BRENT, MIN_CORRELATION_DAYS, SERIES, pearson
from .nuclear import NUCLEAR_CATEGORIES, risk_snapshot

router = APIRouter(prefix="/api/markets", tags=["markets"])

SOURCE = {"name": "FRED", "publisher": "Federal Reserve Bank of St. Louis", "url": "https://fred.stlouisfed.org/"}
_MAX_DAYS = 400


def _iso(d: date | datetime | None) -> str | None:
    if d is None:
        return None
    if isinstance(d, datetime) and d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.isoformat()


def _change(value: float, prev: float | None) -> tuple[float | None, float | None]:
    if prev is None:
        return None, None
    change = round(value - prev, 4)
    pct = round(change / prev * 100, 2) if prev else None
    return change, pct


@router.get("/latest")
async def markets_latest():
    """آخر قيمة لكل سلسلة مع سابقتها ونسبة التغيّر وتاريخ الملاحظة.

    `observed_at` تاريخ يوم التداول كما ينشره FRED (يتأخّر يومًا أو أكثر)،
    و`fetched_at` وقت آخر جلب — لا تُعرض أيٌّ منهما على أنها «الآن».
    """
    settings = get_settings()
    series = []
    async with get_session_factory()() as session:
        for code, meta in SERIES.items():
            rows = (await session.execute(
                select(MarketQuote)
                .where(MarketQuote.code == code)
                .order_by(desc(MarketQuote.observed_at))
                .limit(2)
            )).scalars().all()
            item = {
                "code": code,
                "unit": meta["unit"],
                "value": None,
                "observed_at": None,
                "prev_value": None,
                "prev_observed_at": None,
                "change": None,
                "change_pct": None,
                "fetched_at": None,
            }
            if rows:
                last, prev = rows[0], (rows[1] if len(rows) > 1 else None)
                change, pct = _change(last.value, prev.value if prev else None)
                item.update({
                    "value": last.value,
                    "observed_at": _iso(last.observed_at),
                    "prev_value": prev.value if prev else None,
                    "prev_observed_at": _iso(prev.observed_at) if prev else None,
                    "change": change,
                    "change_pct": pct,
                    "fetched_at": _iso(last.fetched_at),
                })
            series.append(item)

    dates = [s["observed_at"] for s in series if s["observed_at"]]
    fetched = [s["fetched_at"] for s in series if s["fetched_at"]]
    return {
        "enabled": bool(settings.fred_api_key),
        "has_data": bool(dates),
        "as_of": max(dates) if dates else None,
        "fetched_at": max(fetched) if fetched else None,
        "frequency": "daily",
        "source": SOURCE,
        "series": series,
    }


def _parse_codes(codes: str | None) -> list[str]:
    if not codes:
        return list(SERIES)
    wanted = [c.strip().upper() for c in codes.split(",") if c.strip()]
    unknown = [c for c in wanted if c not in SERIES]
    if unknown:
        raise HTTPException(status_code=400, detail=f"سلاسل غير معروفة: {', '.join(unknown)}")
    # بلا تكرار وبترتيب الطلب
    return list(dict.fromkeys(wanted))


async def _load_quotes(session, codes: list[str], start: date) -> dict[str, dict[date, float]]:
    rows = (await session.execute(
        select(MarketQuote.code, MarketQuote.observed_at, MarketQuote.value)
        .where(and_(MarketQuote.code.in_(codes), MarketQuote.observed_at >= start))
        .order_by(MarketQuote.observed_at)
    )).all()
    out: dict[str, dict[date, float]] = {c: {} for c in codes}
    for code, observed, value in rows:
        out[code][observed] = value
    return out


@router.get("/series")
async def markets_series(
    codes: str | None = Query(default=None, max_length=200, description="رموز مفصولة بفواصل، مثل DCOILBRENTEU,VIXCLS"),
    days: int = Query(default=90, ge=1, le=_MAX_DAYS),
):
    """القيم اليومية لكل سلسلة خلال آخر `days` يومًا (أيام التداول فقط)."""
    wanted = _parse_codes(codes)
    start = (datetime.now(timezone.utc) - timedelta(days=days)).date()
    async with get_session_factory()() as session:
        quotes = await _load_quotes(session, wanted, start)
    return {
        "days": days,
        "series": {
            code: [{"date": d.isoformat(), "value": v} for d, v in sorted(values.items())]
            for code, values in quotes.items()
        },
    }


class _NuclearRow:
    """صفّ خفيف بما يحتاجه `risk_snapshot` (الممثّل والخطر) دون نص الحدث."""

    __slots__ = ("id", "cluster_id", "event_date", "risk_score", "severity")

    def __init__(self, id_, cluster_id, event_date, risk_score, severity):
        self.id = id_
        self.cluster_id = cluster_id
        self.event_date = event_date
        self.risk_score = risk_score
        self.severity = severity


def _utc_day(dt: datetime | None) -> date | None:
    if dt is None:
        return None
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).astimezone(timezone.utc).date()


def _first_full_day(dt: datetime) -> date:
    """أول يوم UTC رُصد كاملًا منذ `dt`."""
    day = _utc_day(dt)
    aware = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    midnight = datetime.combine(day, time.min, tzinfo=timezone.utc)
    return day if aware.astimezone(timezone.utc) == midnight else day + timedelta(days=1)


def _pair(points: list[dict], key: str) -> dict:
    both = [(p[key], p["brent"]) for p in points if p[key] is not None and p["brent"] is not None]
    return {
        "r": pearson([a for a, _ in both], [b for _, b in both]),
        "n": len(both),
    }


async def build_correlation(days: int, now: datetime | None = None) -> dict:
    """سلسلة يومية: المؤشران محسوبان على أحداث كل يوم (UTC) وحده — أي القيمة
    التي كان مؤشر الـ24 ساعة سيعرضها في نهاية ذلك اليوم — مع برنت بتاريخه.

    الأيام قبل أول يوم جمع كامل (أو قبل نافذة احتفاظ الأحداث) تُعاد `null`
    لا صفرًا: غياب البيانات ليس «لا خطر». وبرنت `null` في أيام بلا تداول.
    """
    now = now or datetime.now(timezone.utc)
    today = now.date()
    first_day = today - timedelta(days=days - 1)
    since = datetime.combine(first_day, time.min, tzinfo=timezone.utc)
    retention_floor = today - timedelta(days=get_settings().retention_events_days)

    async with get_session_factory()() as session:
        nuclear_rows = [
            _NuclearRow(*r) for r in (await session.execute(
                select(Event.id, Event.cluster_id, Event.event_date, Event.risk_score, Event.severity)
                .where(and_(
                    Event.event_date >= since, Event.event_date <= now,
                    Event.category.in_(NUCLEAR_CATEGORIES),
                ))
            )).all()
        ]
        impact_rows, _ = await load_impact_rows(session, since, now, story_level=False, cap=None)
        # بداية الجمع لا أقدم تاريخ حدث: حدث UCDP أو GDELT مؤرَّخ قبل التثبيت
        # بأسابيع لا يجعل تلك الأسابيع «مرصودة» بصفر خطر
        first_collected = (await session.execute(select(func.min(Event.collected_at)))).scalar()
        brent = (await _load_quotes(session, [BRENT], first_day))[BRENT]

    # يوم الحدّ نفسه محذوف جزئيًا (القطع عند ساعة التشغيل لا منتصف الليل)،
    # وكذلك يوم بدء الجمع إن لم يبدأ عند منتصف الليل — فالتغطية تبدأ بعدهما
    first_day_collected = _utc_day(first_collected)
    coverage_start = (
        max(retention_floor + timedelta(days=1), _first_full_day(first_collected))
        if first_day_collected else None
    )

    nuclear_by_day: dict[date, list] = {}
    for r in nuclear_rows:
        nuclear_by_day.setdefault(_utc_day(r.event_date), []).append(r)
    impact_by_day: dict[date, list] = {}
    for r in impact_rows:
        impact_by_day.setdefault(_utc_day(r.date), []).append(r)

    points = []
    for i in range(days):
        d = first_day + timedelta(days=i)
        covered = coverage_start is not None and d >= coverage_start
        points.append({
            "date": d.isoformat(),
            "nuclear": risk_snapshot(nuclear_by_day.get(d, []))["index"] if covered else None,
            "ksa": impact_snapshot(impact_by_day.get(d, []))["index"] if covered else None,
            "brent": brent.get(d),
            # اليوم الجاري لم يكتمل: مؤشراه جزئيان
            "partial": d == today,
        })

    brent_dates = sorted(brent)
    return {
        "days": days,
        "generated_at": now.isoformat(),
        "coverage_start": coverage_start.isoformat() if coverage_start else None,
        "brent_as_of": brent_dates[-1].isoformat() if brent_dates else None,
        "brent_code": BRENT,
        "points": points,
        "correlation": {
            "nuclear_brent": _pair(points, "nuclear"),
            "ksa_brent": _pair(points, "ksa"),
            "min_days": MIN_CORRELATION_DAYS,
        },
    }


@router.get("/correlation")
async def markets_correlation(days: int = Query(default=30, ge=7, le=90)):
    """مؤشر الخطر النووي ومؤشر الأثر على المملكة مقابل برنت يومًا بيوم.

    قراءة تزامن وليست تنبؤًا ولا نصيحة مالية.
    """
    ttl = get_settings().response_cache_seconds
    return await cache.cached(("markets.correlation", days), ttl, lambda: build_correlation(days))
