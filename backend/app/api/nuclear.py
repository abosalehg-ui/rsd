"""رصد - نقاط API للرصد النووي والإشعاعي.

- `/facilities`        المنشآت + المسافة إلى المملكة + مسافات التخطيط للطوارئ
- `/facilities/watch`  المنشآت المذكورة في الأخبار خلال الفترة، مرتّبة بالخطر
- `/events`            الأخبار النووية والإشعاعية مطويّة في قصص
- `/risk`              مؤشر المخاطر النووية والإشعاعية مع مكوّناته واتجاهه
- `/brief`             التقرير الدوري (يومي افتراضًا) — بيانات منظّمة تعرضها
                       الواجهة وتصدّرها
- `/topics`            الموضوعات وأوزانها (لشرح المؤشر في الواجهة)

المؤشر مُعرَّف في `risk_snapshot`: 60% أعلى خطر منفرد + 40% متوسط أعلى خمس
قصص، محسوب على ممثّلي القصص (الخبر المكرّر من عشرة مصادر يُعدّ مرة).
"""
import json
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import and_, desc, or_, select

from .. import cache
from ..config import get_settings
from ..models.database import Event, get_session_factory
from ..processors.dates import as_utc
from ..processors.gazetteer import ksa_point_en, nearest_ksa_point
from ..processors.nuclear import TOPICS, severity_from_score
from ._serializers import serialize_event
from ._stories import collapse, representatives
from .chains import build_chains
from .impact import build_ksa_impact

router = APIRouter(prefix="/api/nuclear", tags=["nuclear"])

_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "nuclear_facilities.json"

NUCLEAR_CATEGORIES = ("nuclear", "radiological")

# مسافات التخطيط الاسترشادية لمحطات القوى (مفاعلات > 1000 ميغاواط حراري) وفق
# IAEA EPR-NPP Public Protective Actions (2013). مرجعية للعرض فقط — المسافات
# المعتمدة لكل محطة تحددها خطة الطوارئ الوطنية الخاصة بها.
PLANNING_ZONES = (
    {"key": "PAZ", "km": 5},     # منطقة الإجراءات الوقائية العاجلة
    {"key": "UPZ", "km": 30},    # منطقة التخطيط للإجراءات الوقائية العاجلة
    {"key": "EPD", "km": 100},   # مسافة التخطيط الممتدة
    {"key": "ICPD", "km": 300},  # مسافة التخطيط للأغذية والسلع
)

RISK_MAX_WEIGHT = 0.6
RISK_TOP_WEIGHT = 0.4
RISK_TOP_N = 5
_SERIES_BUCKETS = 12

# موضوعات تُعدّ «تطورات سياسية» و«حوادث إشعاعية/أمان» في التقرير
BRIEF_CHAINS = 3
BRIEF_TOP_KSA = 3

POLITICAL_TOPICS = ("diplomacy_sanctions", "safeguards_iaea", "weapons_program", "military_threat")
INCIDENT_TOPICS = ("radiation_release", "radioactive_source", "safety_incident", "trafficking_security")


@lru_cache(maxsize=1)
def _load_data() -> dict:
    with _DATA_FILE.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def _enrich_facility(fac: dict) -> dict:
    out = dict(fac)
    near = nearest_ksa_point(fac.get("latitude"), fac.get("longitude"))
    if near:
        out["distance_to_ksa_km"], out["nearest_ksa_point"] = near
        out["nearest_ksa_point_en"] = ksa_point_en(near[1])
    out["planning_zones"] = list(PLANNING_ZONES) if fac.get("type") == "power" else []
    return out


def _facilities() -> list[dict]:
    return [_enrich_facility(f) for f in _load_data().get("facilities", [])]


@router.get("/facilities")
async def list_facilities(
    country: Optional[str] = Query(default=None, max_length=10, description="ISO country code, e.g. IR"),
    facility_type: Optional[str] = Query(default=None, max_length=20, description="power|research|enrichment|conversion|heavy_water|fuel"),
    status: Optional[str] = Query(default=None, max_length=20, description="operational|construction|planned|shutdown|modified"),
):
    """قائمة المنشآت النووية مع المسافة إلى أقرب نقطة سعودية ومسافات التخطيط."""
    facilities = _facilities()

    if country:
        cc = country.upper()
        facilities = [f for f in facilities if f.get("country_code") == cc]
    if facility_type:
        facilities = [f for f in facilities if f.get("type") == facility_type]
    if status:
        facilities = [f for f in facilities if f.get("status") == status]

    return {
        "total": len(facilities),
        "meta": {**_load_data().get("_meta", {}), "planning_zones_reference": "IAEA EPR-NPP 2013"},
        "facilities": facilities,
    }


# سقف الأخبار المحمَّلة لكل فترة. يُقصّ الأقدم، والقصّ يُعلَن في الرد (`truncated`)
# كي لا يُقرأ مؤشر جزئي على أنه كامل.
_ROW_CAP = 3000


class NuclearRow:
    """صفّ خفيف بما يحتاجه المؤشر — الممثّل والخطر (`risk_snapshot`)، والسلسلة،
    والتوزيع حسب الموضوع، والقرب من المملكة — دون نص الحدث ولا extra_data.
    يستعمله `/risk` والتزامن اليومي (`api/markets`)."""

    __slots__ = ("id", "cluster_id", "event_date", "risk_score", "severity", "topic", "latitude", "longitude")

    def __init__(self, id_, cluster_id, event_date, risk_score, severity, topic=None, latitude=None, longitude=None):
        self.id = id_
        self.cluster_id = cluster_id
        self.event_date = event_date
        self.risk_score = risk_score
        self.severity = severity
        self.topic = topic
        self.latitude = latitude
        self.longitude = longitude


ROW_COLUMNS = (
    Event.id, Event.cluster_id, Event.event_date, Event.risk_score, Event.severity,
    Event.topic, Event.latitude, Event.longitude,
)


def _window(since, until=None, topic: str | None = None):
    conds = [Event.event_date >= since, Event.category.in_(NUCLEAR_CATEGORIES)]
    if until is not None:
        conds.append(Event.event_date < until)
    if topic:
        conds.append(Event.topic == topic)
    return and_(*conds)


async def _nuclear_events(session, since, until=None, topic: str | None = None) -> tuple[list[Event], bool]:
    """(الأخبار كاملة، هل قُصّت) — للقصص المسلسلة ورصد المنشآت."""
    rows = list((await session.execute(
        select(Event).where(_window(since, until, topic)).order_by(desc(Event.event_date)).limit(_ROW_CAP + 1)
    )).scalars().all())
    return rows[:_ROW_CAP], len(rows) > _ROW_CAP


async def _nuclear_rows(session, since, until=None) -> tuple[list[NuclearRow], bool]:
    """(صفوف خفيفة، هل قُصّت) — لحساب المؤشر بلا تحميل نصوص الأخبار."""
    rows = (await session.execute(
        select(*ROW_COLUMNS).where(_window(since, until)).order_by(desc(Event.event_date)).limit(_ROW_CAP + 1)
    )).all()
    return [NuclearRow(*r) for r in rows[:_ROW_CAP]], len(rows) > _ROW_CAP


def _comparable(prev_since: datetime, now: datetime) -> bool:
    """الفترة السابقة داخل نافذة الاحتفاظ؟ إن لم تكن فبياناتها محذوفة لا «صفر
    خطر»، ومقارنتها بالحالية تعلن صعودًا كاذبًا (المنطق نفسه في `api/impact`)."""
    return prev_since >= now - timedelta(days=get_settings().retention_events_days)


@router.get("/facilities/watch")
async def facilities_watch(hours: int = Query(default=168, ge=1, le=720)):
    """المنشآت التي ورد ذكرها في الأخبار خلال الفترة، الأعلى خطرًا أولًا."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    async with get_session_factory()() as session:
        events, truncated = await _nuclear_events(session, since)
    return {"period_hours": hours, "truncated": truncated, "facilities": _facility_watch(events)}


def _facility_watch(events: list[Event]) -> list[dict]:
    """المنشآت المذكورة بالاسم في `events` مرتّبة بالخطر — منطق مشترك بين
    `/facilities/watch` و`/brief` (الأخير يمرّر أحداثًا محمّلة مسبقًا بدل أن
    يستدعي مسارًا كدالة)."""
    by_fac: dict[str, list[Event]] = {}
    for e in events:
        if e.facility_id:
            by_fac.setdefault(e.facility_id, []).append(e)

    facilities = {f["id"]: f for f in _facilities()}
    watch = []
    for fid, evs in by_fac.items():
        fac = facilities.get(fid)
        if not fac:
            continue
        reps = representatives(evs)
        top = max(reps, key=lambda e: e.risk_score or 0)
        watch.append({
            "facility_id": fid,
            "name_ar": fac.get("name_ar"),
            "name_en": fac.get("name_en"),
            "country_code": fac.get("country_code"),
            "type": fac.get("type"),
            "status": fac.get("status"),
            "latitude": fac.get("latitude"),
            "longitude": fac.get("longitude"),
            "distance_to_ksa_km": fac.get("distance_to_ksa_km"),
            "nearest_ksa_point": fac.get("nearest_ksa_point"),
            "nearest_ksa_point_en": fac.get("nearest_ksa_point_en"),
            "mentions": len(evs),
            "stories": len(reps),
            "max_risk": top.risk_score or 0,
            "top_event": serialize_event(top),
        })
    watch.sort(key=lambda w: (w["max_risk"], w["stories"]), reverse=True)
    return watch


@router.get("/facilities/{facility_id}")
async def get_facility(facility_id: str):
    """تفاصيل منشأة نووية محددة"""
    for facility in _facilities():
        if facility.get("id") == facility_id:
            return facility
    # 404 صريح لا {"error": ...} بحالة 200 يظنّها العميل نجاحاً
    raise HTTPException(status_code=404, detail=f"منشأة غير موجودة: {facility_id}")


@router.get("/stats")
async def nuclear_stats():
    """إحصائيات إجمالية للمنشآت النووية"""
    data = _load_data()
    facilities = data.get("facilities", [])

    by_country: dict[str, int] = {}
    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    total_capacity_mw = 0

    for fac in facilities:
        by_country[fac.get("country", "Unknown")] = by_country.get(fac.get("country", "Unknown"), 0) + 1
        by_type[fac.get("type", "unknown")] = by_type.get(fac.get("type", "unknown"), 0) + 1
        by_status[fac.get("status", "unknown")] = by_status.get(fac.get("status", "unknown"), 0) + 1
        if isinstance(fac.get("capacity_mw"), (int, float)):
            total_capacity_mw += fac["capacity_mw"]

    return {
        "total": len(facilities),
        "total_capacity_mw": round(total_capacity_mw, 1),
        "by_country": by_country,
        "by_type": by_type,
        "by_status": by_status,
    }


@router.get("/topics")
async def list_topics():
    """الموضوعات النووية/الإشعاعية وأوزان أساسها — مرجع شرح المؤشر."""
    return {
        "topics": [{"key": t.key, "category": t.category, "base": t.base} for t in TOPICS],
        "formula": {
            "max_weight": RISK_MAX_WEIGHT,
            "top_mean_weight": RISK_TOP_WEIGHT,
            "top_n": RISK_TOP_N,
        },
    }


@router.get("/events")
async def nuclear_events(
    hours: int = Query(default=72, ge=1, le=720),
    topic: Optional[str] = Query(default=None, max_length=40),
    min_risk: float = Query(default=0, ge=0, le=100),
    limit: int = Query(default=100, ge=1, le=300),
    near_ksa_km: Optional[float] = Query(default=None, ge=0, le=5000),
):
    """الأخبار النووية والإشعاعية مطويّة في قصص (الأحدث أولًا)."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    async with get_session_factory()() as session:
        events, truncated = await _nuclear_events(session, since, topic=topic)
    if min_risk:
        events = [e for e in events if (e.risk_score or 0) >= min_risk]
    if near_ksa_km is not None:
        events = [e for e in events if _within_ksa(e, near_ksa_km)]
    stories = collapse(events, limit)
    return {"total": len(events), "stories": len(stories), "truncated": truncated, "events": stories}


def _within_ksa(e, km: float) -> bool:
    near = nearest_ksa_point(e.latitude, e.longitude)
    return bool(near and near[0] <= km)


def risk_snapshot(events: list) -> dict:
    """المؤشر على قائمة أحداث: 60% أعلى خطر + 40% متوسط أعلى خمس قصص."""
    reps = sorted(
        (e for e in representatives(events) if e.risk_score is not None),
        key=lambda e: e.risk_score, reverse=True,
    )
    if not reps:
        return {"index": 0.0, "max": 0.0, "top_mean": 0.0, "stories": 0, "reps": []}
    top = reps[:RISK_TOP_N]
    peak = top[0].risk_score
    top_mean = sum(e.risk_score for e in top) / len(top)
    index = round(RISK_MAX_WEIGHT * peak + RISK_TOP_WEIGHT * top_mean, 1)
    return {
        "index": index,
        "max": round(peak, 1),
        "top_mean": round(top_mean, 1),
        "stories": len(reps),
        "reps": reps,
    }


async def _previous_rows(session, hours: int, now: datetime) -> tuple[list[NuclearRow] | None, bool]:
    """صفوف الفترة السابقة، أو None حين تقع خارج نافذة الاحتفاظ."""
    since = now - timedelta(hours=hours)
    prev_since = since - timedelta(hours=hours)
    if not _comparable(prev_since, now):
        return None, False
    return await _nuclear_rows(session, prev_since, until=since)


def _top_story_ids(snap: dict) -> set[int]:
    return {r.cluster_id or r.id for r in snap["reps"][:RISK_TOP_N]}


def _top_events(events: list[Event], story_ids: set[int]) -> list[dict]:
    """أعلى القصص خطرًا مسلسلة كاملة (بمصادرها)."""
    stories = collapse([e for e in events if (e.cluster_id or e.id) in story_ids], RISK_TOP_N)
    return sorted(stories, key=lambda s: s.get("risk_score") or 0, reverse=True)


async def build_risk(hours: int, now: datetime | None = None) -> dict:
    """المؤشر من صفوف خفيفة؛ الأخبار الكاملة تُجلب لأعلى القصص وحدها."""
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(hours=hours)
    async with get_session_factory()() as session:
        current, truncated = await _nuclear_rows(session, since)
        previous, prev_truncated = await _previous_rows(session, hours, now)
        story_ids = _top_story_ids(risk_snapshot(current))
        top_full: list[Event] = []
        if story_ids:
            top_full = list((await session.execute(
                select(Event).where(and_(
                    _window(since),
                    or_(Event.cluster_id.in_(story_ids), Event.id.in_(story_ids)),
                ))
            )).scalars().all())
    return risk_from_windows(
        current, previous, hours, now,
        truncated=truncated or prev_truncated,
        top_events=_top_events(top_full, story_ids),
    )


def risk_from_windows(
    current: list, previous: list | None, hours: int, now: datetime,
    *, truncated: bool = False, top_events: list[dict] | None = None,
) -> dict:
    """`previous=None`: الفترة السابقة خارج نافذة الاحتفاظ — لا مقارنة ولا اتجاه.
    `top_events=None`: تُشتقّ من `current` (يمرّر التقرير أخبارًا كاملة)."""
    since = now - timedelta(hours=hours)
    snap = risk_snapshot(current)
    comparable = previous is not None
    prev_index = risk_snapshot(previous)["index"] if comparable else None

    by_topic: dict[str, dict] = {}
    for e in snap["reps"]:
        t = by_topic.setdefault(e.topic or "energy_program", {"stories": 0, "max_risk": 0.0})
        t["stories"] += 1
        t["max_risk"] = max(t["max_risk"], e.risk_score or 0)

    # سلسلة زمنية: المؤشر داخل كل شريحة (أحداث الشريحة وحدها)
    step = timedelta(hours=hours) / _SERIES_BUCKETS
    series = []
    for i in range(_SERIES_BUCKETS):
        start = since + step * i
        end = start + step
        bucket = [e for e in current if e.event_date and start <= as_utc(e.event_date) < end]
        s = risk_snapshot(bucket)
        series.append({"t": end.isoformat(), "value": s["index"], "stories": s["stories"]})

    near_ksa = sum(1 for e in snap["reps"] if _within_ksa(e, 500))

    return {
        "period_hours": hours,
        "generated_at": now.isoformat(),
        "index": snap["index"],
        "level": severity_from_score(snap["index"]),
        "prev_index": prev_index,
        "delta": round(snap["index"] - prev_index, 1) if comparable else None,
        "comparable": comparable,
        "truncated": truncated,
        "components": {
            "max": snap["max"],
            "top_mean": snap["top_mean"],
            "max_weight": RISK_MAX_WEIGHT,
            "top_mean_weight": RISK_TOP_WEIGHT,
            "top_n": RISK_TOP_N,
        },
        "stories": snap["stories"],
        "events": len(current),
        "near_ksa_stories": near_ksa,
        "by_topic": by_topic,
        "series": series,
        "top_events": top_events if top_events is not None else _top_events(current, _top_story_ids(snap)),
    }


@router.get("/risk")
async def nuclear_risk(hours: int = Query(default=24, ge=1, le=720)):
    """مؤشر المخاطر النووية والإشعاعية (0-100) مع مكوّناته واتجاهه."""
    ttl = get_settings().response_cache_seconds
    return await cache.cached(("nuclear.risk", hours), ttl, lambda: build_risk(hours))


@router.get("/brief")
async def nuclear_brief(hours: int = Query(default=24, ge=1, le=168)):
    """تقرير الرصد النووي والإشعاعي للفترة — بيانات منظّمة؛ الواجهة تعرضه
    وتصدّره (طباعة/PDF، HTML، Markdown)."""
    ttl = get_settings().response_cache_seconds
    return await cache.cached(("nuclear.brief", hours), ttl, lambda: build_brief(hours))


async def build_brief(hours: int) -> dict:
    # تحميل واحد لأحداث الفترة يتشاركه المؤشر والأقسام ورصد المنشآت
    now = datetime.now(timezone.utc)
    async with get_session_factory()() as session:
        events, truncated = await _nuclear_events(session, now - timedelta(hours=hours))
        previous, prev_truncated = await _previous_rows(session, hours, now)
    truncated = truncated or prev_truncated
    risk = risk_from_windows(events, previous, hours, now, truncated=truncated)

    def _section(topics) -> list[dict]:
        subset = [e for e in events if (e.topic or "") in topics]
        stories = collapse(subset, 50)
        stories.sort(key=lambda s: s.get("risk_score") or 0, reverse=True)
        return stories[:10]

    watch = _facility_watch(events)[:8]
    sources: dict[str, int] = {}
    for e in events:
        name = serialize_event(e)["source_name"]
        sources[name] = sources.get(name, 0) + 1

    all_stories = collapse(events, 200)
    all_stories.sort(key=lambda s: s.get("risk_score") or 0, reverse=True)

    # للموجز السردي في رأس التقرير: مؤشر الأثر على المملكة وقطاعاته، وأبرز
    # سلاسل الترابط في الفترة نفسها
    ksa = await build_ksa_impact(hours, now=now)
    chains = await build_chains(hours, get_settings().causal_min_confidence, BRIEF_CHAINS, now=now)

    return {
        "period_hours": hours,
        "generated_at": risk["generated_at"],
        "risk": {k: risk[k] for k in (
            "index", "level", "prev_index", "delta", "comparable", "components", "stories", "near_ksa_stories", "by_topic",
        )},
        "truncated": truncated,
        "top_stories": all_stories[:10],
        "near_ksa": [s for s in all_stories if _story_near(s, 800)][:10],
        "incidents": _section(INCIDENT_TOPICS),
        "political": _section(POLITICAL_TOPICS),
        "facilities": watch,
        "sources": dict(sorted(sources.items(), key=lambda kv: kv[1], reverse=True)[:15]),
        "totals": {"events": len(events), "stories": risk["stories"]},
        "ksa_impact": {
            **{k: ksa[k] for k in ("index", "level", "prev_index", "delta", "trend", "stories")},
            "sectors": [
                {k: s[k] for k in ("key", "index", "prev_index", "delta", "trend", "stories", "top_event_id")}
                for s in ksa["sectors"]
            ],
            "top_events": [
                {k: e.get(k) for k in ("id", "title", "url", "ksa_impact", "source_name")}
                for e in ksa["top_events"][:BRIEF_TOP_KSA]
            ],
        },
        "chains": chains["chains"],
        # الموجز في الواجهة مبنيّ من قوالب نصية على هذه البيانات (لا نموذج لغوي)
        "narrative_method": "template",
    }


def _story_near(story: dict, km: float) -> bool:
    near = nearest_ksa_point(story.get("latitude"), story.get("longitude"))
    return bool(near and near[0] <= km)
