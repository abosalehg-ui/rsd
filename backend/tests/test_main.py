"""رصد - اختبارات نقاط النظام (/api/health، /api/sources، /api/refresh…).

نستخدم ASGITransport مباشرة فلا يعمل lifespan — أي لا مجدول ولا جمع خارجي.
نُبدّل قاموس الجامعين `system.COLLECTORS` كي لا يضرب /api/refresh نقاطاً
خارجية حية ولا يكتب صفوفاً حقيقية تلوّث بقية الاختبارات.
"""
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

import app.api.system as system
from app import __version__
from app.auth import CLIENT_HEADER
from app.config import get_settings
from app.main import app

#: كل طلب تحديث يدوي يحتاج حارس CSRF
CLIENT_HEADERS = {CLIENT_HEADER: "1"}


@pytest.fixture
def main_client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
def mock_collectors(monkeypatch):
    """يجعل كل جامع يعيد 3 دون شبكة، ويصفّر مؤقّت التبريد."""
    monkeypatch.setattr(
        system, "COLLECTORS",
        {name: AsyncMock(return_value=3) for name in system.COLLECTORS},
    )
    monkeypatch.setattr(system, "_last_manual_refresh", 0.0)


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
async def test_sources_marks_credential_less_collectors_disabled(main_client):
    """UCDP بلا رمز وNewsAPI بلا مفتاح لا يجمعان شيئاً — لا يُعلَنان active."""
    settings = get_settings()
    async with main_client as c:
        r = await c.get("/api/sources")
    by_id = {s["id"]: s for s in r.json()["active"]}

    expected_ucdp = "active" if settings.ucdp_access_token else "disabled"
    expected_news = "active" if settings.newsapi_key else "disabled"
    assert by_id["ucdp"]["status"] == expected_ucdp
    assert by_id["newsapi"]["status"] == expected_news


@pytest.mark.asyncio
async def test_refresh_aggregates_collector_counts(main_client, mock_collectors):
    """أول استدعاء ينجح ويجمع أعداد الجامعين المُبدَّلة (5 × 3 = 15)."""
    async with main_client as c:
        r = await c.post("/api/refresh", headers=CLIENT_HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["total_new"] == 15
    assert body["sources"]["gdelt"]["status"] == "ok"
    assert body["sources"]["gdelt"]["new_events"] == 3


@pytest.mark.asyncio
async def test_refresh_requires_the_client_header(main_client, mock_collectors):
    """حارس CSRF: بلا الترويسة المخصّصة يُرفض الطلب قبل تشغيل أي جامع.

    الترويسة غير البسيطة تُلزم المتصفح بـpreflight فيرفضه CORS للأصول الغريبة،
    فلا تستطيع صفحة خارجية إطلاق الجامعين على جهاز المستخدم.
    """
    async with main_client as c:
        r = await c.post("/api/refresh")
    assert r.status_code == 403
    for collector in system.COLLECTORS.values():
        collector.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_is_rate_limited_after_the_first_call(main_client, mock_collectors):
    """الاستدعاء الثاني خلال نافذة التبريد يعيد 429 مع Retry-After."""
    async with main_client as c:
        first = await c.post("/api/refresh", headers=CLIENT_HEADERS)
        second = await c.post("/api/refresh", headers=CLIENT_HEADERS)

    assert first.status_code == 200
    assert second.status_code == 429
    assert int(second.headers["Retry-After"]) > 0


@pytest.mark.asyncio
async def test_refresh_reports_failing_collector_generically(main_client, monkeypatch):
    """جامع يرفع استثناءً يظهر status=error برسالة عامة (لا نصّ الاستثناء الخام)."""
    monkeypatch.setattr(system, "_last_manual_refresh", 0.0)
    monkeypatch.setattr(system, "COLLECTORS", {
        "gdelt": AsyncMock(return_value=2),
        "newsapi": AsyncMock(return_value=2),
        "rss": AsyncMock(return_value=2),
        "ucdp": AsyncMock(return_value=2),
        "iran_osint": AsyncMock(side_effect=RuntimeError("apikey=SECRET leaked in url")),
    })
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/refresh", headers=CLIENT_HEADERS)
    body = r.json()
    assert body["sources"]["iran_osint"]["status"] == "error"
    assert "SECRET" not in body["sources"]["iran_osint"]["message"]
    assert body["total_new"] == 8  # 4 جامعين ناجحين × 2


@pytest.mark.asyncio
async def test_collectors_status_covers_every_scheduled_source(main_client):
    async with main_client as c:
        r = await c.get("/api/collectors/status")
    assert r.status_code == 200
    data = r.json()
    assert {"gdelt", "newsapi", "rss", "ucdp", "iran_osint"} == set(data)
    for entry in data.values():
        assert entry["interval_seconds"] > 0
        assert isinstance(entry["healthy"], bool)
        assert isinstance(entry["recent_count"], int)


@pytest.mark.asyncio
async def test_cors_is_restricted_to_configured_origins():
    """انحدار: كان allow_origins=["*"] — نتأكّد أن أصلاً غريباً لا يُعكَس."""
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


@pytest.mark.asyncio
async def test_api_responses_do_not_carry_page_security_headers(main_client):
    """ترويسات الصفحات لا تُلبَس استجابات JSON — سياسة الصفحة لا تعنيها."""
    async with main_client as c:
        r = await c.get("/api/health")
    assert "x-frame-options" not in {k.lower() for k in r.headers}
