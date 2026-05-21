"""رصد - نقاط API للأحداث"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import and_, desc, func, select

from ..models.database import Event, get_session_factory

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("/")
async def get_events(
    category: Optional[str] = None,
    severity: Optional[str] = None,
    country_code: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    hours: int = Query(default=24, ge=1, le=720),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """الحصول على الأحداث مع فلاتر"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        query = select(Event)

        # الفلاتر
        conditions = []
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        conditions.append(Event.event_date >= since)

        if category:
            conditions.append(Event.category == category)
        if severity:
            conditions.append(Event.severity == severity)
        if country_code:
            conditions.append(Event.country_code == country_code)
        if source:
            conditions.append(Event.source == source)
        if search:
            conditions.append(
                Event.title.contains(search) | Event.description.contains(search)
            )

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(desc(Event.event_date)).offset(offset).limit(limit)
        result = await session.execute(query)
        events = result.scalars().all()

        # العدد الإجمالي
        count_query = select(func.count(Event.id)).where(and_(*conditions))
        total = (await session.execute(count_query)).scalar()

        return {
            "total": total,
            "events": [_serialize_event(e) for e in events],
        }


@router.get("/latest")
async def get_latest_events(limit: int = Query(default=20, ge=1, le=100)):
    """أحدث الأحداث"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        query = select(Event).order_by(desc(Event.event_date)).limit(limit)
        result = await session.execute(query)
        events = result.scalars().all()
        return [_serialize_event(e) for e in events]


@router.get("/map")
async def get_map_events(hours: int = Query(default=24, ge=1, le=720)):
    """أحداث الخريطة (فقط التي لها إحداثيات)"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = (
            select(Event)
            .where(
                and_(
                    Event.latitude.isnot(None),
                    Event.longitude.isnot(None),
                    Event.event_date >= since,
                )
            )
            .order_by(desc(Event.event_date))
            .limit(200)
        )
        result = await session.execute(query)
        events = result.scalars().all()
        return [_serialize_event(e) for e in events]


@router.get("/stats")
async def get_stats(hours: int = Query(default=24, ge=1, le=720)):
    """إحصائيات الأحداث"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        base_filter = Event.event_date >= since

        # إجمالي
        total = (await session.execute(
            select(func.count(Event.id)).where(base_filter)
        )).scalar()

        # حسب التصنيف
        cat_query = (
            select(Event.category, func.count(Event.id))
            .where(base_filter)
            .group_by(Event.category)
        )
        categories = dict((await session.execute(cat_query)).all())

        # حسب الخطورة
        sev_query = (
            select(Event.severity, func.count(Event.id))
            .where(base_filter)
            .group_by(Event.severity)
        )
        severities = dict((await session.execute(sev_query)).all())

        # حسب الدولة
        country_query = (
            select(Event.country_code, Event.country, func.count(Event.id))
            .where(and_(base_filter, Event.country_code != ""))
            .group_by(Event.country_code, Event.country)
            .order_by(desc(func.count(Event.id)))
            .limit(15)
        )
        countries = [
            {"code": r[0], "name": r[1], "count": r[2]}
            for r in (await session.execute(country_query)).all()
        ]

        # حسب المصدر
        source_query = (
            select(Event.source, func.count(Event.id))
            .where(base_filter)
            .group_by(Event.source)
        )
        sources = dict((await session.execute(source_query)).all())

        # مؤشر التصعيد (نسبة الأحداث العسكرية الحرجة)
        critical_military = (await session.execute(
            select(func.count(Event.id)).where(
                and_(base_filter, Event.category == "military", Event.severity.in_(["critical", "high"]))
            )
        )).scalar()
        escalation_index = round((critical_military / max(total, 1)) * 100, 1)

        return {
            "total": total,
            "categories": categories,
            "severities": severities,
            "countries": countries,
            "sources": sources,
            "escalation_index": escalation_index,
            "period_hours": hours,
        }


@router.get("/timeline")
async def get_timeline(
    hours: int = Query(default=48, ge=1, le=720),
    interval: str = Query(default="hour", pattern="^(hour|day)$"),
):
    """بيانات الخط الزمني"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        query = (
            select(Event)
            .where(Event.event_date >= since)
            .order_by(Event.event_date)
        )
        result = await session.execute(query)
        events = result.scalars().all()

        return [_serialize_event(e) for e in events]


# ===== مؤشر استخبارات الدول (Country Intelligence Index) v1.3 =====
# Severity weight × Confidence weight → composite score per country
_SEVERITY_WEIGHT = {"low": 1, "medium": 3, "high": 7, "critical": 15}
_CONFIDENCE_WEIGHT = {"HIGH": 1.0, "MEDIUM": 0.8, "LOW": 0.5}


@router.get("/country-index")
async def get_country_index(
    hours: int = Query(default=72, ge=1, le=720),
    top: int = Query(default=20, ge=1, le=50),
):
    """مؤشر استخبارات لكل دولة (0-100) بناءً على عدد الأحداث × الخطورة × الثقة"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = (
            select(Event)
            .where(and_(Event.event_date >= since, Event.country_code != "", Event.country_code.isnot(None)))
        )
        events = (await session.execute(query)).scalars().all()

        countries: dict[str, dict] = {}
        for ev in events:
            code = (ev.country_code or "").upper()
            if not code:
                continue
            country = countries.setdefault(code, {
                "country_code": code,
                "country_name": ev.country or code,
                "raw_score": 0.0,
                "total": 0,
                "by_severity": {"low": 0, "medium": 0, "high": 0, "critical": 0},
                "by_category": {},
                "by_confidence": {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "NONE": 0},
            })
            sev = (ev.severity or "low").lower()
            sev_w = _SEVERITY_WEIGHT.get(sev, 1)
            conf = (ev.confidence or "").upper()
            conf_w = _CONFIDENCE_WEIGHT.get(conf, 0.7)

            country["raw_score"] += sev_w * conf_w
            country["total"] += 1
            country["by_severity"][sev] = country["by_severity"].get(sev, 0) + 1
            country["by_category"][ev.category or "general"] = country["by_category"].get(ev.category or "general", 0) + 1
            country["by_confidence"][conf if conf in country["by_confidence"] else "NONE"] += 1

        if not countries:
            return {"total_countries": 0, "period_hours": hours, "ranking": []}

        max_raw = max(c["raw_score"] for c in countries.values()) or 1.0
        ranking = sorted(countries.values(), key=lambda c: c["raw_score"], reverse=True)
        for c in ranking:
            c["score"] = round((c["raw_score"] / max_raw) * 100, 1)

        return {
            "total_countries": len(ranking),
            "period_hours": hours,
            "max_raw_score": round(max_raw, 1),
            "ranking": ranking[:top],
        }


def _serialize_event(event: Event) -> dict:
    """تحويل حدث لـ JSON"""
    import json
    extra = {}
    if event.extra_data:
        try:
            extra = json.loads(event.extra_data)
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "id": event.id,
        "source": event.source,
        "title": event.title,
        "description": event.description,
        "url": event.url,
        "image_url": event.image_url,
        "category": event.category,
        "severity": event.severity,
        "latitude": event.latitude,
        "longitude": event.longitude,
        "country": event.country,
        "country_code": event.country_code,
        "location_name": event.location_name,
        "event_date": event.event_date.isoformat() if event.event_date else None,
        "extra": extra,
    }
