"""رصد - اختبارات الذاكرة المؤقتة للنقاط الثقيلة (app/cache.py)."""
from __future__ import annotations

import pytest

from app import cache
from app.config import get_settings
from app.models import database


class TestCached:
    @pytest.mark.asyncio
    async def test_hit_until_invalidated(self):
        calls = []

        async def compute():
            calls.append(1)
            return {"n": len(calls)}

        assert (await cache.cached("k", 60, compute))["n"] == 1
        assert (await cache.cached("k", 60, compute))["n"] == 1
        assert (await cache.cached("other", 60, compute))["n"] == 2
        cache.invalidate()
        assert (await cache.cached("k", 60, compute))["n"] == 3

    @pytest.mark.asyncio
    async def test_zero_ttl_disables(self):
        calls = []

        async def compute():
            calls.append(1)
            return len(calls)

        assert await cache.cached("k", 0, compute) == 1
        assert await cache.cached("k", 0, compute) == 2

    @pytest.mark.asyncio
    async def test_analysis_cycle_invalidates(self, monkeypatch):
        async def noop(*_a, **_k):
            return 0

        monkeypatch.setattr(database, "run_story_clustering", noop)
        monkeypatch.setattr(database, "run_causal_linking", noop)

        async def compute():
            return object()

        first = await cache.cached("k", 60, compute)
        await database.run_analysis_cycle()
        assert await cache.cached("k", 60, compute) is not first

    @pytest.mark.asyncio
    async def test_endpoint_is_cached_between_writes(self, client, monkeypatch):
        from app.api import markets as markets_api

        calls = []
        real = markets_api.build_correlation

        async def counting(days, now=None):
            calls.append(days)
            return await real(days, now)

        monkeypatch.setattr(markets_api, "build_correlation", counting)
        assert get_settings().response_cache_seconds > 0
        for _ in range(3):
            assert (await client.get("/api/markets/correlation", params={"days": 7})).status_code == 200
        assert calls == [7]
