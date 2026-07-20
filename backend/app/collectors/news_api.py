"""رصد - جامع أخبار NewsAPI
يجمع الأخبار من مصادر عالمية عبر NewsAPI
"""
import hashlib
import json
import logging
from datetime import datetime, timezone

import httpx

from ..config import get_settings
from ..models.database import get_session_factory, insert_event_if_new
from ..processors.text_analysis import classify, geolocate

logger = logging.getLogger("rasad.newsapi")

NEWSAPI_URL = "https://newsapi.org/v2/everything"

# استعلامات البحث لتغطية شاملة
SEARCH_QUERIES = [
    '("middle east" OR "الشرق الأوسط") AND (war OR conflict OR attack)',
    "(gaza OR palestine) AND (strike OR ceasefire OR humanitarian)",
    "(yemen OR houthi) AND (attack OR red sea OR shipping)",
    "(syria OR lebanon) AND (military OR hezbollah OR airstrike)",
    "(iran OR nuclear) AND (enrichment OR IAEA OR sanctions)",
    "(iraq) AND (militia OR attack OR security)",
]


async def collect_news() -> int:
    """جمع الأخبار من NewsAPI"""
    settings = get_settings()
    if not settings.newsapi_key:
        logger.warning("مفتاح NewsAPI غير موجود")
        return 0

    count = 0
    session_factory = get_session_factory()
    if not session_factory:
        return 0

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for query in SEARCH_QUERIES:
                for lang in ["en", "ar"]:
                    try:
                        params = {
                            "q": query,
                            "sortBy": "publishedAt",
                            "pageSize": 20,
                            "language": lang,
                            "apiKey": settings.newsapi_key,
                        }

                        response = await client.get(NEWSAPI_URL, params=params)
                        if response.status_code != 200:
                            continue

                        data = response.json()
                        articles = data.get("articles", [])

                        async with session_factory() as session:
                            for article in articles:
                                try:
                                    url = article.get("url", "")
                                    source_id = f"newsapi_{hashlib.md5(url.encode()).hexdigest()}"

                                    title = article.get("title", "")
                                    description = article.get("description", "")
                                    category, severity = classify(title, description)
                                    country_code, country_name, lat, lon = geolocate(title, description)

                                    inserted = await insert_event_if_new(
                                        session,
                                        source="newsapi",
                                        source_id=source_id,
                                        title=title,
                                        description=description,
                                        url=url,
                                        image_url=article.get("urlToImage", ""),
                                        category=category,
                                        severity=severity,
                                        latitude=lat,
                                        longitude=lon,
                                        country=country_name,
                                        country_code=country_code,
                                        location_name=article.get("source", {}).get("name", ""),
                                        event_date=_parse_date(article.get("publishedAt")),
                                        extra_data=json.dumps({
                                            "author": article.get("author", ""),
                                            "source_name": article.get("source", {}).get("name", ""),
                                            "language": lang,
                                        }),
                                    )
                                    if inserted:
                                        count += 1

                                except Exception as e:
                                    logger.error(f"خطأ في مقال: {e}")
                                    continue

                            await session.commit()

                    except Exception as e:
                        logger.error(f"خطأ في استعلام '{query[:30]}' ({lang}): {e}")
                        continue

    except Exception as e:
        logger.error(f"خطأ عام في NewsAPI: {e}")

    logger.info(f"NewsAPI: تم جمع {count} خبر جديد")
    return count



def _parse_date(date_str: str) -> datetime:
    """تحويل تاريخ ISO"""
    if date_str:
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass
    return datetime.now(timezone.utc)
