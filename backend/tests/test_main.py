"""رصد - اختبارات نقاط التطبيق الجذرية (كانت main.py بتغطية صفر).

نستخدم ASGITransport مباشرة فلا يعمل lifespan — أي لا مجدول ولا جمع خارجي.
نُبدّل الجامعين الخمسة بـ AsyncMock كي لا يضرب /api/refresh ~30 نقطة خارجية
حية ولا يكتب صفوفاً حقيقية تلوّث بقية الاختبارات ولا يحرق حصة NewsAPI.
"""
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

import app.main as main
from app import __version__
from app.main import app

_COLLECTORS = (
    "collect_gdelt_events",
    "collect_news",
    "collect_rss_feeds",
    "collect_ucdp_events",
    "collect_iran_osint",
)


@pytest.fixture
def main_client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
def mock_collectors(monkeypatch):
    """يجعل كل جامع يعيد 3 دون شبكة."""
    for name in _COLLECTORS:
        monkeypatch.setattr(main, name, AsyncMock(return_value=3))
    # نعيد ضبط مؤقّت التبريد كي لا يتسرّب بين الاختبارات
    monkeypatch.setattr(main, "_last_manual_refresh", 0.0)


@pytest.mark.asyncio
async def test_health_reports_the_package_version(main_client):
    async with main_client as c:
        r = await c.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "running"
    assert body["version"] == __version__


@pytest.mark.asyncio
async def test_sources_lists_active_collectors_with_readable_intervals(main_client):
    async with main_client as c:
        r = await c.get("/api/sources")
    assert r.status_code == 200
    data = r.json()
    ids = {s["id"] for s in data["active"]}
    assert {"gdelt", "newsapi", "rss", "ucdp", "iran_osint", "adsb"} <= ids
    for source in data["active"]:
        assert source["interval"], "كل مصدر يحتاج وصفاً مقروءاً لفاصله"


@pytest.mark.asyncio
async def test_refresh_aggregates_collector_counts(main_client, mock_collectors):
    """أول استدعاء ينجح ويجمع أعداد الجامعين المُبدَّلة (5 × 3 = 15)."""
    async with main_client as c:
        r = await c.post("/api/refresh")
    assert r.status_code == 200
    body = r.json()
    assert body["total_new"] == 15
    assert body["sources"]["gdelt"]["status"] == "ok"
    assert body["sources"]["gdelt"]["new_events"] == 3


@pytest.mark.asyncio
async def test_refresh_is_rate_limited_after_the_first_call(main_client, mock_collectors):
    """الاستدعاء الثاني خلال نافذة التبريد يعيد 429 مع Retry-After."""
    async with main_client as c:
        first = await c.post("/api/refresh")
        second = await c.post("/api/refresh")

    assert first.status_code == 200
    assert second.status_code == 429
    assert int(second.headers["Retry-After"]) > 0


@pytest.mark.asyncio
async def test_refresh_reports_failing_collector_generically(main_client, monkeypatch):
    """جامع يرفع استثناءً يظهر status=error برسالة عامة (لا نصّ الاستثناء الخام)."""
    monkeypatch.setattr(main, "_last_manual_refresh", 0.0)
    monkeypatch.setattr(main, "collect_gdelt_events", AsyncMock(return_value=2))
    monkeypatch.setattr(main, "collect_news", AsyncMock(return_value=2))
    monkeypatch.setattr(main, "collect_rss_feeds", AsyncMock(return_value=2))
    monkeypatch.setattr(main, "collect_ucdp_events", AsyncMock(return_value=2))
    monkeypatch.setattr(
        main, "collect_iran_osint",
        AsyncMock(side_effect=RuntimeError("apikey=SECRET leaked in url")),
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/refresh")
    body = r.json()
    assert body["sources"]["iran_osint"]["status"] == "error"
    assert "SECRET" not in body["sources"]["iran_osint"]["message"]
    assert body["total_new"] == 8  # 4 جامعين ناجحين × 2


@pytest.mark.asyncio
async def test_cors_is_restricted_to_configured_origins():
    """انحدار: كان allow_origins=["*"] — نتأكّد أن أصلاً غريباً لا يُعكَس."""
    from app.config import get_settings

    allowed = get_settings().cors_origins_list
    assert allowed, "يجب أن تكون هناك قائمة أصول صريحة"
    assert "*" not in allowed

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/health", headers={"Origin": "https://evil.example"})
    assert r.headers.get("access-control-allow-origin") != "https://evil.example"


@pytest.mark.asyncio
async def test_etag_middleware_is_wired_on_api_responses(main_client):
    async with main_client as c:
        r = await c.get("/api/health")
    assert "etag" in {k.lower() for k in r.headers}
