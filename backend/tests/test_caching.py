"""
رصد - اختبار ETag + Cache-Control middleware (v1.4)
"""
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.infrastructure import router as infrastructure_router
from app.middleware.cache import ETagCacheMiddleware


@pytest.fixture
def cached_app() -> FastAPI:
    a = FastAPI()
    a.add_middleware(ETagCacheMiddleware)
    a.include_router(infrastructure_router)
    return a


@pytest.mark.asyncio
async def test_etag_present(cached_app):
    transport = ASGITransport(app=cached_app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.get("/api/infrastructure/bases")
        assert r.status_code == 200
        assert "etag" in (k.lower() for k in r.headers.keys())
        assert "cache-control" in (k.lower() for k in r.headers.keys())
        assert "max-age=3600" in r.headers["cache-control"]


@pytest.mark.asyncio
async def test_304_on_matching_if_none_match(cached_app):
    transport = ASGITransport(app=cached_app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        first = await c.get("/api/infrastructure/bases")
        etag = first.headers["etag"]
        second = await c.get("/api/infrastructure/bases", headers={"If-None-Match": etag})
        assert second.status_code == 304
        assert second.headers["etag"] == etag


@pytest.mark.asyncio
async def test_200_on_mismatched_if_none_match(cached_app):
    transport = ASGITransport(app=cached_app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.get("/api/infrastructure/bases", headers={"If-None-Match": 'W/"wrong"'})
        assert r.status_code == 200
        assert r.json()["total"] >= 15
