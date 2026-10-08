"""رصد - اختبارات نقطة الأثر على المملكة، وترقية الأعمدة وإعادة الحساب، ورابط
الحدث، وجدول المزامنة."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.api import impact as impact_api
from app.models import database
from app.models.database import (
    Event,
    backfill_analysis,
    get_session_factory,
    insert_event_if_new,
)

SOURCE = "impact_test"
# «الآن» ثابت في الماضي البعيد: أحداث الاختبارات الأخرى (بتواريخ اليوم) لا
# تدخل نوافذ هذه الاختبارات فتبقى الأرقام دقيقة.
NOW = datetime(2001, 3, 10, 12, 0, tzinfo=timezone.utc)


def _fields(title, *, hours_ago, severity="high", lat=None, lon=None, cluster=None, n=0):
    return dict(
        source=SOURCE,
        source_id=f"{SOURCE}_{n}_{title}",
        title=title,
        description="",
        severity=severity,
        category="military",
        latitude=lat,
        longitude=lon,
        cluster_id=cluster,
        event_date=NOW - timedelta(hours=hours_ago),
        collected_at=datetime.now(timezone.utc),
        extra_data=json.dumps({"source_name": f"S{n}"}),
    )


@pytest.fixture
async def impact_seed():
    sf = get_session_factory()
    async with sf() as session:
        await session.execute(delete(Event).where(Event.source == SOURCE))
        rows = [
            # الفترة الحالية (48 ساعة قبل NOW)
            _fields("Houthi drone attack on Aramco facility in Abqaiq", hours_ago=2, severity="critical",
                    lat=25.94, lon=49.67, n=1),
            _fields("Tanker struck by missile in the Red Sea", hours_ago=5, lat=15.0, lon=42.0, n=2),
            _fields("Flights suspended at Abha airport after drone alert", hours_ago=8, lat=18.2, lon=42.5, n=3),
            _fields("Ceasefire talks resume in Muscat", hours_ago=10, severity="medium", lat=23.6, lon=58.4, n=4),
            # الفترة السابقة: أمن وطيران أخفّ، ولا طاقة ولا ملاحة
            _fields("Clashes reported near the border", hours_ago=60, severity="medium", lat=17.5, lon=44.1, n=5),
            _fields("Ceasefire talks continue", hours_ago=70, severity="medium", lat=23.6, lon=58.4, n=6),
        ]
        for r in rows:
            await insert_event_if_new(session, **r)
        await session.commit()
        events = (await session.execute(select(Event).where(Event.source == SOURCE))).scalars().all()
        by_title = {e.title: e for e in events}
        # خبر ثانٍ من مصدر آخر في قصة أرامكو نفسها (أقل أثرًا)
        aramco = by_title["Houthi drone attack on Aramco facility in Abqaiq"]
        aramco.cluster_id = aramco.id
        dup = _fields("Drone attack reported in eastern region", hours_ago=3, severity="high", n=7)
        dup["cluster_id"] = aramco.id
        await insert_event_if_new(session, **dup)
        await session.commit()
    yield by_title
    async with sf() as session:
        await session.execute(delete(Event).where(Event.source == SOURCE))
        await session.commit()


class TestInsertComputesImpact:
    @pytest.mark.asyncio
    async def test_every_inserted_event_gets_impact(self, impact_seed):
        async with get_session_factory()() as session:
            rows = (await session.execute(select(Event).where(Event.source == SOURCE))).scalars().all()
        assert rows and all(r.ksa_impact is not None for r in rows)
        aramco = next(r for r in rows if "Aramco" in r.title)
        extra = json.loads(aramco.extra_data)
        assert extra["source_name"] == "S1"                  # بيانات الجامع محفوظة
        assert extra["impact"]["mention"] == "asset"
        assert aramco.ksa_impact == extra["impact"]["score"] == 90.0
        assert set(json.loads(aramco.impact_sectors)) >= {"security", "energy"}

    @pytest.mark.asyncio
    async def test_precomputed_impact_is_kept(self):
        async with get_session_factory()() as session:
            await insert_event_if_new(session, **{
                **_fields("Anything", hours_ago=1, n=99), "ksa_impact": 12.5, "impact_sectors": "[]",
            })
            await session.commit()
            ev = (await session.execute(
                select(Event).where(Event.source_id == f"{SOURCE}_99_Anything")
            )).scalar_one()
            assert ev.ksa_impact == 12.5
            await session.delete(ev)
            await session.commit()


class TestKsaImpactIndex:
    @pytest.mark.asyncio
    async def test_index_trend_and_components(self, impact_seed):
        body = await impact_api.build_ksa_impact(48, now=NOW)
        # أرامكو (90) هي الأعلى؛ قصتها تُعدّ مرة واحدة رغم مصدرين
        assert body["components"]["max"] == 90.0
        assert body["stories"] == 4
        assert body["events"] == 5
        c = body["components"]
        expected = round(c["max_weight"] * c["max"] + c["top_mean_weight"] * c["top_mean"], 1)
        assert body["index"] == pytest.approx(expected, abs=0.15)
        assert body["prev_index"] > 0
        assert body["delta"] == round(body["index"] - body["prev_index"], 1)
        assert body["trend"] == "up"
        assert body["level"] in ("critical", "high", "medium", "low")
        assert len(body["series"]) == 12
        assert body["series"][-1]["value"] > 0

    @pytest.mark.asyncio
    async def test_sector_breakdown_and_watch(self, impact_seed):
        body = await impact_api.build_ksa_impact(48, now=NOW)
        sectors = {s["key"]: s for s in body["sectors"]}
        assert set(sectors) == set(impact_api.SECTOR_KEYS)
        assert sectors["energy"]["index"] > 0 and sectors["energy"]["prev_index"] == 0
        assert sectors["health"]["stories"] == 0
        # مرتّبة تنازليًا بالمؤشر
        indexes = [s["index"] for s in body["sectors"]]
        assert indexes == sorted(indexes, reverse=True)

        watch = {w["key"] for w in body["watch"]}
        assert {"energy", "shipping_ports"} <= watch
        assert "diplomacy" not in watch           # لم يرتفع بما يكفي
        for w in body["watch"]:
            assert w["delta"] >= impact_api.WATCH_MIN_DELTA
            assert w["index"] >= impact_api.WATCH_MIN_INDEX

    @pytest.mark.asyncio
    async def test_top_events_carry_components(self, impact_seed):
        body = await impact_api.build_ksa_impact(48, now=NOW)
        top = body["top_events"][0]
        assert "Aramco" in top["title"]                      # الممثّل الأعلى أثرًا
        assert top["story_size"] == 2
        assert top["ksa_impact"] == 90.0
        assert top["impact"]["components"]["mention"] == 1.0
        assert "energy" in top["impact_sectors"]
        scores = [e["ksa_impact"] for e in body["top_events"]]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_empty_window(self):
        body = await impact_api.build_ksa_impact(24, now=datetime(1990, 1, 1, tzinfo=timezone.utc))
        assert body["index"] == 0 and body["stories"] == 0
        assert body["top_events"] == [] and body["watch"] == []
        assert body["trend"] == "flat"

    def test_trend_thresholds(self):
        assert impact_api.trend_of(5) == "up"
        assert impact_api.trend_of(-5) == "down"
        assert impact_api.trend_of(1) == "flat"


class TestImpactEndpoint:
    @pytest.mark.asyncio
    async def test_shape_and_caching(self, client):
        r = await client.get("/api/impact/ksa", params={"hours": 48})
        assert r.status_code == 200
        body = r.json()
        for key in ("index", "prev_index", "delta", "trend", "series", "sectors", "watch", "top_events", "formula"):
            assert key in body
        assert body["formula"]["severity"]["critical"] == 1.0
        assert "ETag" in r.headers
        assert "max-age=30" in r.headers["Cache-Control"]
        again = await client.get("/api/impact/ksa", params={"hours": 48},
                                 headers={"If-None-Match": r.headers["ETag"]})
        assert again.status_code in (200, 304)

    @pytest.mark.asyncio
    async def test_validates_hours(self, client):
        assert (await client.get("/api/impact/ksa", params={"hours": 0})).status_code == 422
        assert (await client.get("/api/impact/ksa", params={"hours": 9999})).status_code == 422

    @pytest.mark.asyncio
    async def test_sectors_reference(self, client):
        body = (await client.get("/api/impact/sectors")).json()
        assert body["sectors"][0] == "security"
        assert body["formula"]["top_n"] == impact_api.INDEX_TOP_N


class TestEventsSectorFilter:
    @pytest.mark.asyncio
    async def test_filters_by_sector(self, client, impact_seed):
        params = {"source": SOURCE, "hours": 720, "collapse": "false", "sector": "aviation"}
        # النافذة تنتهي الآن: أحداث 2001 خارجها، فنعيد تأريخ واحد منها
        async with get_session_factory()() as session:
            ev = impact_seed["Flights suspended at Abha airport after drone alert"]
            row = await session.get(Event, ev.id)
            row.event_date = datetime.now(timezone.utc) - timedelta(hours=1)
            await session.commit()
        body = (await client.get("/api/events/", params=params)).json()
        assert [e["title"] for e in body["events"]] == ["Flights suspended at Abha airport after drone alert"]
        assert "aviation" in body["events"][0]["impact_sectors"]

        stats = (await client.get("/api/events/stats", params={"hours": 24})).json()
        assert stats["sectors"]["aviation"] >= 1
        assert set(stats["sectors"]) == set(impact_api.SECTOR_KEYS)

    @pytest.mark.asyncio
    async def test_unknown_sector_is_rejected(self, client):
        r = await client.get("/api/events/", params={"sector": "tourism"})
        assert r.status_code == 422


class TestEventById:
    @pytest.mark.asyncio
    async def test_returns_the_requested_event_with_its_story(self, client, impact_seed):
        aramco = impact_seed["Houthi drone attack on Aramco facility in Abqaiq"]
        async with get_session_factory()() as session:
            dup = (await session.execute(
                select(Event).where(Event.source == SOURCE, Event.cluster_id == aramco.id, Event.id != aramco.id)
            )).scalar_one()
        # الرابط يشير للخبر الأقل أثرًا: يبقى هو الممثّل
        body = (await client.get(f"/api/events/{dup.id}")).json()
        assert body["id"] == dup.id
        assert body["story_size"] == 2
        assert [s["id"] for s in body["story_related"]] == [aramco.id]

    @pytest.mark.asyncio
    async def test_missing_event_is_404(self, client):
        assert (await client.get("/api/events/987654321")).status_code == 404

    @pytest.mark.asyncio
    async def test_named_routes_still_win(self, client):
        assert (await client.get("/api/events/latest")).status_code == 200
        assert (await client.get("/api/events/not-a-number")).status_code == 422


class TestSchedule:
    @pytest.mark.asyncio
    async def test_without_running_scheduler(self, client, monkeypatch):
        monkeypatch.setattr(database, "_last_analysis_at", None)
        body = (await client.get("/api/schedule")).json()
        assert body["next_sync"] is None and body["jobs"] == []
        assert "now" in body

    @pytest.mark.asyncio
    async def test_reports_next_sync_and_last_analysis(self, client, monkeypatch):
        from app.config import get_settings
        from app.scheduler import register_jobs, scheduler

        register_jobs(scheduler, get_settings())
        scheduler.start(paused=True)
        try:
            await database.run_story_clustering(hours=1)
            body = (await client.get("/api/schedule")).json()
        finally:
            scheduler.shutdown(wait=False)
            scheduler.remove_all_jobs()
        assert body["last_analysis"] is not None
        assert body["next_sync"] is not None
        assert body["next_sync_in_seconds"] >= 0
        ids = {j["id"] for j in body["jobs"]}
        assert "rss_collector" in ids
        # الطيران كل 30 ثانية لا يُحتسب «مزامنة»
        sync_times = [j["next_run"] for j in body["jobs"] if j["id"] in ("rss_collector", "gdelt_collector")]
        assert body["next_sync"] <= max(sync_times)


class TestMigrationAndBackfill:
    @pytest.mark.asyncio
    async def test_migration_adds_impact_columns(self, tmp_path):
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'old.db'}")
        async with engine.begin() as conn:
            await conn.execute(text(
                "CREATE TABLE events (id INTEGER PRIMARY KEY, source VARCHAR(50), source_id VARCHAR(255), "
                "title TEXT, event_date DATETIME, collected_at DATETIME)"
            ))
            await database._migrate_sqlite(conn)
            cols = {r[1] for r in (await conn.execute(text("PRAGMA table_info(events)"))).fetchall()}
            # تشغيل ثانٍ لا يفشل ولا يكرّر
            await database._migrate_sqlite(conn)
        await engine.dispose()
        assert {"impact_sectors", "ksa_impact", "geo_precision", "cluster_id"} <= cols

    def test_columns_are_registered(self):
        assert database._EVENTS_ADDED_COLUMNS["impact_sectors"] == "TEXT"
        assert database._EVENTS_ADDED_COLUMNS["ksa_impact"] == "FLOAT"

    @pytest.mark.asyncio
    async def test_backfill_computes_impact_for_stored_rows(self):
        sf = get_session_factory()
        async with sf() as session:
            # صفّ من v2.0 (محلَّل) بلا أثر، وصفّ UCDP (لا يُعاد تحليله) بلا أثر
            session.add(Event(
                source="legacy_impact", source_id="legacy_impact_1",
                title="Drone attack on Ras Tanura terminal", severity="critical",
                category="military", latitude=26.64, longitude=50.16, geo_precision="city",
                event_date=datetime.now(timezone.utc),
                extra_data=json.dumps({"source_kind": "official"}),
            ))
            session.add(Event(
                source="ucdp", source_id="legacy_impact_ucdp",
                title="نزاع مسلح: A vs B - Yemen", severity="high", category="military",
                latitude=15.4, longitude=44.2, geo_precision="city",
                event_date=datetime.now(timezone.utc),
            ))
            await session.commit()

        assert await backfill_analysis() >= 2
        assert await backfill_analysis() == 0          # لا شيء بعد المرة الأولى

        async with sf() as session:
            rows = {e.source_id: e for e in (await session.execute(
                select(Event).where(Event.source_id.in_(["legacy_impact_1", "legacy_impact_ucdp"]))
            )).scalars().all()}
            terminal = rows["legacy_impact_1"]
            assert terminal.ksa_impact == 100.0          # حرج × ملاصق × أصل × رسمي
            assert "energy" in json.loads(terminal.impact_sectors)
            assert json.loads(terminal.extra_data)["source_kind"] == "official"
            ucdp = rows["legacy_impact_ucdp"]
            assert json.loads(ucdp.extra_data)["impact"]["components"]["source_trust"] == 1.0
            await session.execute(delete(Event).where(Event.source_id.in_(list(rows))))
            await session.commit()

    @pytest.mark.asyncio
    async def test_reanalysed_rows_get_fresh_impact(self):
        sf = get_session_factory()
        async with sf() as session:
            session.add(Event(
                source="legacy", source_id="legacy_impact_v1",
                title="Missile strike on Bushehr nuclear power plant", category="general",
                severity="low", event_date=datetime.now(timezone.utc), ksa_impact=1.0,
            ))
            await session.commit()
        await backfill_analysis()
        async with sf() as session:
            ev = (await session.execute(select(Event).where(Event.source_id == "legacy_impact_v1"))).scalar_one()
            assert ev.category == "nuclear"
            assert ev.ksa_impact > 1.0                   # أُعيد حسابه بعد التصنيف الجديد
            await session.delete(ev)
            await session.commit()
