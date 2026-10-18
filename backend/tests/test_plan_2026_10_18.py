"""رصد - اختبارات بنود خطة مراجعة 2026-10-18 التي لم يكن يلتقطها CI لأنه يشغّل
التطبيق من غير مسار المستخدم: `.env` من جذر المستودع، و`/docs` خلف CSP،
وقفل الذاكرة المؤقتة، والإزاحة مع الطيّ، ومجموعة UCDP، ودورة الحياة."""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app import cache
from app.collectors import ucdp
from app.config import _REPO_ROOT, Settings, _env_files
from app.middleware.security_headers import (
    CONTENT_SECURITY_POLICY,
    DOCS_CONTENT_SECURITY_POLICY,
    SecurityHeadersMiddleware,
)

BACKEND = Path(__file__).resolve().parent.parent


class TestEnvFiles:
    """البند 2: `.env` في الجذر يُقرأ مهما كان مجلد التشغيل."""

    def test_repo_root_env_comes_first_then_cwd(self):
        files = _env_files()
        assert files[0] == str(_REPO_ROOT / ".env")
        assert files[1] == ".env"
        assert _REPO_ROOT == BACKEND.parent

    def test_root_env_is_read_when_backend_runs_from_its_own_folder(self, tmp_path, monkeypatch):
        """تشغيل فعلي من مجلد فرعي (كما يفعل Rasad.bat): مفتاح في جذر المستودع
        يصل إلى الإعدادات. يُعزل عن `.env` الحقيقي بترحيل الجذر إلى مجلد مؤقت."""
        root = tmp_path / "repo"
        (root / "backend" / "app").mkdir(parents=True)
        (root / ".env").write_text("NEWSAPI_KEY=rootkey123\n", encoding="utf-8")
        code = (
            "import sys; sys.path.insert(0, %r)\n"
            "from app import config\n"
            "from pathlib import Path\n"
            "config._REPO_ROOT = Path(%r)\n"
            "config.Settings.model_config['env_file'] = config._env_files()\n"
            "print(config.Settings().newsapi_key)\n"
        ) % (str(BACKEND), str(root))
        env = {k: v for k, v in os.environ.items() if k != "NEWSAPI_KEY"}
        out = subprocess.run(
            [sys.executable, "-c", code], cwd=root / "backend", env=env,
            capture_output=True, text=True, check=True,
        )
        assert out.stdout.strip() == "rootkey123"


class TestDocsCsp:
    """البند 3: Swagger/ReDoc يحمّلان من jsdelivr بسكربت مضمّن — سياسة خاصة بهما."""

    def _app(self) -> FastAPI:
        app = FastAPI()   # docs_url الافتراضي /docs
        app.add_middleware(SecurityHeadersMiddleware)
        return app

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
    async def test_docs_paths_get_the_docs_policy(self, path):
        async with AsyncClient(transport=ASGITransport(app=self._app()), base_url="http://t") as c:
            r = await c.get(path)
        assert r.status_code == 200
        csp = r.headers["content-security-policy"]
        assert csp == DOCS_CONTENT_SECURITY_POLICY
        assert "https://cdn.jsdelivr.net" in csp and "'unsafe-inline'" in csp
        assert r.headers["x-frame-options"] == "DENY"

    @pytest.mark.asyncio
    async def test_docs_page_scripts_are_all_allowed_by_its_policy(self):
        """كل مصدر سكربت في صفحة /docs الفعلية مسموح في سياستها."""
        import re

        async with AsyncClient(transport=ASGITransport(app=self._app()), base_url="http://t") as c:
            r = await c.get("/docs")
        for src in re.findall(r'<script src="([^"]+)"', r.text):
            assert src.startswith("https://cdn.jsdelivr.net/"), src
        assert "<script>" in r.text   # مضمّن — لذلك 'unsafe-inline' هناك

    def test_general_policy_is_unchanged(self):
        assert "cdn.jsdelivr.net" not in CONTENT_SECURITY_POLICY
        assert "'unsafe-inline'" not in CONTENT_SECURITY_POLICY.split("style-src")[0]


class TestCacheLock:
    """البند 11: طلبات متزامنة للمفتاح نفسه تحسب مرة واحدة."""

    @pytest.mark.asyncio
    async def test_concurrent_misses_compute_once(self):
        cache.invalidate()
        calls = 0

        async def compute():
            nonlocal calls
            calls += 1
            await asyncio.sleep(0.02)
            return calls

        results = await asyncio.gather(*(cache.cached(("lock-test",), 60, compute) for _ in range(5)))
        assert calls == 1
        assert set(results) == {1}

    @pytest.mark.asyncio
    async def test_zero_ttl_bypasses_cache(self):
        calls = 0

        async def compute():
            nonlocal calls
            calls += 1
            return calls

        await cache.cached(("no-ttl",), 0, compute)
        await cache.cached(("no-ttl",), 0, compute)
        assert calls == 2


class TestOffsetWithCollapse:
    """البند 10: الإزاحة تعدّ الأحداث الخام والحدّ يعدّ القصص — لا تُجمعان."""

    @pytest.mark.asyncio
    async def test_offset_with_collapse_is_rejected(self, client, seed_events):
        r = await client.get("/api/events/", params={"offset": 1})
        assert r.status_code == 422
        assert "collapse=false" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_offset_without_collapse_pages_raw_events(self, client, seed_events):
        first = (await client.get("/api/events/", params={"collapse": "false", "limit": 1})).json()
        second = (await client.get("/api/events/", params={"collapse": "false", "limit": 1, "offset": 1})).json()
        assert first["events"][0]["id"] != second["events"][0]["id"]


class TestUcdpDataset:
    """البند 4: لا مجموعة افتراضية منتهية؛ بلا مجموعة يُعلَن المصدر معطّلًا."""

    def test_default_dataset_is_empty_so_source_is_disabled(self):
        s = Settings(ucdp_access_token="tok", _env_file=None)
        assert s.ucdp_dataset == "" and s.ucdp_enabled is False
        assert Settings(ucdp_access_token="tok", ucdp_dataset="candidateevents/25.0.9", _env_file=None).ucdp_enabled

    @pytest.mark.parametrize("dataset, url", [
        ("25.1", "https://ucdpapi.pcr.uu.se/api/gedevents/25.1"),
        ("candidateevents/25.0.9", "https://ucdpapi.pcr.uu.se/api/candidateevents/25.0.9"),
        (" /candidateevents/25.0.9/ ", "https://ucdpapi.pcr.uu.se/api/candidateevents/25.0.9"),
    ])
    def test_dataset_url(self, dataset, url):
        assert ucdp.dataset_url(dataset) == url

    @pytest.mark.asyncio
    async def test_collector_skips_with_token_but_no_dataset(self, monkeypatch, caplog):
        monkeypatch.setattr(ucdp, "get_settings", lambda: Settings(ucdp_access_token="tok", _env_file=None))
        with caplog.at_level("WARNING", logger="rasad.ucdp"):
            assert await ucdp.collect_ucdp_events() == 0
        assert "UCDP_DATASET" in caplog.text


class TestLifespan:
    """البند 15: دورة الحياة — الجمع الأولي في الخلفية وتحذير المضيف غير المحلي."""

    @pytest.mark.asyncio
    async def test_lifespan_runs_initial_collection_and_scheduler(self, monkeypatch, caplog):
        from app import main as main_module

        started, stopped = [], []
        monkeypatch.setattr(main_module, "init_db", AsyncMock())
        monkeypatch.setattr(main_module, "backfill_analysis", AsyncMock())
        monkeypatch.setattr(main_module, "run_all_collectors", AsyncMock(return_value=(
            {"gdelt": {"status": "ok", "new_events": 2}, "rss": {"status": "error", "message": "x"}}, 2,
        )))
        monkeypatch.setattr(main_module, "start_scheduler", lambda: started.append(1))
        monkeypatch.setattr(main_module, "stop_scheduler", lambda: stopped.append(1))
        monkeypatch.setattr(main_module, "get_settings", lambda: Settings(backend_host="0.0.0.0", _env_file=None))

        app = FastAPI()
        with caplog.at_level("INFO", logger="rasad"):
            async with main_module.lifespan(app):
                assert started == [1]
                await asyncio.sleep(0)   # تترك مهمة الجمع الأولي تعمل
                await asyncio.sleep(0)
        assert stopped == [1]
        assert "الجمع الأولي: 2 حدث جديد" in caplog.text
        assert "API_KEY فارغ" in caplog.text          # تحذير المضيف غير المحلي

    @pytest.mark.asyncio
    async def test_initial_collection_failure_does_not_raise(self, monkeypatch, caplog):
        from app import main as main_module

        monkeypatch.setattr(main_module, "run_all_collectors", AsyncMock(side_effect=RuntimeError("boom")))
        with caplog.at_level("ERROR", logger="rasad"):
            await main_module._initial_collection()
        assert "boom" in caplog.text
