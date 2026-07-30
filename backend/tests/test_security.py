"""رصد - اختبارات الضوابط الأمنية: مفتاح API وحدّ المعدل وإعدادات الأسرار."""
import pytest
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpx import ASGITransport, AsyncClient

from app.auth import require_api_key
from app.config import Settings, get_settings
from app.middleware.ratelimit import RateLimitMiddleware


def _app_with_protected_route() -> FastAPI:
    a = FastAPI()

    @a.post("/api/protected", dependencies=[Depends(require_api_key)])
    async def protected():
        return {"ok": True}

    return a


async def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


class TestApiKey:
    @pytest.mark.asyncio
    async def test_open_when_no_key_configured(self, monkeypatch):
        """الوضع المحلي الافتراضي — لا نُعقّد تجربة المستخدم الشخصي."""
        get_settings.cache_clear()
        monkeypatch.delenv("API_KEY", raising=False)
        async with await _client(_app_with_protected_route()) as c:
            assert (await c.post("/api/protected")).status_code == 200
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_rejects_missing_key_when_configured(self, monkeypatch):
        get_settings.cache_clear()
        monkeypatch.setenv("API_KEY", "s3cret-value")
        async with await _client(_app_with_protected_route()) as c:
            r = await c.post("/api/protected")
        assert r.status_code == 401
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_rejects_wrong_key(self, monkeypatch):
        get_settings.cache_clear()
        monkeypatch.setenv("API_KEY", "s3cret-value")
        async with await _client(_app_with_protected_route()) as c:
            r = await c.post("/api/protected", headers={"X-API-Key": "wrong"})
        assert r.status_code == 401
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_accepts_correct_key(self, monkeypatch):
        get_settings.cache_clear()
        monkeypatch.setenv("API_KEY", "s3cret-value")
        async with await _client(_app_with_protected_route()) as c:
            r = await c.post("/api/protected", headers={"X-API-Key": "s3cret-value"})
        assert r.status_code == 200
        get_settings.cache_clear()


class TestRateLimit:
    def _app(self, max_requests=3):
        a = FastAPI()
        a.add_middleware(RateLimitMiddleware, max_requests=max_requests, window_seconds=60)

        @a.get("/api/thing")
        async def thing():
            return {"ok": True}

        @a.get("/api/health")
        async def health():
            return {"ok": True}

        return a

    @pytest.mark.asyncio
    async def test_allows_requests_under_the_limit(self):
        async with await _client(self._app(max_requests=3)) as c:
            for _ in range(3):
                assert (await c.get("/api/thing")).status_code == 200

    @pytest.mark.asyncio
    async def test_rejects_over_the_limit_with_retry_after(self):
        async with await _client(self._app(max_requests=2)) as c:
            await c.get("/api/thing")
            await c.get("/api/thing")
            r = await c.get("/api/thing")
        assert r.status_code == 429
        assert int(r.headers["Retry-After"]) >= 1

    @pytest.mark.asyncio
    async def test_health_check_is_exempt(self):
        """وإلا فشلت healthchecks المتكرّرة في Docker."""
        async with await _client(self._app(max_requests=1)) as c:
            for _ in range(5):
                assert (await c.get("/api/health")).status_code == 200

    @pytest.mark.asyncio
    async def test_non_api_paths_are_untouched(self):
        a = self._app(max_requests=1)

        @a.get("/static-ish")
        async def other():
            return {"ok": True}

        async with await _client(a) as c:
            for _ in range(4):
                assert (await c.get("/static-ish")).status_code == 200

    @pytest.mark.asyncio
    async def test_forwarded_for_ignored_by_default(self):
        """انتحال X-Forwarded-For لا يتجاوز الحدّ ما لم نُفعّل الثقة صراحةً."""
        async with await _client(self._app(max_requests=2)) as c:
            await c.get("/api/thing", headers={"X-Forwarded-For": "1.1.1.1"})
            await c.get("/api/thing", headers={"X-Forwarded-For": "2.2.2.2"})
            r = await c.get("/api/thing", headers={"X-Forwarded-For": "3.3.3.3"})
        assert r.status_code == 429  # كلها تُنسب للعميل الحقيقي نفسه

    @pytest.mark.asyncio
    async def test_forwarded_for_trusted_when_enabled(self):
        a = FastAPI()
        a.add_middleware(
            RateLimitMiddleware, max_requests=2, window_seconds=60, trust_proxy_headers=True
        )

        @a.get("/api/thing")
        async def thing():
            return {"ok": True}

        async with await _client(a) as c:
            # كل XFF مختلف = مفتاح مختلف، فلا يُحدّ أيٌّ منها
            for ip in ("1.1.1.1", "2.2.2.2", "3.3.3.3"):
                r = await c.get("/api/thing", headers={"X-Forwarded-For": ip})
                assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_429_carries_cors_headers(self):
        """انحدار: كان RateLimit أبعد من CORS فتخرج 429 بلا Access-Control-Allow-Origin،
        فلا يقرأ المتصفح Retry-After. الآن CORS الأبعد فيلفّ 429."""
        a = FastAPI()
        # الترتيب كما في main: RateLimit أولاً (داخلي)، CORS آخراً (خارجي)
        a.add_middleware(RateLimitMiddleware, max_requests=1, window_seconds=60)
        a.add_middleware(
            CORSMiddleware,
            allow_origins=["http://allowed.test"],
            allow_methods=["GET"],
        )

        @a.get("/api/thing")
        async def thing():
            return {"ok": True}

        async with await _client(a) as c:
            await c.get("/api/thing", headers={"Origin": "http://allowed.test"})
            r = await c.get("/api/thing", headers={"Origin": "http://allowed.test"})
        assert r.status_code == 429
        assert r.headers.get("access-control-allow-origin") == "http://allowed.test"


class TestSettings:
    def test_cors_origins_are_split_and_trimmed(self):
        s = Settings(cors_origins=" http://a.test , http://b.test ,, ")
        assert s.cors_origins_list == ["http://a.test", "http://b.test"]

    def test_google_alert_feeds_default_to_empty(self):
        """لا روابط خلاصات شخصية مثبّتة في المصدر."""
        assert Settings(google_alert_feeds="").google_alert_feeds_list == []

    def test_google_alert_feeds_parse_name_category_url(self):
        s = Settings(google_alert_feeds="GA - Red Sea|military|https://www.google.com/alerts/feeds/1/2")
        feeds = s.google_alert_feeds_list
        assert len(feeds) == 1
        assert feeds[0]["name"] == "GA - Red Sea"
        assert feeds[0]["category"] == "military"
        assert feeds[0]["url"].startswith("https://")

    def test_google_alert_feeds_accept_a_bare_url(self):
        s = Settings(google_alert_feeds="https://www.google.com/alerts/feeds/1/2")
        assert s.google_alert_feeds_list[0]["category"] == "general"

    def test_google_alert_feeds_reject_non_https_and_malformed(self):
        s = Settings(google_alert_feeds="a|b|http://insecure.test, junk|only-two, ")
        assert s.google_alert_feeds_list == []

    def test_backend_host_defaults_to_loopback(self):
        """الافتراضي لا يعرّض API بلا مصادقة على الشبكة."""
        assert Settings().backend_host == "127.0.0.1"
