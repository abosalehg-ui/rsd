"""رصد - اختبارات تجميع القصص ونقاط الرصد النووي والإشعاعي وجامعه."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import delete, select

from app.collectors import nuclear_watch
from app.models.database import Event, get_session_factory, run_story_clustering
from app.processors.clustering import similar, title_tokens
from app.processors.text_analysis import analyze, event_fields

from .test_collectors import mock_httpx

SOURCE = "nuc_test"


def _event(title, *, hours_ago=1, source_name="A", url=None, description=""):
    now = datetime.now(timezone.utc)
    a = analyze(title, description)
    fields = event_fields(a)
    return Event(
        source=SOURCE,
        source_id=f"{SOURCE}_{title}_{source_name}_{hours_ago}",
        title=title,
        description=description,
        url=url or f"https://example.com/{abs(hash((title, source_name)))}",
        event_date=now - timedelta(hours=hours_ago),
        collected_at=now,
        extra_data=json.dumps({"source_name": source_name, **a.extra}, ensure_ascii=False),
        **fields,
    )


@pytest.fixture
async def nuclear_seed():
    sf = get_session_factory()
    samples = [
        # قصة واحدة من ثلاثة مصادر
        _event("Missile strike on Bushehr nuclear power plant reported", source_name="Reuters"),
        _event("Missile strike on Bushehr nuclear power plant reported by officials", source_name="AP", hours_ago=2),
        _event("Bushehr nuclear power plant hit by missile strike, officials say", source_name="BBC", hours_ago=3),
        # قصص أخرى
        _event("Radioactive source missing from construction site in Dammam", source_name="SPA", hours_ago=4),
        _event("IAEA Board of Governors to discuss Iran safeguards report", source_name="IAEA", hours_ago=5),
        # خبر غير نووي لا يدخل المؤشر
        _event("Ceasefire talks resume in Doha", source_name="X", hours_ago=2),
        # الفترة السابقة (للاتجاه)
        _event("Nuclear medicine centre opens in Riyadh", source_name="SPA", hours_ago=30),
    ]
    async with sf() as session:
        await session.execute(delete(Event).where(Event.source == SOURCE))
        session.add_all(samples)
        await session.commit()
    await run_story_clustering(hours=72)
    yield samples
    async with sf() as session:
        await session.execute(delete(Event).where(Event.source == SOURCE))
        await session.commit()


class TestClustering:
    def test_tokens_drop_stopwords_and_prefixes(self):
        assert "قصف" in title_tokens("والقصف على المنشأة")
        assert "the" not in title_tokens("the strike on the plant")

    def test_similar_titles(self):
        a = title_tokens("Missile strike on Bushehr nuclear power plant reported")
        b = title_tokens("Bushehr nuclear power plant hit by missile strike, officials say")
        assert similar(a, b)

    def test_different_titles(self):
        a = title_tokens("Missile strike on Bushehr nuclear power plant")
        b = title_tokens("Radioactive source missing in Dammam")
        assert not similar(a, b)

    @pytest.mark.asyncio
    async def test_same_story_shares_a_cluster(self, nuclear_seed):
        async with get_session_factory()() as session:
            rows = (await session.execute(
                select(Event.title, Event.cluster_id).where(Event.source == SOURCE)
            )).all()
        bushehr = {cid for title, cid in rows if "Bushehr" in title}
        assert len(bushehr) == 1
        assert len({cid for _, cid in rows}) == 5


class TestEventsEndpoint:
    @pytest.mark.asyncio
    async def test_collapsed_by_default(self, client, nuclear_seed):
        r = await client.get("/api/events/", params={"source": SOURCE, "hours": 72})
        body = r.json()
        assert body["total"] == 7
        assert body["stories"] == 5
        story = next(e for e in body["events"] if "Bushehr" in e["title"])
        assert story["story_size"] == 3
        assert story["story_source_count"] == 3
        assert len(story["story_related"]) == 2

    @pytest.mark.asyncio
    async def test_raw_when_not_collapsed(self, client, nuclear_seed):
        r = await client.get("/api/events/", params={"source": SOURCE, "hours": 72, "collapse": "false"})
        assert len(r.json()["events"]) == 7

    @pytest.mark.asyncio
    async def test_nuclear_category_includes_radiological(self, client, nuclear_seed):
        r = await client.get("/api/events/", params={"source": SOURCE, "category": "nuclear", "hours": 24})
        cats = {e["category"] for e in r.json()["events"]}
        assert cats == {"nuclear", "radiological"}

    @pytest.mark.asyncio
    async def test_titles_are_cleaned_on_output(self, client):
        sf = get_session_factory()
        async with sf() as session:
            session.add(Event(
                source=SOURCE, source_id=f"{SOURCE}_html", title="&quot;قصف&quot; <b>عاجل</b>",
                event_date=datetime.now(timezone.utc),
            ))
            await session.commit()
        r = await client.get("/api/events/", params={"source": SOURCE, "collapse": "false"})
        titles = [e["title"] for e in r.json()["events"]]
        assert '"قصف" عاجل' in titles
        async with sf() as session:
            await session.execute(delete(Event).where(Event.source == SOURCE))
            await session.commit()

    @pytest.mark.asyncio
    async def test_stats_expose_escalation_trend(self, client, nuclear_seed):
        body = (await client.get("/api/events/stats", params={"hours": 24})).json()
        assert {"escalation_prev", "escalation_delta", "escalation_series"} <= set(body)
        assert len(body["escalation_series"]) == 8


class TestNuclearEndpoints:
    @pytest.mark.asyncio
    async def test_risk_index(self, client, nuclear_seed):
        body = (await client.get("/api/nuclear/risk", params={"hours": 24})).json()
        assert 0 < body["index"] <= 100
        c = body["components"]
        assert body["index"] == pytest.approx(c["max_weight"] * c["max"] + c["top_mean_weight"] * c["top_mean"], abs=0.2)
        # الخبر الثلاثي يُعدّ قصة واحدة: 3 قصص نووية/إشعاعية في 24 ساعة
        assert body["stories"] == 3
        assert body["near_ksa_stories"] >= 2          # بوشهر + الدمام
        assert len(body["series"]) == 12
        assert "military_threat" in body["by_topic"]
        assert body["level"] in ("low", "medium", "high", "critical")

    @pytest.mark.asyncio
    async def test_nuclear_events_are_stories(self, client, nuclear_seed):
        body = (await client.get("/api/nuclear/events", params={"hours": 24})).json()
        titles = [e["title"] for e in body["events"]]
        assert sum("Bushehr" in t for t in titles) == 1
        assert not any("Ceasefire" in t for t in titles)

    @pytest.mark.asyncio
    async def test_nuclear_events_near_ksa_filter(self, client, nuclear_seed):
        body = (await client.get("/api/nuclear/events", params={"hours": 24, "near_ksa_km": 50})).json()
        assert [e["topic"] for e in body["events"]] == ["radioactive_source"]

    @pytest.mark.asyncio
    async def test_facility_watch(self, client, nuclear_seed):
        body = (await client.get("/api/nuclear/facilities/watch", params={"hours": 24})).json()
        top = body["facilities"][0]
        assert top["facility_id"] == "ir-bushehr-1"
        assert top["mentions"] == 3 and top["stories"] == 1
        assert top["distance_to_ksa_km"] < 300

    @pytest.mark.asyncio
    async def test_facilities_have_distance_and_planning_zones(self, client):
        body = (await client.get("/api/nuclear/facilities", params={"country": "AE"})).json()
        barakah = body["facilities"][0]
        assert barakah["distance_to_ksa_km"] < 200
        assert [z["key"] for z in barakah["planning_zones"]] == ["PAZ", "UPZ", "EPD", "ICPD"]

    @pytest.mark.asyncio
    async def test_brief(self, client, nuclear_seed):
        body = (await client.get("/api/nuclear/brief", params={"hours": 24})).json()
        assert body["risk"]["index"] > 0
        assert body["top_stories"][0]["risk_score"] >= body["top_stories"][-1]["risk_score"]
        assert any(s["topic"] == "radioactive_source" for s in body["incidents"])
        assert any(s["topic"] == "safeguards_iaea" for s in body["political"])
        assert body["facilities"][0]["facility_id"] == "ir-bushehr-1"

    @pytest.mark.asyncio
    async def test_topics(self, client):
        body = (await client.get("/api/nuclear/topics")).json()
        assert len(body["topics"]) == 12
        assert body["formula"]["top_n"] == 5


def google_news_xml(*items):
    body = "".join(
        f"<item><title>{t} - {src}</title><link>https://news.google.com/rss/articles/{i}</link>"
        f"<source url='https://x.test'>{src}</source>"
        f"<description>&lt;a href=&quot;x&quot;&gt;{t}&lt;/a&gt;</description></item>"
        for i, (t, src) in enumerate(items)
    )
    return f'<?xml version="1.0"?><rss version="2.0"><channel><title>g</title>{body}</channel></rss>'


class TestNuclearWatchCollector:
    @pytest.fixture(autouse=True)
    async def _clean(self):
        async def purge():
            async with get_session_factory()() as s:
                await s.execute(delete(Event).where(Event.source == "nuclear_watch"))
                await s.commit()
        await purge()
        yield
        await purge()

    @pytest.mark.asyncio
    async def test_filters_non_nuclear_and_splits_publisher(self, monkeypatch):
        monkeypatch.setattr(nuclear_watch, "NUCLEAR_FEEDS", [
            {"name": "GN", "url": "https://gn.test/rss", "kind": "aggregator"},
        ])
        xml = google_news_xml(
            ("بزشكيان: مستعدون لتخفيف اليورانيوم المخصب", "الشرق بلومبرغ"),
            ("اختبار الحمض النووي لتحديد هوية الضحايا", "Vietnam.vn"),
        )
        mock_httpx(monkeypatch, nuclear_watch, lambda request: httpx.Response(200, text=xml))

        assert await nuclear_watch.collect_nuclear_watch() == 1
        async with get_session_factory()() as s:
            ev = (await s.execute(select(Event).where(Event.source == "nuclear_watch"))).scalar_one()
        assert ev.title == "بزشكيان: مستعدون لتخفيف اليورانيوم المخصب"
        assert json.loads(ev.extra_data)["source_name"] == "الشرق بلومبرغ"
        assert ev.topic and ev.risk_score is not None
        assert ev.category == "nuclear"

    @pytest.mark.asyncio
    async def test_specialist_feed_is_forced_nuclear(self, monkeypatch):
        monkeypatch.setattr(nuclear_watch, "NUCLEAR_FEEDS", [
            {"name": "WNN", "url": "https://wnn.test/rss", "kind": "specialist", "force": True},
        ])
        xml = ('<?xml version="1.0"?><rss version="2.0"><channel><title>w</title>'
               '<item><title>Fuel loading begins at new unit</title><link>https://wnn.test/1</link>'
               '<description>Operator confirms schedule.</description></item></channel></rss>')
        mock_httpx(monkeypatch, nuclear_watch, lambda request: httpx.Response(200, text=xml))
        assert await nuclear_watch.collect_nuclear_watch() == 1

    @pytest.mark.asyncio
    async def test_raises_when_every_feed_fails(self, monkeypatch):
        monkeypatch.setattr(nuclear_watch, "NUCLEAR_FEEDS", [
            {"name": "A", "url": "https://a.test", "kind": "specialist", "force": True},
        ])
        mock_httpx(monkeypatch, nuclear_watch, lambda request: httpx.Response(503))
        with pytest.raises(RuntimeError):
            await nuclear_watch.collect_nuclear_watch()
