"""رصد - اختبارات بنود مراجعة مِحَك 2026-10-17: جدولة المنظّف، فحص Host،
الإقلاع البارد لـ ADS-B، قابلية مقارنة المؤشر النووي وقصّه، مسارات الطيران
العسكري، والمساعدات المشتركة (`as_utc`، `parse_extra`)."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.api import nuclear as nuclear_api
from app.collectors import adsb
from app.config import Settings, get_settings
from app.main import create_app
from app.middleware.trusted_host import TrustedHostMiddleware, host_of
from app.models.database import Event, FlightTrack, get_session_factory
from app.processors.dates import as_utc
from app.processors.normalize import parse_extra
from app.processors.text_analysis import analyze, event_fields
from app.scheduler import JOB_DEFAULTS, PRUNE_STARTUP_DELAY, register_jobs

# ===== المنظّف =====

class TestPrunerSchedule:
    def test_first_prune_runs_minutes_after_startup_not_a_day_later(self):
        scheduler = AsyncIOScheduler(job_defaults=JOB_DEFAULTS)
        before = datetime.now(timezone.utc)
        register_jobs(scheduler, get_settings())
        job = next(j for j in scheduler.get_jobs() if j.id == "data_pruner")
        first = job.next_run_time
        assert first is not None
        assert before + PRUNE_STARTUP_DELAY - timedelta(seconds=5) <= first <= before + timedelta(hours=1)


# ===== فحص Host =====

class TestHostOf:
    @pytest.mark.parametrize("header, host", [
        ("localhost:8000", "localhost"),
        ("127.0.0.1", "127.0.0.1"),
        ("[::1]:8000", "::1"),
        ("[::1]", "::1"),
        ("Example.COM:443", "example.com"),
        ("", ""),
        ("[broken", ""),
    ])
    def test_strips_port_and_brackets(self, header, host):
        assert host_of(header) == host


class TestAllowedHosts:
    def test_defaults_cover_loopback_and_cors_hosts(self):
        s = Settings(cors_origins="http://localhost:3000,https://user.github.io", allowed_hosts="", backend_host="127.0.0.1")
        hosts = s.allowed_hosts_list
        assert {"localhost", "127.0.0.1", "::1", "user.github.io"} <= set(hosts)
        assert "evil.example" not in hosts

    def test_extra_hosts_and_specific_bind_address(self):
        s = Settings(allowed_hosts=" API.example.com ,", backend_host="192.168.1.5")
        assert {"api.example.com", "192.168.1.5"} <= set(s.allowed_hosts_list)

    def test_wildcard_bind_address_is_not_a_host(self):
        assert "0.0.0.0" not in Settings(backend_host="0.0.0.0").allowed_hosts_list

    def test_star_disables_the_check(self):
        assert Settings(allowed_hosts="localhost,*").allowed_hosts_list == ["*"]


async def _ok_app(scope, receive, send):
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})


async def _status(app, host: str) -> int:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://x") as c:
        return (await c.get("/", headers={"host": host})).status_code


class TestTrustedHostMiddleware:
    async def test_rejects_unknown_host(self):
        mw = TrustedHostMiddleware(_ok_app, ["localhost", "127.0.0.1", "::1"])
        assert await _status(mw, "evil.example") == 400
        assert await _status(mw, "localhost:8000") == 200
        assert await _status(mw, "[::1]:8000") == 200

    async def test_subdomain_pattern(self):
        mw = TrustedHostMiddleware(_ok_app, ["*.example.com"])
        assert await _status(mw, "api.example.com") == 200
        assert await _status(mw, "example.com.evil.net") == 400

    async def test_star_allows_any(self):
        assert await _status(TrustedHostMiddleware(_ok_app, ["*"]), "anything.example") == 200


class TestAppRejectsForeignHost:
    async def test_dns_rebinding_host_is_refused(self):
        app = create_app(with_lifespan=False)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            ok = await c.get("/api/health")
            evil = await c.get("/api/health", headers={"host": "evil.example:8000"})
            evil_refresh = await c.post("/api/refresh", headers={"host": "evil.example", "X-Rasad-Client": "1"})
        assert ok.status_code == 200
        assert evil.status_code == 400
        assert evil_refresh.status_code == 400

    async def test_loopback_is_always_accepted(self):
        app = create_app(with_lifespan=False)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1:8000") as c:
            assert (await c.get("/api/health")).status_code == 200


# ===== الإقلاع البارد لـ ADS-B =====

class TestColdFlights:
    @pytest.fixture(autouse=True)
    def _reset(self, monkeypatch):
        monkeypatch.setitem(adsb._last_snapshot, "updated_at", None)
        monkeypatch.setitem(adsb._last_snapshot, "flights", [])
        monkeypatch.setattr(adsb, "_cold_attempted_at", None)

    async def test_concurrent_cold_requests_hit_the_provider_once(self, monkeypatch):
        calls = []

        async def fake_fetch(_sf):
            calls.append(1)
            await asyncio.sleep(0.05)
            return {"total": 1, "military": 0, "flights": [{"icao24": "abc"}]}

        monkeypatch.setattr(adsb, "_fetch_flights", fake_fetch)
        results = await asyncio.gather(*(adsb.get_live_flights() for _ in range(3)))
        assert len(calls) == 1
        assert all(r["total"] == 1 for r in results)

    async def test_failed_cold_attempt_is_not_retried_by_each_waiter(self, monkeypatch):
        calls = []

        async def failing(_sf):
            calls.append(1)
            return None

        monkeypatch.setattr(adsb, "_fetch_flights", failing)
        await asyncio.gather(*(adsb.get_live_flights() for _ in range(3)))
        assert len(calls) == 1


# ===== المؤشر النووي: المقارنة والقصّ والذاكرة المؤقتة =====

SOURCE = "hardening_nuc"


def _nuc(title, hours_ago):
    now = datetime.now(timezone.utc)
    a = analyze(title, "")
    return Event(
        source=SOURCE,
        source_id=f"{SOURCE}_{hours_ago}_{abs(hash(title))}",
        title=title,
        url=f"https://example.com/{SOURCE}/{hours_ago}",
        event_date=now - timedelta(hours=hours_ago),
        collected_at=now,
        extra_data=json.dumps({"source_name": "T", **a.extra}, ensure_ascii=False),
        **event_fields(a),
    )


@pytest.fixture
async def nuc_rows():
    sf = get_session_factory()
    rows = [
        _nuc("Radiation leak reported at Bushehr nuclear power plant", 2),
        _nuc("IAEA inspectors arrive at Natanz enrichment site", 5),
    ]
    async with sf() as session:
        await session.execute(delete(Event).where(Event.source == SOURCE))
        session.add_all(rows)
        await session.commit()
    yield rows
    async with sf() as session:
        await session.execute(delete(Event).where(Event.source == SOURCE))
        await session.commit()


class TestNuclearRiskComparability:
    async def test_short_window_is_comparable(self, client, nuc_rows):
        body = (await client.get("/api/nuclear/risk", params={"hours": 24})).json()
        assert body["comparable"] is True
        assert body["prev_index"] is not None and body["delta"] is not None
        assert body["truncated"] is False

    async def test_window_beyond_half_retention_has_no_trend(self, client, nuc_rows):
        body = (await client.get("/api/nuclear/risk", params={"hours": 720})).json()
        assert body["comparable"] is False
        assert body["prev_index"] is None and body["delta"] is None
        assert body["index"] > 0

    async def test_top_events_are_full_stories(self, client, nuc_rows):
        body = (await client.get("/api/nuclear/risk", params={"hours": 24})).json()
        assert body["top_events"], "أعلى القصص تُجلب كاملة رغم حساب المؤشر من صفوف خفيفة"
        assert {"title", "story_size", "risk_score"} <= set(body["top_events"][0])

    async def test_truncation_is_reported(self, client, nuc_rows, monkeypatch):
        monkeypatch.setattr(nuclear_api, "_ROW_CAP", 1)
        risk = (await client.get("/api/nuclear/risk", params={"hours": 24})).json()
        events = (await client.get("/api/nuclear/events", params={"hours": 24})).json()
        watch = (await client.get("/api/nuclear/facilities/watch", params={"hours": 24})).json()
        brief = (await client.get("/api/nuclear/brief", params={"hours": 24})).json()
        assert risk["truncated"] and events["truncated"] and watch["truncated"] and brief["truncated"]

    async def test_risk_is_cached_until_invalidated(self, client, nuc_rows, monkeypatch):
        from app import cache

        calls = []
        real = nuclear_api.build_risk

        async def counting(hours, now=None):
            calls.append(hours)
            return await real(hours, now)

        monkeypatch.setattr(nuclear_api, "build_risk", counting)
        await client.get("/api/nuclear/risk", params={"hours": 24})
        await client.get("/api/nuclear/risk", params={"hours": 24})
        assert calls == [24]
        cache.invalidate()
        await client.get("/api/nuclear/risk", params={"hours": 24})
        assert calls == [24, 24]


class TestEventsStatsCache:
    async def test_stats_and_country_index_are_cached(self, client, seed_events, monkeypatch):
        from app.api import events as events_api

        calls = []
        real_stats, real_index = events_api.build_stats, events_api.build_country_index

        async def stats(hours):
            calls.append("stats")
            return await real_stats(hours)

        async def index(hours, top):
            calls.append("index")
            return await real_index(hours, top)

        monkeypatch.setattr(events_api, "build_stats", stats)
        monkeypatch.setattr(events_api, "build_country_index", index)
        for _ in range(2):
            assert (await client.get("/api/events/stats")).status_code == 200
            assert (await client.get("/api/events/country-index")).status_code == 200
        assert calls == ["stats", "index"]


# ===== الطيران العسكري =====

@pytest.fixture
async def military_tracks():
    sf = get_session_factory()
    now = datetime.now(timezone.utc)
    rows = [
        FlightTrack(icao24="ae0001", callsign="RCH01", origin_country="United States", latitude=26.0,
                    longitude=50.0, altitude=9000, velocity=230, heading=90, is_military=True,
                    aircraft_type="US Military", tracked_at=now - timedelta(hours=1)),
        FlightTrack(icao24="ae0001", callsign="RCH01", origin_country="United States", latitude=26.5,
                    longitude=50.5, altitude=9100, velocity=231, heading=91, is_military=True,
                    aircraft_type="US Military", tracked_at=now - timedelta(minutes=30)),
        FlightTrack(icao24="43c001", callsign="RRR01", origin_country="United Kingdom", latitude=30.0,
                    longitude=40.0, is_military=True, tracked_at=now - timedelta(hours=3)),
        FlightTrack(icao24="ae0002", callsign="OLD", origin_country="United States", latitude=20.0,
                    longitude=45.0, is_military=True, tracked_at=now - timedelta(days=3)),
    ]
    async with sf() as session:
        await session.execute(delete(FlightTrack))
        session.add_all(rows)
        await session.commit()
    yield rows
    async with sf() as session:
        await session.execute(delete(FlightTrack))
        await session.commit()


class TestMilitaryFlights:
    async def test_history_is_newest_first_within_window(self, client, military_tracks):
        body = (await client.get("/api/flights/military/history", params={"hours": 24})).json()
        assert [t["callsign"] for t in body] == ["RCH01", "RCH01", "RRR01"]
        assert body[0]["tracked_at"] > body[1]["tracked_at"]

    async def test_history_limit(self, client, military_tracks):
        body = (await client.get("/api/flights/military/history", params={"hours": 24, "limit": 1})).json()
        assert len(body) == 1

    async def test_stats_count_tracks_and_unique_aircraft(self, client, military_tracks):
        body = (await client.get("/api/flights/military/stats", params={"hours": 24})).json()
        assert body["total_tracks"] == 3
        assert body["unique_aircraft"] == 2
        assert body["by_country"][0] == {"country": "United States", "count": 2}

    async def test_hours_are_bounded(self, client):
        assert (await client.get("/api/flights/military/stats", params={"hours": 500})).status_code == 422


# ===== المساعدات المشتركة =====

class TestSharedHelpers:
    def test_as_utc_assumes_utc_for_naive(self):
        naive = datetime(2026, 1, 1, 12, 0)
        assert as_utc(naive) == datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    def test_as_utc_converts_other_offsets(self):
        riyadh = datetime(2026, 1, 1, 15, 0, tzinfo=timezone(timedelta(hours=3)))
        assert as_utc(riyadh) == datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert as_utc(riyadh).tzinfo == timezone.utc

    @pytest.mark.parametrize("raw, expected", [
        (None, {}), ("", {}), ("not json", {}), ("[1, 2]", {}), ('{"a": 1}', {"a": 1}), ({"b": 2}, {"b": 2}),
    ])
    def test_parse_extra(self, raw, expected):
        assert parse_extra(raw) == expected
