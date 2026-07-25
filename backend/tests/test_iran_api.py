"""رصد - اختبارات /api/iran/* (كانت التغطية صفراً)."""
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import delete

from app.models.database import Event, IranianLeaderNews, get_session_factory


@pytest_asyncio.fixture
async def seed_iran():
    session_factory = get_session_factory()
    now = datetime.now(timezone.utc)
    async with session_factory() as session:
        await session.execute(delete(Event).where(Event.source == "iran_osint"))
        await session.execute(delete(IranianLeaderNews).where(IranianLeaderNews.leader_name == "Test Leader"))
        session.add_all([
            Event(
                source="iran_osint", source_id="iran_t1", title="ضربة تجريبية",
                category="military", severity="critical", confidence="HIGH",
                event_type="strike", latitude=35.6, longitude=51.4,
                country="إيران", country_code="IR",
                event_date=now - timedelta(hours=2), collected_at=now,
                extra_data='{"feed_name": "TestFeed", "confidence_icon": "🟢"}',
            ),
            Event(
                source="iran_osint", source_id="iran_t2", title="إطلاق تجريبي",
                category="military", severity="high", confidence="MEDIUM",
                event_type="launch", latitude=32.6, longitude=51.6,
                country="إيران", country_code="IR",
                event_date=now - timedelta(hours=5), collected_at=now,
                extra_data="not-valid-json",
            ),
        ])
        # خبرا قائد لنفس المعرّف — نتحقّق من التجميع في استعلام واحد
        session.add_all([
            IranianLeaderNews(leader_id=1, leader_name="Test Leader", title="خبر 1",
                              url="https://example.com/1", news_date=now - timedelta(hours=1)),
            IranianLeaderNews(leader_id=1, leader_name="Test Leader", title="خبر 2",
                              url="https://example.com/2", news_date=now - timedelta(hours=3)),
        ])
        await session.commit()

    yield

    async with session_factory() as session:
        await session.execute(delete(Event).where(Event.source == "iran_osint"))
        await session.execute(delete(IranianLeaderNews).where(IranianLeaderNews.leader_name == "Test Leader"))
        await session.commit()


@pytest.mark.asyncio
async def test_strikes_returns_events_and_confidence_stats(iran_client, seed_iran):
    r = await iran_client.get("/api/iran/strikes")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    assert data["confidence_stats"] == {"HIGH": 1, "MEDIUM": 1, "LOW": 0}
    titles = [s["title"] for s in data["strikes"]]
    assert "ضربة تجريبية" in titles


@pytest.mark.asyncio
async def test_strikes_filter_by_confidence(iran_client, seed_iran):
    r = await iran_client.get("/api/iran/strikes", params={"confidence": "high"})
    assert r.status_code == 200
    for s in r.json()["strikes"]:
        assert s["confidence"] == "HIGH"


@pytest.mark.asyncio
async def test_strikes_filter_by_event_type(iran_client, seed_iran):
    r = await iran_client.get("/api/iran/strikes", params={"event_type": "launch"})
    assert [s["event_type"] for s in r.json()["strikes"]] == ["launch"]


@pytest.mark.asyncio
async def test_strike_serializer_survives_corrupt_extra_data(iran_client, seed_iran):
    """extra_data غير صالح لا يجب أن يُسقط الاستجابة."""
    r = await iran_client.get("/api/iran/strikes", params={"event_type": "launch"})
    assert r.status_code == 200
    item = r.json()["strikes"][0]
    assert item["feed_name"] == ""
    assert item["confidence_icon"] == "🔵"


@pytest.mark.asyncio
async def test_strikes_validates_hours(iran_client):
    assert (await iran_client.get("/api/iran/strikes", params={"hours": 0})).status_code == 422
    assert (await iran_client.get("/api/iran/strikes", params={"hours": 9999})).status_code == 422


@pytest.mark.asyncio
async def test_leaders_groups_news_without_n_plus_one(iran_client, seed_iran):
    r = await iran_client.get("/api/iran/leaders")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 10

    leader_one = next(x for x in data["leaders"] if x["id"] == 1)
    assert leader_one["news_count"] == 2
    assert leader_one["active"] is True
    # الأحدث أولاً
    assert leader_one["recent_news"][0]["title"] == "خبر 1"

    quiet = next(x for x in data["leaders"] if x["id"] == 9)
    assert quiet["news_count"] == 0
    assert quiet["active"] is False


@pytest.mark.asyncio
async def test_iran_stats(iran_client, seed_iran):
    r = await iran_client.get("/api/iran/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    assert data["by_type"] == {"strike": 1, "launch": 1}
    assert data["by_confidence"] == {"HIGH": 1, "MEDIUM": 1}
