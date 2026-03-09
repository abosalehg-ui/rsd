"""رصد - نقاط API لمتابعة إيران OSINT"""
from fastapi import APIRouter, Query
from sqlalchemy import select, func, desc, and_
from datetime import datetime, timedelta, timezone
from typing import Optional
from ..models.database import Event, IranianLeaderNews, get_session_factory
from ..collectors.iran_osint import get_leaders_list

router = APIRouter(prefix="/api/iran", tags=["iran"])


@router.get("/strikes")
async def get_iran_strikes(
    hours: int = Query(default=72, ge=1, le=720),
    confidence: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    """الضربات والأحداث الإيرانية مع تصنيف الثقة"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        conditions = [
            Event.source == "iran_osint",
            Event.event_date >= since,
        ]
        if confidence:
            conditions.append(Event.confidence == confidence.upper())
        if event_type:
            conditions.append(Event.event_type == event_type)

        query = (
            select(Event)
            .where(and_(*conditions))
            .order_by(desc(Event.event_date))
            .limit(limit)
        )
        result = await session.execute(query)
        events = result.scalars().all()

        total = (await session.execute(
            select(func.count(Event.id)).where(and_(*conditions))
        )).scalar()

        # إحصائيات الثقة
        conf_stats = {}
        for conf_level in ["HIGH", "MEDIUM", "LOW"]:
            count = (await session.execute(
                select(func.count(Event.id)).where(
                    and_(Event.source == "iran_osint", Event.event_date >= since, Event.confidence == conf_level)
                )
            )).scalar()
            conf_stats[conf_level] = count

        return {
            "total": total,
            "confidence_stats": conf_stats,
            "strikes": [_serialize_iran_event(e) for e in events],
        }


@router.get("/leaders")
async def get_iranian_leaders(hours: int = Query(default=72, ge=1, le=720)):
    """قائمة القادة الإيرانيين مع آخر الأخبار"""
    leaders = get_leaders_list()
    session_factory = get_session_factory()

    async with session_factory() as session:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = []

        for leader in leaders:
            news_query = (
                select(IranianLeaderNews)
                .where(
                    and_(
                        IranianLeaderNews.leader_id == leader["id"],
                        IranianLeaderNews.news_date >= since,
                    )
                )
                .order_by(desc(IranianLeaderNews.news_date))
                .limit(3)
            )
            news_result = await session.execute(news_query)
            news_items = news_result.scalars().all()

            result.append({
                **leader,
                "recent_news": [
                    {
                        "title": n.title,
                        "url": n.url,
                        "date": n.news_date.isoformat(),
                    }
                    for n in news_items
                ],
                "news_count": len(news_items),
                "active": len(news_items) > 0,
            })

    return {"leaders": result, "total": len(result)}


@router.get("/stats")
async def get_iran_stats(hours: int = Query(default=72, ge=1, le=720)):
    """إحصائيات أحداث إيران"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        base = and_(Event.source == "iran_osint", Event.event_date >= since)

        total = (await session.execute(select(func.count(Event.id)).where(base))).scalar()

        # حسب النوع
        type_query = (
            select(Event.event_type, func.count(Event.id))
            .where(base)
            .group_by(Event.event_type)
        )
        by_type = dict((await session.execute(type_query)).all())

        # حسب الثقة
        conf_query = (
            select(Event.confidence, func.count(Event.id))
            .where(base)
            .group_by(Event.confidence)
        )
        by_confidence = dict((await session.execute(conf_query)).all())

        return {
            "total": total,
            "by_type": by_type,
            "by_confidence": by_confidence,
            "period_hours": hours,
        }


def _serialize_iran_event(event: Event) -> dict:
    import json
    extra = {}
    if event.extra_data:
        try:
            extra = json.loads(event.extra_data)
        except Exception:
            pass
    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "url": event.url,
        "video_url": event.video_url,
        "category": event.category,
        "severity": event.severity,
        "confidence": event.confidence,
        "confidence_icon": extra.get("confidence_icon", "🔵"),
        "event_type": event.event_type,
        "latitude": event.latitude,
        "longitude": event.longitude,
        "country": event.country,
        "location_name": event.location_name,
        "event_date": event.event_date.isoformat() if event.event_date else None,
        "feed_name": extra.get("feed_name", ""),
    }