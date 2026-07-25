"""رصد - اختبارات نقاط التطبيق الجذرية (كانت main.py بتغطية صفر).

نستخدم ASGITransport مباشرة فلا يعمل lifespan — أي لا مجدول ولا جمع خارجي.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app import __version__
from app.main import app


@pytest.fixture
def main_client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


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
async def test_refresh_is_rate_limited_after_the_first_call(main_client):
    """الاستدعاء الثاني خلال نافذة التبريد يعيد 429 مع Retry-After."""
    async with main_client as c:
        first = await c.post("/api/refresh")
        second = await c.post("/api/refresh")

    # الأول قد ينجح أو يفشل حسب الشبكة، لكن الثاني محدود قطعاً
    assert first.status_code in (200, 429)
    assert second.status_code == 429
    assert int(second.headers["Retry-After"]) > 0


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
