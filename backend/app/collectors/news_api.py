"""رصد - جامع أخبار NewsAPI

المستوى المجاني يسمح بـ100 طلب/يوم. الجامع كان يُرسل ستة استعلامات × لغتين
= 12 طلبًا لكل دورة، فيستنزف الحصة كاملةً قبل الظهر ثم يبقى بقية اليوم يتلقى
429. هنا استعلام مركّب واحد لكل لغة (طلبان لكل دورة) مع فاصل ساعة —
48 طلبًا يوميًا داخل الحصة.
"""
import logging

import httpx

from ..config import get_settings
from ..models.database import get_session_factory, insert_event_if_new
from ..processors.dates import parse_iso
from ._feed_base import analyzed_fields, clean_html, clean_title, make_source_id

logger = logging.getLogger("rasad.newsapi")

NEWSAPI_URL = "https://newsapi.org/v2/everything"

# استعلام واحد لكل لغة يغطي ما كانت تغطيه الاستعلامات الستة: مواضع الشرق
# الأوسط × مفردات الصراع. حدّ NewsAPI لطول `q` هو 500 حرف.
SEARCH_QUERIES = {
    "en": (
        '("middle east" OR gaza OR palestine OR israel OR yemen OR houthi OR syria '
        'OR lebanon OR hezbollah OR iran OR iraq OR saudi OR uae OR gulf) AND (war OR attack OR '
        'strike OR missile OR ceasefire OR nuclear OR radiation OR radioactive OR IAEA OR '
        'uranium OR sanctions OR "red sea")'
    ),
    "ar": (
        '("الشرق الأوسط" OR غزة OR إسرائيل OR اليمن OR سوريا OR لبنان '
        'OR إيران OR العراق OR السعودية OR الإمارات OR الخليج) AND (حرب OR هجوم OR قصف '
        'OR صاروخ OR هدنة OR نووي OR إشعاعي OR يورانيوم OR "الطاقة الذرية" OR عقوبات)'
    ),
}

_PAGE_SIZE = 50


async def collect_news() -> int:
    """جمع الأخبار من NewsAPI (طلب واحد لكل لغة)."""
    settings = get_settings()
    if not settings.newsapi_key:
        logger.info("NewsAPI: لا مفتاح (NEWSAPI_KEY) — المصدر متخطّى")
        return 0

    session_factory = get_session_factory()
    if not session_factory:
        return 0

    count = 0
    attempts = 0
    request_errors = 0

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for lang, query in SEARCH_QUERIES.items():
                attempts += 1
                try:
                    count += await _collect_language(
                        client, session_factory, settings.newsapi_key, lang, query
                    )
                except Exception as e:
                    request_errors += 1
                    logger.error(f"خطأ في استعلام NewsAPI ({lang}): {e}")
                    continue

    except Exception as e:
        logger.error(f"خطأ عام في NewsAPI: {e}")
        raise  # فشل كارثي (إنشاء العميل مثلاً) — إشارة صادقة بدل 0

    # فشلت كل الطلبات (حصة مستنزَفة/شبكة) → إشارة فشل بدل "لا جديد" صامت
    if attempts and request_errors == attempts:
        raise RuntimeError(f"NewsAPI: فشلت كل الطلبات ({request_errors}/{attempts})")

    logger.info(f"NewsAPI: تم جمع {count} خبر جديد")
    return count


async def _collect_language(client, session_factory, api_key: str, lang: str, query: str) -> int:
    """طلب واحد للغة واحدة ثم تخزين مقالاته. يرفع عند فشل الطلب."""
    params = {
        "q": query,
        "sortBy": "publishedAt",
        "pageSize": _PAGE_SIZE,
        "language": lang,
        "apiKey": api_key,
    }

    response = await client.get(NEWSAPI_URL, params=params)
    if response.status_code != 200:
        # 429 = تجاوز الحصة. لا نُدرج نصّ الاستجابة كي لا يتسرّب المفتاح.
        raise RuntimeError(f"HTTP {response.status_code}")

    articles = response.json().get("articles", [])
    count = 0

    async with session_factory() as session:
        for article in articles:
            try:
                if await _store_article(session, article, lang):
                    count += 1
            except Exception as e:
                logger.error(f"خطأ في مقال: {e}")
                continue
        await session.commit()

    return count


async def _store_article(session, article: dict, lang: str) -> bool:
    """يحوّل مقال NewsAPI إلى حدث ويُدرجه ذرّيًا؛ يعيد True إن أُدرِج فعلاً."""
    source_name = (article.get("source") or {}).get("name", "")
    title, _ = clean_title(article.get("title") or "", source_name)
    if not title:
        return False

    url = article.get("url", "")
    description = clean_html(article.get("description") or "", 600)
    fields, analysis = analyzed_fields(
        title, description,
        extra={
            "author": article.get("author") or "",
            "source_name": source_name,
            "language": lang,
        },
    )

    return await insert_event_if_new(
        session,
        source="newsapi",
        source_id=make_source_id("newsapi", url),
        title=title,
        description=description,
        url=url,
        image_url=article.get("urlToImage") or "",
        location_name=analysis.location.place_name or source_name,
        event_date=parse_iso(article.get("publishedAt")),
        **fields,
    )
