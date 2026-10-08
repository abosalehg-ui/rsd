"""رصد - جامع أسعار الطاقة والأسواق من FRED (بنك الاحتياطي الفيدرالي في سانت لويس).

أربع سلاسل يومية: برنت، غرب تكساس، غاز هنري هب، ومؤشر التقلّب VIX. FRED
ينشرها بعد إغلاق يوم التداول بيوم أو أكثر، فهي **ليست لحظية**: كل قيمة
تُخزَّن بتاريخ ملاحظتها لا بوقت جلبها، والواجهة تعرض ذلك التاريخ صراحةً.

المفتاح اختياري مثل NewsAPI: بلا `FRED_API_KEY` يُتخطّى الجامع بسطر سجل
واحد، وتبقى آخر القيم المخزّنة تُعرض من قاعدة البيانات (دون اتصال أيضًا).

الطلب يحمل المفتاح في معاملات الرابط، ونصّ استثناءات httpx يتضمّن الرابط
كاملًا — لذلك لا نسجّل الاستثناء الخام أبدًا، بل نوعه وحالة HTTP فقط.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

import httpx
from sqlalchemy import func, select, update

from ..config import get_settings
from ..models.database import MarketQuote, get_session_factory

logger = logging.getLogger("rasad.markets")

FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"

#: السلاسل المجموعة بترتيب العرض. الأسماء المعروضة في ملفات الترجمة
#: (`markets.series.<code>`)؛ هنا الوحدة وحدها لأنها جزء من البيانات.
SERIES: dict[str, dict] = {
    "DCOILBRENTEU": {"unit": "USD/bbl"},
    "DCOILWTICO": {"unit": "USD/bbl"},
    "DHHNGSP": {"unit": "USD/MMBtu"},
    "VIXCLS": {"unit": "index"},
}
BRENT = "DCOILBRENTEU"

#: نعيد جلب أيام قليلة قبل آخر قيمة مخزّنة: FRED يراجع القيم الأخيرة أحيانًا،
#: ويوم العطلة الذي نُشر متأخرًا يُلتقط في الجلب التالي.
REFETCH_OVERLAP_DAYS = 7


def parse_observation(raw: dict) -> tuple[date, float] | None:
    """ملاحظة FRED → (التاريخ، القيمة)، أو None لما لا يُخزَّن.

    FRED يضع "." مكان القيمة في أيام بلا تداول (عطل) — ليست صفرًا. ونرفض أي
    قيمة غير رقمية أو غير منتهية أو تاريخًا مشوّهًا بدل إسقاط الدفعة كلها.
    """
    raw_value = str(raw.get("value", "")).strip()
    if raw_value in ("", "."):
        return None
    try:
        value = float(raw_value)
        observed = date.fromisoformat(str(raw.get("date", ""))[:10])
    except (TypeError, ValueError):
        return None
    if value != value or value in (float("inf"), float("-inf")):
        return None
    return observed, value


def _upsert_insert(dialect_name: str):
    if dialect_name == "sqlite":
        from sqlalchemy.dialects.sqlite import insert

        return insert
    if dialect_name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert

        return insert
    return None


async def upsert_quotes(session, code: str, rows: list[tuple[date, float]]) -> int:
    """يكتب القيم بلا تكرار على (code, observed_at) ويحدّث القيمة المراجَعة.

    يعيد عدد التواريخ **الجديدة** (لا المحدّثة) — هو ما يعنيه «جديد» في السجل.
    """
    if not rows:
        return 0
    # آخر قيمة لكل تاريخ إن تكرّر في الاستجابة نفسها
    by_date = dict(rows)
    now = datetime.now(timezone.utc)
    existing = set((await session.execute(
        select(MarketQuote.observed_at).where(
            MarketQuote.code == code, MarketQuote.observed_at.in_(list(by_date)),
        )
    )).scalars().all())

    dialect = session.bind.dialect.name if session.bind is not None else "sqlite"
    insert_fn = _upsert_insert(dialect)
    if insert_fn is not None:
        stmt = insert_fn(MarketQuote).values([
            {"code": code, "observed_at": d, "value": v, "fetched_at": now}
            for d, v in by_date.items()
        ])
        stmt = stmt.on_conflict_do_update(
            index_elements=["code", "observed_at"],
            set_={"value": stmt.excluded.value, "fetched_at": stmt.excluded.fetched_at},
        )
        await session.execute(stmt)
    else:  # pragma: no cover - محرّكات غير SQLite/PostgreSQL
        for d, v in by_date.items():
            if d in existing:
                await session.execute(
                    update(MarketQuote)
                    .where(MarketQuote.code == code, MarketQuote.observed_at == d)
                    .values(value=v, fetched_at=now)
                )
            else:
                session.add(MarketQuote(code=code, observed_at=d, value=v, fetched_at=now))
    return sum(1 for d in by_date if d not in existing)


async def _observation_start(session, code: str, retention_days: int) -> date:
    """من أين نطلب: قبل آخر قيمة مخزّنة بأيام قليلة، وإلا نافذة الاحتفاظ كاملة
    (أول تشغيل) — لا أقدم منها، فما يُجلب أقدم يحذفه المنظّف في يومه."""
    floor = (datetime.now(timezone.utc) - timedelta(days=retention_days)).date()
    latest = (await session.execute(
        select(func.max(MarketQuote.observed_at)).where(MarketQuote.code == code)
    )).scalar()
    if latest is None:
        return floor
    return max(floor, latest - timedelta(days=REFETCH_OVERLAP_DAYS))


async def _fetch_series(client: httpx.AsyncClient, code: str, api_key: str, start: date) -> list[dict]:
    response = await client.get(FRED_OBSERVATIONS_URL, params={
        "series_id": code,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start.isoformat(),
    })
    if response.status_code in (400, 401, 403):
        # FRED يردّ 400 على مفتاح غير مسجّل — لا نعيد رسالته (قد تحوي المفتاح)
        raise PermissionError(f"FRED: الطلب مرفوض ({response.status_code}) — تحقّق من FRED_API_KEY")
    if response.status_code != 200:
        raise RuntimeError(f"FRED: HTTP {response.status_code}")
    try:
        body = response.json()
    except ValueError as e:
        raise RuntimeError("FRED: استجابة ليست JSON") from e
    observations = body.get("observations") if isinstance(body, dict) else None
    return observations if isinstance(observations, list) else []


async def collect_markets() -> int:
    """يجلب السلاسل الأربع ويخزّنها. يعيد عدد القيم اليومية الجديدة.

    بلا مفتاح يعيد 0 دون أي طلب. فشل سلسلة واحدة لا يُسقط البقية؛ وإن فشلت
    كلها (أو رُفض المفتاح) يرفع استثناءً كي يُميَّز الفشل من «لا جديد».
    """
    settings = get_settings()
    if not settings.fred_api_key:
        logger.info("FRED: لا مفتاح (FRED_API_KEY) — جامع الأسواق متخطّى")
        return 0

    session_factory = get_session_factory()
    if not session_factory:
        return 0

    new_rows = 0
    failures = 0
    async with httpx.AsyncClient(timeout=30.0) as client:
        async with session_factory() as session:
            for code in SERIES:
                try:
                    start = await _observation_start(session, code, settings.retention_markets_days)
                    raw = await _fetch_series(client, code, settings.fred_api_key, start)
                except PermissionError:
                    raise  # مفتاح مرفوض: كل السلاسل ستفشل بالسبب نفسه
                except (httpx.HTTPError, RuntimeError) as e:
                    # نوع الاستثناء لا نصّه: نصّ httpx يحمل الرابط بمفتاحه
                    failures += 1
                    logger.warning("FRED: تعذّر جلب %s (%s)", code, type(e).__name__)
                    continue
                parsed = [p for p in (parse_observation(o) for o in raw if isinstance(o, dict)) if p]
                new_rows += await upsert_quotes(session, code, parsed)
            await session.commit()

    if failures == len(SERIES):
        raise RuntimeError("FRED: تعذّر جلب كل السلاسل")
    logger.info("FRED: %s قيمة يومية جديدة", new_rows)
    return new_rows
