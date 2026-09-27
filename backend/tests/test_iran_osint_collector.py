"""رصد - اختبارات جامع إيران OSINT على الطبقة الشبكية.

الجامع كان بتغطية 43% ومسار الجمع كله (جلب → تصنيف → موقع → قادة → تخزين)
بلا اختبار، فبقي فيه بحثان بجزء النص يضعان براكة في أراك ويُنسبان «الجمهورية
الإسلامية» لمحمد إسلامي. هنا نحقن `httpx.MockTransport` ونغطّي المسار كاملًا.
"""
from __future__ import annotations

import httpx
import pytest
from sqlalchemy import delete, select

from app.collectors import iran_osint
from app.models.database import Event, IranianLeaderNews, get_session_factory

from .test_collectors import mock_httpx, rss_xml


async def _events(source: str) -> list[Event]:
    async with get_session_factory()() as session:
        return list((await session.execute(
            select(Event).where(Event.source == source)
        )).scalars().all())


async def _leader_rows() -> list[IranianLeaderNews]:
    async with get_session_factory()() as session:
        return list((await session.execute(
            select(IranianLeaderNews).where(IranianLeaderNews.url.like("https://%.test/%"))
        )).scalars().all())


@pytest.fixture(autouse=True)
async def _clean_rows():
    async def _purge():
        async with get_session_factory()() as session:
            await session.execute(delete(Event).where(Event.source.in_(("iran_osint", "rss"))))
            await session.execute(delete(IranianLeaderNews).where(IranianLeaderNews.url.like("https://%.test/%")))
            await session.commit()

    await _purge()
    yield
    await _purge()


@pytest.fixture
def two_feeds(monkeypatch):
    monkeypatch.setattr(iran_osint, "IRAN_OSINT_FEEDS", [
        {"name": "Specialist", "url": "https://high.test/rss", "confidence": "HIGH", "icon": "🎯"},
        {"name": "Regional", "url": "https://low.test/rss", "confidence": "LOW", "icon": "📰",
         "category": "general"},
    ])


@pytest.mark.asyncio
async def test_barakah_strike_is_stored_in_the_uae(two_feeds, monkeypatch):
    def handler(request):
        if request.url.host == "high.test":
            return httpx.Response(200, text=rss_xml(
                ("UAE Barakah nuclear plant reports drone attack, IRGC blamed", "https://high.test/1"),
            ))
        return httpx.Response(200, text=rss_xml())

    mock_httpx(monkeypatch, iran_osint, handler)
    assert await iran_osint.collect_iran_osint() == 1

    (ev,) = await _events("iran_osint")
    assert ev.country_code == "AE"
    assert ev.geo_precision == "facility"
    assert ev.facility_id == "ae-barakah-1"
    assert ev.event_type == "strike"
    assert ev.confidence == "HIGH"
    assert ev.category == "nuclear", "ضربة على منشأة نووية تُقيَّم نوويًا"


@pytest.mark.asyncio
async def test_islamic_republic_does_not_tag_eslami(two_feeds, monkeypatch):
    def handler(request):
        if request.url.host == "high.test":
            return httpx.Response(200, text=rss_xml(
                ("الجمهورية الإسلامية الإيرانية تطلق صاروخًا باليستيًا جديدًا", "https://high.test/2"),
                ("Mohammad Eslami: Iran launches new centrifuges at Natanz", "https://high.test/3"),
            ))
        return httpx.Response(200, text=rss_xml())

    mock_httpx(monkeypatch, iran_osint, handler)
    assert await iran_osint.collect_iran_osint() == 2

    rows = await _leader_rows()
    assert [r.url for r in rows] == ["https://high.test/3"]
    assert rows[0].leader_name == "Mohammad Eslami"


@pytest.mark.asyncio
async def test_regional_feed_falls_back_to_plain_rss_storage(two_feeds, monkeypatch):
    """الخلاصة الإقليمية (تحمل `category`) لا تُسقط ما ليس حدثًا إيرانيًا بل
    تخزّنه خبر RSS عاديًا — كانت مسجّلة في الجامعين فيُخزَّن المقال مرتين."""
    def handler(request):
        if request.url.host == "low.test":
            return httpx.Response(200, text=rss_xml(
                ("Houthi missile strike on tanker in Red Sea", "https://low.test/1"),
                ("Cairo book fair opens its doors", "https://low.test/2"),
            ))
        return httpx.Response(200, text=rss_xml())

    mock_httpx(monkeypatch, iran_osint, handler)
    assert await iran_osint.collect_iran_osint() == 2

    iran_rows = await _events("iran_osint")
    rss_rows = await _events("rss")
    assert [e.url for e in iran_rows] == ["https://low.test/1"]
    assert iran_rows[0].country_code == "", "البحر الأحمر مسطّح مائي بلا دولة"
    assert [e.url for e in rss_rows] == ["https://low.test/2"]
    assert rss_rows[0].category == "general"


@pytest.mark.asyncio
async def test_specialist_feed_drops_unclassified_articles(two_feeds, monkeypatch):
    def handler(request):
        if request.url.host == "high.test":
            return httpx.Response(200, text=rss_xml(("Weekly newsletter roundup", "https://high.test/9")))
        return httpx.Response(200, text=rss_xml())

    mock_httpx(monkeypatch, iran_osint, handler)
    assert await iran_osint.collect_iran_osint() == 0
    assert await _events("iran_osint") == []
    assert await _events("rss") == []


@pytest.mark.asyncio
async def test_reruns_do_not_duplicate(two_feeds, monkeypatch):
    def handler(request):
        if request.url.host == "high.test":
            return httpx.Response(200, text=rss_xml(("IRGC naval drills in the Gulf", "https://high.test/4")))
        return httpx.Response(200, text=rss_xml())

    mock_httpx(monkeypatch, iran_osint, handler)
    assert await iran_osint.collect_iran_osint() == 1
    assert await iran_osint.collect_iran_osint() == 0
    assert len(await _events("iran_osint")) == 1


@pytest.mark.asyncio
async def test_raises_when_every_feed_fails(two_feeds, monkeypatch):
    mock_httpx(monkeypatch, iran_osint, lambda request: httpx.Response(403))
    with pytest.raises(RuntimeError, match="Iran OSINT"):
        await iran_osint.collect_iran_osint()


@pytest.mark.asyncio
async def test_one_dead_feed_does_not_sink_the_other(two_feeds, monkeypatch):
    def handler(request):
        if request.url.host == "high.test":
            return httpx.Response(403)
        return httpx.Response(200, text=rss_xml(("Iran fires missiles at Israel", "https://low.test/5")))

    mock_httpx(monkeypatch, iran_osint, handler)
    assert await iran_osint.collect_iran_osint() == 1
