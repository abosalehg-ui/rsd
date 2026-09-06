"""رصد - اختبارات الجامعين على الطبقة الشبكية.

كان الجامعون (أخطر كود في المشروع: مدخلات خارجية غير موثوقة + كتابة في قاعدة
البيانات) بتغطية 16–25% وبلا اختبار سلبي واحد، فلا شيء يمنع تعطُّل مصدر بصمت.
نحقن هنا `httpx.MockTransport` فنغطّي المسار الكامل — طلب، تحليل، تخزين —
دون شبكة: نجاح، خطأ خادم، XML مشوّه، وفشل كل الخلاصات.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import delete, select

from app.collectors import adsb, gdelt, news_api, rss_feeds, ucdp
from app.config import get_settings
from app.models.database import Event, get_session_factory

# ===== أدوات مشتركة =====


#: الصنف الحقيقي، مُلتقَط قبل أي ترقيع — الرجوع إلى `httpx.AsyncClient` داخل
#: المصنع بعد الترقيع يستدعي المصنع نفسه (تكرار لا نهائي)، ويتكرّر الأمر حين
#: يُرقَّع مرتين في اختبار واحد.
_REAL_ASYNC_CLIENT = httpx.AsyncClient


def mock_httpx(monkeypatch, module, handler):
    """يجعل `module` يبني عملاء httpx فوق نقل وهمي بدل الشبكة."""

    def _factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return _REAL_ASYNC_CLIENT(*args, **kwargs)

    monkeypatch.setattr(module.httpx, "AsyncClient", _factory)


def rss_xml(*items: tuple[str, str]) -> str:
    """خلاصة RSS 2.0 صغيرة من أزواج (عنوان، رابط)."""
    entries = "".join(
        f"<item><title>{title}</title><link>{link}</link>"
        f"<description>وصف تجريبي</description></item>"
        for title, link in items
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<rss version=\"2.0\"><channel><title>t</title>{entries}</channel></rss>"
    )


async def events_for(source: str) -> list[Event]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        return list((await session.execute(
            select(Event).where(Event.source == source)
        )).scalars().all())


@pytest.fixture(autouse=True)
async def _clean_collector_rows():
    """يُبقي قاعدة الاختبار نظيفة من صفوف هذه الوحدة."""
    sources = ("rss", "ucdp", "newsapi", "gdelt")

    async def _purge():
        session_factory = get_session_factory()
        async with session_factory() as session:
            await session.execute(delete(Event).where(Event.source.in_(sources)))
            await session.commit()

    await _purge()
    get_settings.cache_clear()
    yield
    await _purge()
    get_settings.cache_clear()


# ===== خلاصات RSS =====


class TestRssCollector:
    @pytest.fixture(autouse=True)
    def _two_feeds(self, monkeypatch):
        monkeypatch.setattr(rss_feeds, "RSS_FEEDS", {
            "test": [
                {"name": "Feed A", "url": "https://a.test/rss", "category": "military"},
                {"name": "Feed B", "url": "https://b.test/rss", "category": "general"},
            ],
        })

    @pytest.mark.asyncio
    async def test_stores_entries_from_a_healthy_feed(self, monkeypatch):
        def handler(request):
            slug = request.url.host[0]
            return httpx.Response(200, text=rss_xml(
                (f"قصف جوي على موقع {slug}", f"https://{slug}.test/1"),
                (f"اجتماع دبلوماسي {slug}", f"https://{slug}.test/2"),
            ))

        mock_httpx(monkeypatch, rss_feeds, handler)
        count = await rss_feeds.collect_rss_feeds()

        assert count == 4  # خلاصتان × مقالان
        stored = await events_for("rss")
        assert len(stored) == 4
        assert any("قصف" in e.title for e in stored)

    @pytest.mark.asyncio
    async def test_one_failing_feed_does_not_sink_the_others(self, monkeypatch):
        def handler(request):
            if request.url.host == "a.test":
                return httpx.Response(500, text="boom")
            return httpx.Response(200, text=rss_xml(("خبر سليم", "https://b.test/1")))

        mock_httpx(monkeypatch, rss_feeds, handler)
        count = await rss_feeds.collect_rss_feeds()

        assert count == 1, "الخلاصة السليمة تُجمع رغم سقوط الأخرى"

    @pytest.mark.asyncio
    async def test_malformed_xml_is_survived(self, monkeypatch):
        def handler(request):
            if request.url.host == "a.test":
                return httpx.Response(200, text="<rss><channel><item><title>مبتور")
            return httpx.Response(200, text=rss_xml(("خبر سليم", "https://b.test/1")))

        mock_httpx(monkeypatch, rss_feeds, handler)
        count = await rss_feeds.collect_rss_feeds()

        assert count >= 1
        assert all(e.title for e in await events_for("rss")), "لا عناوين فارغة"

    @pytest.mark.asyncio
    async def test_raises_when_every_feed_fails(self, monkeypatch):
        """إشارة فشل صادقة بدل 0 صامت — وإلا بدا الجامع المعطّل هادئاً."""
        mock_httpx(monkeypatch, rss_feeds, lambda request: httpx.Response(503))

        with pytest.raises(RuntimeError, match="RSS"):
            await rss_feeds.collect_rss_feeds()

    @pytest.mark.asyncio
    async def test_reruns_do_not_duplicate_the_same_article(self, monkeypatch):
        mock_httpx(monkeypatch, rss_feeds, lambda request: httpx.Response(
            200, text=rss_xml(("خبر مكرّر", "https://a.test/same")),
        ))

        first = await rss_feeds.collect_rss_feeds()
        second = await rss_feeds.collect_rss_feeds()

        assert first == 1
        assert second == 0, "source_id ثابت من الرابط ⇒ لا تكرار"


# ===== UCDP =====


def ucdp_payload(*, event_id: int, days_ago: int, country: str = "Iraq") -> dict:
    date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    return {
        "Result": [{
            "id": event_id,
            "country": country,
            "date_start": date,
            "latitude": 33.3,
            "longitude": 44.4,
            "deaths_a": 3,
            "deaths_b": 2,
            "deaths_civilians": 20,
            "side_a": "طرف أ",
            "side_b": "طرف ب",
            "where_description": "موقع تجريبي",
            "type_of_violence": 1,
        }],
    }


class TestUcdpCollector:
    @pytest.mark.asyncio
    async def test_skips_cleanly_without_an_access_token(self, monkeypatch):
        """الـ API صار مغلقاً برمز: بلا رمز لا نُرسل طلباً أصلاً."""
        monkeypatch.delenv("UCDP_ACCESS_TOKEN", raising=False)
        get_settings.cache_clear()

        def handler(request):  # pragma: no cover - لا يُفترض استدعاؤه
            raise AssertionError("لا يجوز إرسال طلب بلا رمز وصول")

        mock_httpx(monkeypatch, ucdp, handler)
        assert await ucdp.collect_ucdp_events() == 0

    @pytest.mark.asyncio
    async def test_sends_the_access_token_header(self, monkeypatch):
        monkeypatch.setenv("UCDP_ACCESS_TOKEN", "tok-123")
        get_settings.cache_clear()
        seen = {}

        def handler(request):
            seen["token"] = request.headers.get("x-ucdp-access-token")
            seen["params"] = dict(request.url.params)
            return httpx.Response(200, json=ucdp_payload(event_id=1, days_ago=2))

        mock_httpx(monkeypatch, ucdp, handler)
        await ucdp.collect_ucdp_events()

        assert seen["token"] == "tok-123"
        assert "StartDate" in seen["params"], "نطلب نافذة زمنية لا المجموعة كاملة"

    @pytest.mark.asyncio
    async def test_stores_a_recent_event(self, monkeypatch):
        monkeypatch.setenv("UCDP_ACCESS_TOKEN", "tok-123")
        get_settings.cache_clear()
        mock_httpx(monkeypatch, ucdp, lambda request: httpx.Response(
            200, json=ucdp_payload(event_id=7, days_ago=1),
        ))

        assert await ucdp.collect_ucdp_events() == 1
        stored = await events_for("ucdp")
        assert len(stored) == 1
        assert stored[0].country_code == "IQ"
        assert stored[0].severity == "high"  # 25 وفاة: أكثر من 10 وأقل من 50

    @pytest.mark.asyncio
    async def test_does_not_store_events_older_than_the_retention_window(self, monkeypatch):
        """حارس الصفوف غير المرئية: حدث أقدم من نافذة الاحتفاظ لا يراه أحد،
        فتخزينه يملأ القاعدة بما يُحذف لاحقاً بلا أن يُعرض مرة."""
        monkeypatch.setenv("UCDP_ACCESS_TOKEN", "tok-123")
        get_settings.cache_clear()
        mock_httpx(monkeypatch, ucdp, lambda request: httpx.Response(
            200, json=ucdp_payload(event_id=9, days_ago=900),
        ))

        assert await ucdp.collect_ucdp_events() == 0
        assert await events_for("ucdp") == []

    @pytest.mark.asyncio
    async def test_raises_on_rejected_token(self, monkeypatch):
        monkeypatch.setenv("UCDP_ACCESS_TOKEN", "bad")
        get_settings.cache_clear()
        mock_httpx(monkeypatch, ucdp, lambda request: httpx.Response(401, text="Invalid token"))

        with pytest.raises(RuntimeError, match="401"):
            await ucdp.collect_ucdp_events()

    @pytest.mark.asyncio
    async def test_skips_events_without_a_usable_date(self, monkeypatch):
        """تاريخ مفقود كان يقع على "الآن" فيظهر نزاع قديم كخبر عاجل."""
        monkeypatch.setenv("UCDP_ACCESS_TOKEN", "tok-123")
        get_settings.cache_clear()
        payload = ucdp_payload(event_id=11, days_ago=1)
        payload["Result"][0]["date_start"] = ""
        mock_httpx(monkeypatch, ucdp, lambda request: httpx.Response(200, json=payload))

        assert await ucdp.collect_ucdp_events() == 0


# ===== NewsAPI =====


class TestNewsApiCollector:
    @pytest.mark.asyncio
    async def test_skips_cleanly_without_a_key(self, monkeypatch):
        monkeypatch.delenv("NEWSAPI_KEY", raising=False)
        monkeypatch.delenv("newsapi_key", raising=False)
        get_settings.cache_clear()

        def handler(request):  # pragma: no cover
            raise AssertionError("لا يجوز إرسال طلب بلا مفتاح")

        mock_httpx(monkeypatch, news_api, handler)
        assert await news_api.collect_news() == 0

    @pytest.mark.asyncio
    async def test_sends_exactly_one_request_per_language(self, monkeypatch):
        """حصة المستوى المجاني 100 طلب/يوم — كانت 12 طلباً لكل دورة."""
        monkeypatch.setenv("NEWSAPI_KEY", "k")
        get_settings.cache_clear()
        languages = []

        def handler(request):
            languages.append(request.url.params.get("language"))
            return httpx.Response(200, json={"articles": [{
                "title": f"خبر {request.url.params.get('language')}",
                "description": "قصف",
                "url": f"https://n.test/{request.url.params.get('language')}",
                "publishedAt": "2026-09-01T10:00:00Z",
                "source": {"name": "Test"},
            }]})

        mock_httpx(monkeypatch, news_api, handler)
        count = await news_api.collect_news()

        assert sorted(languages) == ["ar", "en"]
        assert count == 2

    @pytest.mark.asyncio
    async def test_raises_when_the_quota_is_exhausted(self, monkeypatch):
        monkeypatch.setenv("NEWSAPI_KEY", "k")
        get_settings.cache_clear()
        mock_httpx(monkeypatch, news_api, lambda request: httpx.Response(429, json={}))

        with pytest.raises(RuntimeError, match="NewsAPI"):
            await news_api.collect_news()

    @pytest.mark.asyncio
    async def test_error_message_never_carries_the_api_key(self, monkeypatch):
        monkeypatch.setenv("NEWSAPI_KEY", "super-secret-key")
        get_settings.cache_clear()
        mock_httpx(monkeypatch, news_api, lambda request: httpx.Response(401, json={}))

        with pytest.raises(RuntimeError) as excinfo:
            await news_api.collect_news()
        assert "super-secret-key" not in str(excinfo.value)


# ===== GDELT =====


class TestGdeltCollector:
    @pytest.mark.asyncio
    async def test_stores_articles_and_classifies_them(self, monkeypatch):
        mock_httpx(monkeypatch, gdelt, lambda request: httpx.Response(200, json={"articles": [
            {
                "url": "https://g.test/1",
                "title": "Airstrike kills civilians in Gaza",
                "seendate": "20260901T101500Z",
                "sourcecountry": "Israel",
                "socialimage": "",
                "domain": "g.test",
                "language": "English",
            },
        ]}))

        assert await gdelt.collect_gdelt_events() == 1
        stored = await events_for("gdelt")
        assert len(stored) == 1
        assert stored[0].category == "military"
        assert stored[0].country_code == "PS"  # "Gaza" في العنوان

    @pytest.mark.asyncio
    async def test_raises_when_the_quota_is_exceeded(self, monkeypatch):
        """رأينا 429 فعلياً من GDELT؛ ابتلاعه كان يُظهر الجامع المخنوق هادئاً."""
        mock_httpx(monkeypatch, gdelt, lambda request: httpx.Response(429, text="rate limited"))

        with pytest.raises(RuntimeError, match="429"):
            await gdelt.collect_gdelt_events()

    @pytest.mark.asyncio
    async def test_a_single_malformed_article_does_not_sink_the_batch(self, monkeypatch):
        mock_httpx(monkeypatch, gdelt, lambda request: httpx.Response(200, json={"articles": [
            {"url": None, "title": None},
            {
                "url": "https://g.test/ok",
                "title": "Ceasefire talks resume in Lebanon",
                "seendate": "20260901T101500Z",
            },
        ]}))

        assert await gdelt.collect_gdelt_events() >= 1


# ===== ADS-B =====


class TestAdsbSnapshot:
    @pytest.fixture(autouse=True)
    def _reset_snapshot(self):
        adsb._last_snapshot.update(
            total=0, military=0, flights=[], updated_at=None, stale=False
        )
        adsb._last_recorded.clear()
        yield
        adsb._last_snapshot.update(
            total=0, military=0, flights=[], updated_at=None, stale=False
        )
        adsb._last_recorded.clear()

    @pytest.mark.asyncio
    async def test_successful_collection_fills_the_snapshot(self, monkeypatch):
        mock_httpx(monkeypatch, adsb, lambda request: httpx.Response(200, json={"ac": [
            {"hex": "AE1234", "lat": 30.0, "lon": 40.0, "alt_baro": 10000, "flight": "RCH1"},
            {"hex": "c01234", "lat": 31.0, "lon": 41.0, "alt_baro": 9000, "flight": "UAE2"},
        ]}))

        result = await adsb.collect_flights()

        assert result["total"] == 2
        assert result["military"] == 1
        assert adsb._last_snapshot["stale"] is False
        assert adsb._last_snapshot["updated_at"] is not None

    @pytest.mark.asyncio
    async def test_a_transient_failure_keeps_the_last_good_snapshot(self, monkeypatch):
        """كان أي فشل عابر يكتب صفر رحلة فوق لقطة صالحة عمرها 30 ثانية،
        فتُفرغ الخريطة من الطائرات حتى الدورة التالية."""
        mock_httpx(monkeypatch, adsb, lambda request: httpx.Response(200, json={"ac": [
            {"hex": "AE1234", "lat": 30.0, "lon": 40.0, "alt_baro": 10000},
        ]}))
        await adsb.collect_flights()

        def boom(request):
            raise httpx.ConnectError("network down")

        mock_httpx(monkeypatch, adsb, boom)
        result = await adsb.collect_flights()

        assert result["total"] == 1, "اللقطة السابقة باقية"
        assert result["stale"] is True
        assert adsb._last_snapshot["flights"], "لم تُمسح الرحلات"

    @pytest.mark.asyncio
    async def test_rate_limited_response_also_preserves_the_snapshot(self, monkeypatch):
        mock_httpx(monkeypatch, adsb, lambda request: httpx.Response(200, json={"ac": [
            {"hex": "AE9999", "lat": 30.0, "lon": 40.0, "alt_baro": 1000},
        ]}))
        await adsb.collect_flights()

        mock_httpx(monkeypatch, adsb, lambda request: httpx.Response(429))
        result = await adsb.collect_flights()

        assert result["total"] == 1
        assert result["stale"] is True

    @pytest.mark.asyncio
    async def test_recovery_clears_the_stale_flag(self, monkeypatch):
        adsb._last_snapshot.update(total=5, stale=True, updated_at="old")
        mock_httpx(monkeypatch, adsb, lambda request: httpx.Response(200, json={"ac": [
            {"hex": "c05555", "lat": 30.0, "lon": 40.0, "alt_baro": 1000},
        ]}))

        await adsb.collect_flights()
        assert adsb._last_snapshot["stale"] is False
