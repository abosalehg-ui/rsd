"""رصد - نقاط API لتتبع الطيران"""
from fastapi import APIRouter, Query
from sqlalchemy import select, func, desc, and_
from datetime import datetime, timedelta, timezone
from ..models.database import FlightTrack, get_session_factory
from ..collectors.adsb import get_live_flights

router = APIRouter(prefix="/api/flights", tags=["flights"])


@router.get("/live")
async def get_live():
    """الرحلات الحية الآن فوق الشرق الأوسط"""
    return await get_live_flights()


@router.get("/military/history")
async def get_military_history(
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=100, ge=1, le=500),
):
    """سجل الطائرات العسكرية"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = (
            select(FlightTrack)
            .where(
                and_(
                    FlightTrack.is_military == True,
                    FlightTrack.tracked_at >= since,
                )
            )
            .order_by(desc(FlightTrack.tracked_at))
            .limit(limit)
        )
        result = await session.execute(query)
        tracks = result.scalars().all()

        return [
            {
                "icao24": t.icao24,
                "callsign": t.callsign,
                "origin_country": t.origin_country,
                "latitude": t.latitude,
                "longitude": t.longitude,
                "altitude": t.altitude,
                "velocity": t.velocity,
                "heading": t.heading,
                "is_military": t.is_military,
                "aircraft_type": t.aircraft_type,
                "tracked_at": t.tracked_at.isoformat(),
            }
            for t in tracks
        ]


@router.get("/military/stats")
async def get_military_stats(hours: int = Query(default=24, ge=1, le=168)):
    """إحصائيات الطيران العسكري"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        base = and_(FlightTrack.is_military == True, FlightTrack.tracked_at >= since)

        total = (await session.execute(
            select(func.count(FlightTrack.id)).where(base)
        )).scalar()

        by_country = (await session.execute(
            select(FlightTrack.origin_country, func.count(FlightTrack.id))
            .where(base)
            .group_by(FlightTrack.origin_country)
            .order_by(desc(func.count(FlightTrack.id)))
        )).all()

        unique_aircraft = (await session.execute(
            select(func.count(func.distinct(FlightTrack.icao24))).where(base)
        )).scalar()

        return {
            "total_tracks": total,
            "unique_aircraft": unique_aircraft,
            "by_country": [{"country": r[0], "count": r[1]} for r in by_country],
            "period_hours": hours,
        }
