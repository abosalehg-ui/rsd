"""رصد - نقاط API لمتابعة إيران OSINT"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import and_, desc, func, select

from ..collectors.iran_osint import get_leaders_list
from ..models.database import Event, IranianLeaderNews, get_session_factory
from ._serializers import serialize_iran_event

router = APIRouter(prefix="/api/iran", tags=["iran"])

# آخر N خبر تُعرض لكل قائد، وسقف الصفوف المجلوبة في الاستعلام الموحّد
_LEADER_NEWS_LIMIT = 3
_LEADER_NEWS_FETCH_CAP = 500


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

        # إحصائيات الثقة — GROUP BY واحد بدل استعلام COUNT لكل مستوى
        conf_rows = (await session.execute(
            select(Event.confidence, func.count(Event.id))
            .where(and_(Event.source == "iran_osint", Event.event_date >= since))
            .group_by(Event.confidence)
        )).all()
        counted = {(level or "").upper(): n for level, n in conf_rows}
        conf_stats = {level: counted.get(level, 0) for level in ("HIGH", "MEDIUM", "LOW")}

        return {
            "total": total,
            "confidence_stats": conf_stats,
            "strikes": [serialize_iran_event(e) for e in events],
        }


@router.get("/leaders")
async def get_iranian_leaders(hours: int = Query(default=72, ge=1, le=720)):
    """قائمة القادة الإيرانيين مع آخر الأخبار"""
    leaders = get_leaders_list()
    session_factory = get_session_factory()

    async with session_factory() as session:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        # استعلام واحد لكل القادة بدل استعلام لكل قائد (كان N+1 بعشرة استعلامات).
        # نقصّ إلى آخر 3 أخبار لكل قائد في بايثون — عدد الصفوف صغير ومحدود.
        rows = (await session.execute(
            select(IranianLeaderNews)
            .where(
                and_(
                    IranianLeaderNews.leader_id.in_([leader["id"] for leader in leaders]),
                    IranianLeaderNews.news_date >= since,
                )
            )
            .order_by(desc(IranianLeaderNews.news_date))
            .limit(_LEADER_NEWS_FETCH_CAP)
        )).scalars().all()

        by_leader: dict[int, list[IranianLeaderNews]] = defaultdict(list)
        for row in rows:
            bucket = by_leader[row.leader_id]
            if len(bucket) < _LEADER_NEWS_LIMIT:
                bucket.append(row)

        result = []
        for leader in leaders:
            news_items = by_leader.get(leader["id"], [])
            result.append({
                **leader,
                "recent_news": [
                    {
                        "title": n.title,
                        "url": n.url,
                        "date": n.news_date.isoformat() if n.news_date else None,
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

