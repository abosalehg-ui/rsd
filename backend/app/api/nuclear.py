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
from sqlalchemy import and_, desc, select

from ..models.database import Event, get_session_factory
from ..processors.gazetteer import ksa_point_en, nearest_ksa_point
from ..processors.nuclear import TOPICS, severity_from_score
from ._serializers import serialize_event
from ._stories import collapse, representatives

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


async def _nuclear_events(session, since, until=None, topic: str | None = None) -> list[Event]:
    conds = [Event.event_date >= since, Event.category.in_(NUCLEAR_CATEGORIES)]
    if until is not None:
        conds.append(Event.event_date < until)
    if topic:
        conds.append(Event.topic == topic)
    rows = await session.execute(
        select(Event).where(and_(*conds)).order_by(desc(Event.event_date)).limit(3000)
    )
    return list(rows.scalars().all())


@router.get("/facilities/watch")
async def facilities_watch(hours: int = Query(default=168, ge=1, le=720)):
    """المنشآت التي ورد ذكرها في الأخبار خلال الفترة، الأعلى خطرًا أولًا."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    async with get_session_factory()() as session:
        events = [e for e in await _nuclear_events(session, since) if e.facility_id]

    by_fac: dict[str, list[Event]] = {}
    for e in events:
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
    return {"period_hours": hours, "facilities": watch}


@router.get("/facilities/{facility_id}")
async def get_facility(facility_id: str):
    """تفاصيل منشأة نووية محددة"""
    for facility in _facilities():
        if facility.get("id") == facility_id:
            return facility
    # كان يعيد {"error": ...} بحالة 200 فيظنّها العميل نجاحاً
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
        events = await _nuclear_events(session, since, topic=topic)
    if min_risk:
        events = [e for e in events if (e.risk_score or 0) >= min_risk]
    if near_ksa_km is not None:
        events = [e for e in events if _within_ksa(e, near_ksa_km)]
    stories = collapse(events, limit)
    return {"total": len(events), "stories": len(stories), "events": stories}


def _within_ksa(e: Event, km: float) -> bool:
    near = nearest_ksa_point(e.latitude, e.longitude)
    return bool(near and near[0] <= km)


def risk_snapshot(events: list[Event]) -> dict:
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


async def build_risk(hours: int) -> dict:
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=hours)
    prev_since = since - timedelta(hours=hours)
    async with get_session_factory()() as session:
        current = await _nuclear_events(session, since)
        previous = await _nuclear_events(session, prev_since, until=since)

    snap = risk_snapshot(current)
    prev = risk_snapshot(previous)

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
        bucket = [e for e in current if e.event_date and _aware(e.event_date) >= start and _aware(e.event_date) < end]
        s = risk_snapshot(bucket)
        series.append({"t": end.isoformat(), "value": s["index"], "stories": s["stories"]})

    near_ksa = sum(1 for e in snap["reps"] if _within_ksa(e, 500))

    return {
        "period_hours": hours,
        "generated_at": now.isoformat(),
        "index": snap["index"],
        "level": severity_from_score(snap["index"]),
        "prev_index": prev["index"],
        "delta": round(snap["index"] - prev["index"], 1),
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
        "top_events": sorted(
            collapse(
                [e for e in current if (e.cluster_id or e.id) in {r.cluster_id or r.id for r in snap["reps"][:RISK_TOP_N]}],
                RISK_TOP_N,
            ),
            key=lambda s: s.get("risk_score") or 0, reverse=True,
        ),
    }


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@router.get("/risk")
async def nuclear_risk(hours: int = Query(default=24, ge=1, le=720)):
    """مؤشر المخاطر النووية والإشعاعية (0-100) مع مكوّناته واتجاهه."""
    return await build_risk(hours)


@router.get("/brief")
async def nuclear_brief(hours: int = Query(default=24, ge=1, le=168)):
    """تقرير الرصد النووي والإشعاعي للفترة — بيانات منظّمة؛ الواجهة تعرضه
    وتصدّره (طباعة/PDF، HTML، Markdown)."""
    risk = await build_risk(hours)
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    async with get_session_factory()() as session:
        events = await _nuclear_events(session, since)

    def _section(topics) -> list[dict]:
        subset = [e for e in events if (e.topic or "") in topics]
        stories = collapse(subset, 50)
        stories.sort(key=lambda s: s.get("risk_score") or 0, reverse=True)
        return stories[:10]

    watch = (await facilities_watch(hours=hours))["facilities"][:8]
    sources: dict[str, int] = {}
    for e in events:
        name = serialize_event(e)["source_name"]
        sources[name] = sources.get(name, 0) + 1

    all_stories = collapse(events, 200)
    all_stories.sort(key=lambda s: s.get("risk_score") or 0, reverse=True)

    return {
        "period_hours": hours,
        "generated_at": risk["generated_at"],
        "risk": {k: risk[k] for k in ("index", "level", "prev_index", "delta", "components", "stories", "near_ksa_stories", "by_topic")},
        "top_stories": all_stories[:10],
        "near_ksa": [s for s in all_stories if _story_near(s, 800)][:10],
        "incidents": _section(INCIDENT_TOPICS),
        "political": _section(POLITICAL_TOPICS),
        "facilities": watch,
        "sources": dict(sorted(sources.items(), key=lambda kv: kv[1], reverse=True)[:15]),
        "totals": {"events": len(events), "stories": risk["stories"]},
    }


def _story_near(story: dict, km: float) -> bool:
    near = nearest_ksa_point(story.get("latitude"), story.get("longitude"))
    return bool(near and near[0] <= km)
