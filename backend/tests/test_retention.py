"""رصد - اختبارات سياسة الاحتفاظ بالبيانات (prune_old_data)"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.database import Event, FlightTrack, get_session_factory, prune_old_data


@pytest.mark.asyncio
async def test_prune_removes_old_and_keeps_recent():
    session_factory = get_session_factory()
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=40)
    recent = now - timedelta(days=1)

    async with session_factory() as s:
        s.add(Event(source="prune_test", title="قديم", collected_at=old, event_date=old))
        s.add(Event(source="prune_test", title="حديث", collected_at=recent, event_date=recent))
        s.add(FlightTrack(icao24="OLD123", tracked_at=now - timedelta(days=10)))
        s.add(FlightTrack(icao24="NEW123", tracked_at=now - timedelta(days=1)))
        await s.commit()

    removed = await prune_old_data(events_days=30, flights_days=7)

    assert removed["events"] >= 1
    assert removed["flight_tracks"] >= 1

    from sqlalchemy import select
    async with session_factory() as s:
        titles = [
            e.title
            for e in (await s.execute(select(Event).where(Event.source == "prune_test")))
            .scalars()
            .all()
        ]
    assert "حديث" in titles
    assert "قديم" not in titles
