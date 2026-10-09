"""رصد - اختبارات جامع الطاقة والأسواق (FRED) ونقاط /api/markets ومخطط التزامن.

لا شبكة: `httpx.MockTransport` يردّ بدل FRED، فنغطّي غياب المفتاح، وقيم "."
التي ينشرها FRED لأيام بلا تداول، ومنع التكرار، ومراجعة القيم، ورفض المفتاح،
وألّا يتسرّب المفتاح إلى السجل.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import delete, select, update

from app.api import markets as markets_api
from app.collectors import markets
from app.config import get_settings
from app.models.database import Event, MarketQuote, get_session_factory, prune_old_data

from .test_collectors import mock_httpx

SOURCE = "markets_test"
KEY = "fred-secret-key-123"


@pytest.fixture(autouse=True)
async def _clean_rows():
    async def _purge():
        async with get_session_factory()() as session:
            await session.execute(delete(MarketQuote))
            await session.execute(delete(Event).where(Event.source == SOURCE))
            await session.commit()

    await _purge()
    get_settings.cache_clear()
    yield
    await _purge()
    get_settings.cache_clear()


def _use_key(monkeypatch, key: str = KEY):
    monkeypatch.setenv("FRED_API_KEY", key)
    get_settings.cache_clear()


def _no_key(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "")
    get_settings.cache_clear()


def _days_ago(n: int) -> str:
    return (datetime.now(timezone.utc).date() - timedelta(days=n)).isoformat()


def fred_payload(*pairs: tuple[str, str]) -> dict:
    return {"observations": [
        {"realtime_start": "x", "realtime_end": "x", "date": d, "value": v} for d, v in pairs
    ]}


async def _quotes(code: str | None = None) -> list[MarketQuote]:
    async with get_session_factory()() as session:
        stmt = select(MarketQuote).order_by(MarketQuote.code, MarketQuote.observed_at)
        if code:
            stmt = stmt.where(MarketQuote.code == code)
        return list((await session.execute(stmt)).scalars().all())


async def _seed_quotes(code: str, rows: list[tuple[date, float]]):
    async with get_session_factory()() as session:
        await markets.upsert_quotes(session, code, rows)
        await session.commit()


# ===== تحليل ملاحظة FRED =====


class TestParseObservation:
    @pytest.mark.parametrize("value", [".", "", "  ", "n/a", "nan", "inf", "-inf", None])
    def test_rejects_missing_and_non_numeric_values(self, value):
        assert markets.parse_observation({"date": "2026-10-05", "value": value}) is None

    @pytest.mark.parametrize("raw_date", ["", "05/10/2026", "2026-13-01", None])
    def test_rejects_malformed_dates(self, raw_date):
        assert markets.parse_observation({"date": raw_date, "value": "80.1"}) is None

    def test_parses_a_valid_observation(self):
        assert markets.parse_observation({"date": "2026-10-05", "value": "84.27"}) == (date(2026, 10, 5), 84.27)


# ===== الجامع =====


class TestCollector:
    @pytest.mark.asyncio
    async def test_skips_silently_without_a_key(self, monkeypatch, caplog):
        _no_key(monkeypatch)

        def handler(request):  # pragma: no cover - لا يُفترض استدعاؤه
            raise AssertionError("لا يجوز إرسال طلب بلا مفتاح")

        mock_httpx(monkeypatch, markets, handler)
        with caplog.at_level(logging.WARNING, logger="rasad.markets"):
            assert await markets.collect_markets() == 0
        assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert await _quotes() == []

    @pytest.mark.asyncio
    async def test_stores_every_series_and_skips_dot_values(self, monkeypatch):
        _use_key(monkeypatch)
        seen = []

        def handler(request):
            params = dict(request.url.params)
            seen.append(params)
            return httpx.Response(200, json=fred_payload(
                (_days_ago(3), "80.5"),
                (_days_ago(2), "."),          # عطلة: لا تداول
                (_days_ago(1), "81.25"),
                ("bad-date", "70"),
            ))

        mock_httpx(monkeypatch, markets, handler)
        assert await markets.collect_markets() == 2 * len(markets.SERIES)

        assert [p["series_id"] for p in seen] == list(markets.SERIES)
        assert all(p["api_key"] == KEY and p["file_type"] == "json" for p in seen)
        # أول تشغيل: نافذة الاحتفاظ كاملة
        floor = (datetime.now(timezone.utc) - timedelta(days=get_settings().retention_markets_days)).date()
        assert seen[0]["observation_start"] == floor.isoformat()

        brent = await _quotes(markets.BRENT)
        assert [(q.observed_at.isoformat(), q.value) for q in brent] == [
            (_days_ago(3), 80.5), (_days_ago(1), 81.25),
        ]

    @pytest.mark.asyncio
    async def test_rerun_is_idempotent_and_updates_revised_values(self, monkeypatch):
        _use_key(monkeypatch)
        payload = {"value": "81.25"}
        starts = []

        def handler(request):
            starts.append(request.url.params["observation_start"])
            return httpx.Response(200, json=fred_payload((_days_ago(3), "80.5"), (_days_ago(1), payload["value"])))

        mock_httpx(monkeypatch, markets, handler)
        assert await markets.collect_markets() == 8
        payload["value"] = "82.0"        # FRED راجع القيمة
        assert await markets.collect_markets() == 0   # لا تواريخ جديدة

        rows = await _quotes()
        assert len(rows) == 8, "صف واحد لكل (رمز، تاريخ)"
        assert next(q for q in rows if q.code == markets.BRENT and q.observed_at.isoformat() == _days_ago(1)).value == 82.0
        # التشغيل الثاني يطلب من قبل آخر قيمة مخزّنة بأيام قليلة لا من أول النافذة
        assert starts[-1] == _days_ago(1 + markets.REFETCH_OVERLAP_DAYS)

    @pytest.mark.asyncio
    async def test_duplicate_dates_in_one_response_are_collapsed(self, monkeypatch):
        _use_key(monkeypatch)
        mock_httpx(monkeypatch, markets, lambda request: httpx.Response(
            200, json=fred_payload((_days_ago(1), "80"), (_days_ago(1), "80.4")),
        ))
        assert await markets.collect_markets() == 4
        brent = await _quotes(markets.BRENT)
        assert [q.value for q in brent] == [80.4]

    @pytest.mark.asyncio
    async def test_rejected_key_raises_without_leaking_it(self, monkeypatch, caplog):
        _use_key(monkeypatch)
        mock_httpx(monkeypatch, markets, lambda request: httpx.Response(
            400, json={"error_code": 400, "error_message": f"api_key {KEY} is not registered"},
        ))
        with caplog.at_level(logging.DEBUG), pytest.raises(PermissionError) as exc:
            await markets.collect_markets()
        assert KEY not in str(exc.value)
        assert KEY not in caplog.text

    @pytest.mark.asyncio
    async def test_one_failing_series_does_not_drop_the_others(self, monkeypatch, caplog):
        _use_key(monkeypatch)

        def handler(request):
            if request.url.params["series_id"] == "DHHNGSP":
                raise httpx.ConnectError(f"boom {request.url}")   # الرابط يحمل المفتاح
            if request.url.params["series_id"] == "VIXCLS":
                return httpx.Response(200, text="<html>not json</html>")
            return httpx.Response(200, json=fred_payload((_days_ago(1), "70")))

        mock_httpx(monkeypatch, markets, handler)
        with caplog.at_level(logging.DEBUG):
            assert await markets.collect_markets() == 2
        assert {q.code for q in await _quotes()} == {"DCOILBRENTEU", "DCOILWTICO"}
        assert KEY not in caplog.text

    @pytest.mark.asyncio
    async def test_raises_when_every_series_fails(self, monkeypatch):
        _use_key(monkeypatch)
        mock_httpx(monkeypatch, markets, lambda request: httpx.Response(503))
        with pytest.raises(RuntimeError, match="كل السلاسل"):
            await markets.collect_markets()

    @pytest.mark.asyncio
    async def test_unexpected_body_shape_stores_nothing(self, monkeypatch):
        _use_key(monkeypatch)
        mock_httpx(monkeypatch, markets, lambda request: httpx.Response(200, json={"observations": "x"}))
        assert await markets.collect_markets() == 0
        assert await _quotes() == []


# ===== الاحتفاظ والجدولة والمصادر =====


@pytest.mark.asyncio
async def test_prune_removes_old_market_quotes():
    today = datetime.now(timezone.utc).date()
    await _seed_quotes(markets.BRENT, [(today - timedelta(days=500), 60.0), (today - timedelta(days=5), 80.0)])
    removed = await prune_old_data(markets_days=400)
    assert removed["market_quotes"] == 1
    assert [q.value for q in await _quotes()] == [80.0]


def test_scheduler_registers_the_daily_markets_job():
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    from app import scheduler as sched_module

    fresh = AsyncIOScheduler(job_defaults=sched_module.JOB_DEFAULTS)
    sched_module.register_jobs(fresh, get_settings())
    job = {j.id: j for j in fresh.get_jobs()}["markets_collector"]
    assert job.trigger.interval.total_seconds() == get_settings().markets_interval == 86400


@pytest.mark.asyncio
async def test_sources_lists_fred_by_key_state(client, monkeypatch):
    _no_key(monkeypatch)
    fred = next(s for s in (await client.get("/api/sources")).json()["active"] if s["id"] == "fred")
    assert fred["status"] == "disabled"
    _use_key(monkeypatch)
    fred = next(s for s in (await client.get("/api/sources")).json()["active"] if s["id"] == "fred")
    assert fred["status"] == "active"


# ===== /api/markets/latest و /series =====


class TestLatest:
    @pytest.mark.asyncio
    async def test_empty_without_key(self, client, monkeypatch):
        _no_key(monkeypatch)
        body = (await client.get("/api/markets/latest")).json()
        assert body["enabled"] is False and body["has_data"] is False and body["as_of"] is None
        assert [s["code"] for s in body["series"]] == list(markets.SERIES)
        assert all(s["value"] is None for s in body["series"])

    @pytest.mark.asyncio
    async def test_latest_previous_and_change(self, client, monkeypatch):
        _use_key(monkeypatch)
        await _seed_quotes(markets.BRENT, [(date(2026, 10, 1), 79.0), (date(2026, 10, 2), 80.0), (date(2026, 10, 5), 84.0)])
        await _seed_quotes("VIXCLS", [(date(2026, 10, 2), 18.5)])
        r = await client.get("/api/markets/latest")
        assert r.status_code == 200
        assert "max-age=300" in r.headers["cache-control"]
        body = r.json()
        assert body["enabled"] is True and body["has_data"] is True
        assert body["as_of"] == "2026-10-05"
        assert body["source"]["name"] == "FRED"
        by = {s["code"]: s for s in body["series"]}
        brent = by[markets.BRENT]
        assert brent["value"] == 84.0 and brent["observed_at"] == "2026-10-05"
        assert brent["prev_value"] == 80.0 and brent["prev_observed_at"] == "2026-10-02"
        assert brent["change"] == 4.0 and brent["change_pct"] == 5.0
        assert brent["unit"] == "USD/bbl" and brent["fetched_at"]
        # قيمة وحيدة: لا سابقة ولا تغيّر
        assert by["VIXCLS"]["value"] == 18.5 and by["VIXCLS"]["change_pct"] is None
        assert by["DHHNGSP"]["value"] is None

    @pytest.mark.asyncio
    async def test_last_values_still_served_after_the_key_is_removed(self, client, monkeypatch):
        """دون اتصال أو بعد حذف المفتاح: آخر القيم المعروفة من قاعدة البيانات."""
        _no_key(monkeypatch)
        await _seed_quotes(markets.BRENT, [(date(2026, 10, 5), 84.0)])
        body = (await client.get("/api/markets/latest")).json()
        assert body["enabled"] is False and body["has_data"] is True
        assert body["series"][0]["value"] == 84.0


class TestSeries:
    @pytest.mark.asyncio
    async def test_window_and_code_filter(self, client):
        today = datetime.now(timezone.utc).date()
        await _seed_quotes(markets.BRENT, [(today - timedelta(days=d), 80.0 + d) for d in (1, 2, 100)])
        await _seed_quotes("VIXCLS", [(today - timedelta(days=1), 17.0)])

        body = (await client.get("/api/markets/series", params={"codes": "dcoilbrenteu,DCOILBRENTEU", "days": 90})).json()
        assert list(body["series"]) == [markets.BRENT]
        assert [p["value"] for p in body["series"][markets.BRENT]] == [82.0, 81.0], "تصاعدي بالتاريخ وداخل النافذة"

        everything = (await client.get("/api/markets/series")).json()
        assert list(everything["series"]) == list(markets.SERIES)
        assert everything["days"] == 90
        assert everything["series"]["VIXCLS"] == [{"date": (today - timedelta(days=1)).isoformat(), "value": 17.0}]

    @pytest.mark.asyncio
    async def test_rejects_unknown_codes_and_bad_days(self, client):
        r = await client.get("/api/markets/series", params={"codes": "DCOILBRENTEU,TASI"})
        assert r.status_code == 400 and "TASI" in r.json()["detail"]
        assert (await client.get("/api/markets/series", params={"days": 0})).status_code == 422
        assert (await client.get("/api/markets/series", params={"days": 5000})).status_code == 422


# ===== مخطط التزامن =====


NOW = datetime(2002, 6, 15, 12, 0, tzinfo=timezone.utc)
FIRST = date(2002, 5, 17)           # NOW - 29 يومًا (نافذة 30 يومًا تشمل اليوم)


def _event(day: date, hour: int, *, n: int, risk=None, ksa=None, category="nuclear", cluster=None,
           collected_at=None):
    when = datetime(day.year, day.month, day.day, hour, tzinfo=timezone.utc)
    return Event(
        source=SOURCE, source_id=f"{SOURCE}_{n}", title=f"t{n}", category=category, severity="high",
        risk_score=risk, ksa_impact=ksa, impact_sectors='["energy"]', cluster_id=cluster,
        # الجمع وقت الحدث نفسه: التغطية تُحسب من أول جمع
        event_date=when, collected_at=collected_at or when,
    )


@pytest.fixture
async def sync_seed():
    d1, d2 = date(2002, 6, 10), date(2002, 6, 11)
    async with get_session_factory()() as session:
        session.add_all([
            _event(FIRST, 0, n=1, risk=10, ksa=5),                # أول جمع عند منتصف الليل: يوم كامل
            _event(d1, 3, n=2, risk=80, ksa=40),
            _event(d1, 20, n=3, risk=40, ksa=None),
            _event(d1, 23, n=4, risk=None, ksa=70, category="military"),
            _event(d2, 0, n=5, risk=20, ksa=10),                   # منتصف الليل UTC = اليوم التالي
        ])
        await session.commit()
    await _seed_quotes(markets.BRENT, [
        (d1, 85.5), (d2, 86.0), (date(2002, 6, 12), 84.0), (date(2002, 3, 1), 70.0),
    ])
    yield d1, d2


class TestCorrelation:
    @pytest.mark.asyncio
    async def test_daily_alignment(self, sync_seed):
        d1, d2 = sync_seed
        body = await markets_api.build_correlation(30, now=NOW)
        points = {p["date"]: p for p in body["points"]}
        assert len(body["points"]) == 30
        assert body["points"][0]["date"] == FIRST.isoformat()
        assert body["points"][-1] == {**body["points"][-1], "date": "2002-06-15", "partial": True}
        assert body["coverage_start"] == FIRST.isoformat()

        day1 = points[d1.isoformat()]
        # نووي: 0.6 × 80 + 0.4 × متوسط (80، 40) = 48 + 24
        assert day1["nuclear"] == 72.0
        # أثر: 0.6 × 70 + 0.4 × متوسط (70، 40) = 42 + 22
        assert day1["ksa"] == 64.0
        assert day1["brent"] == 85.5 and day1["partial"] is False

        day2 = points[d2.isoformat()]
        assert (day2["nuclear"], day2["ksa"], day2["brent"]) == (20.0, 10.0, 86.0)

        # يوم بلا أحداث ضمن التغطية: صفر حقيقي؛ وبلا تداول: برنت null
        quiet = points["2002-06-13"]
        assert (quiet["nuclear"], quiet["ksa"], quiet["brent"]) == (0.0, 0.0, None)
        assert points["2002-06-12"]["brent"] == 84.0
        assert body["brent_as_of"] == "2002-06-12"
        assert body["brent_code"] == markets.BRENT

    @pytest.mark.asyncio
    async def test_stories_are_counted_once(self, sync_seed):
        d1, _ = sync_seed
        async with get_session_factory()() as session:
            # خبر ثانٍ من القصة نفسها لا يرفع متوسط أعلى القصص
            rep = (await session.execute(select(Event).where(Event.source_id == f"{SOURCE}_2"))).scalar_one()
            rep.cluster_id = rep.id
            session.add(_event(d1, 4, n=6, risk=79, ksa=1, cluster=rep.id))
            await session.commit()
        body = await markets_api.build_correlation(30, now=NOW)
        assert next(p for p in body["points"] if p["date"] == d1.isoformat())["nuclear"] == 72.0

    @pytest.mark.asyncio
    async def test_days_before_event_coverage_are_null_not_zero(self, sync_seed, monkeypatch):
        monkeypatch.setenv("RETENTION_EVENTS_DAYS", "5")
        get_settings.cache_clear()
        body = await markets_api.build_correlation(30, now=NOW)
        # الحدّ 06-10 عند ساعة التشغيل: يومه محذوف جزئيًا فلا يُعدّ مرصودًا
        assert body["coverage_start"] == "2002-06-11"
        before = next(p for p in body["points"] if p["date"] == "2002-06-10")
        assert before["nuclear"] is None and before["ksa"] is None
        assert next(p for p in body["points"] if p["date"] == "2002-06-11")["nuclear"] == 20.0

    @pytest.mark.asyncio
    async def test_backdated_events_do_not_extend_coverage(self, sync_seed):
        """حدث مؤرَّخ قبل بدء الجمع (UCDP/GDELT) لا يجعل أيامه «مرصودة» بصفر."""
        first_collect = datetime(2002, 6, 1, 9, tzinfo=timezone.utc)
        async with get_session_factory()() as session:
            await session.execute(update(Event).where(Event.source == SOURCE).values(collected_at=first_collect))
            await session.commit()
        body = await markets_api.build_correlation(30, now=NOW)
        # 06-01 بدأ الجمع فيه ظهرًا: أول يوم كامل 06-02
        assert body["coverage_start"] == "2002-06-02"
        assert next(p for p in body["points"] if p["date"] == "2002-05-25")["ksa"] is None

    @pytest.mark.asyncio
    async def test_correlation_needs_enough_shared_days(self, sync_seed):
        body = await markets_api.build_correlation(30, now=NOW)
        corr = body["correlation"]
        assert corr["nuclear_brent"] == {"r": None, "n": 3}
        assert corr["min_days"] == markets_api.MIN_CORRELATION_DAYS

    @pytest.mark.asyncio
    async def test_endpoint_shape_and_bounds(self, client):
        r = await client.get("/api/markets/correlation")
        assert r.status_code == 200
        body = r.json()
        assert body["days"] == 30 and len(body["points"]) == 30
        assert {"date", "nuclear", "ksa", "brent", "partial"} <= set(body["points"][0])
        assert (await client.get("/api/markets/correlation", params={"days": 3})).status_code == 422
        assert (await client.get("/api/markets/correlation", params={"days": 120})).status_code == 422

    @pytest.mark.asyncio
    async def test_empty_database_window(self):
        """قبل أي حدث محفوظ في النافذة: لا تغطية قبل أقدم حدث."""
        body = await markets_api.build_correlation(7, now=datetime(1990, 1, 10, tzinfo=timezone.utc))
        assert all(p["brent"] is None for p in body["points"])
        assert all(p["nuclear"] is None and p["ksa"] is None for p in body["points"])
        assert body["correlation"]["ksa_brent"] == {"r": None, "n": 0}


class TestPearson:
    def test_perfect_and_inverse(self):
        xs = list(range(12))
        assert markets_api.pearson(xs, [2 * x + 1 for x in xs]) == 1.0
        assert markets_api.pearson(xs, [-x for x in xs]) == -1.0

    def test_too_few_days_or_flat_series(self):
        assert markets_api.pearson([1, 2, 3], [1, 2, 3]) is None
        assert markets_api.pearson(list(range(12)), [5] * 12) is None

    def test_pair_counts_only_shared_days(self):
        points = [{"nuclear": float(i), "brent": 80.0 + i if i % 2 else None} for i in range(30)]
        pair = markets_api._pair(points, "nuclear")
        assert pair == {"r": 1.0, "n": 15}


class TestPearsonConstantFloats:
    def test_constant_float_series_is_undefined(self):
        ys = [float(i) for i in range(12)]
        assert markets_api.pearson([23.4] * 12, ys) is None
        assert markets_api.pearson([0.1] * 12, ys) is None

    def test_no_negative_zero(self):
        r = markets_api.pearson([1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0], [1, 1, 0, 0] * 3)
        assert r == 0.0 and str(r) == "0.0"


class TestFredStatus:
    @pytest.mark.asyncio
    async def test_rejected_key_shows_in_collector_status(self, client, monkeypatch):
        _use_key(monkeypatch)
        monkeypatch.setattr(markets, "_status", {"last_attempt": None, "last_success": None, "error": None})

        async def rejected(*_a, **_k):
            raise PermissionError("FRED: الطلب مرفوض (400)")

        monkeypatch.setattr(markets, "_fetch_series", rejected)
        with pytest.raises(PermissionError):
            await markets.collect_markets()
        fred = (await client.get("/api/collectors/status")).json()["fred"]
        assert fred["healthy"] is False and fred["error"] == "rejected_key"

    @pytest.mark.asyncio
    async def test_absent_without_key(self, client, monkeypatch):
        _no_key(monkeypatch)
        assert "fred" not in (await client.get("/api/collectors/status")).json()
