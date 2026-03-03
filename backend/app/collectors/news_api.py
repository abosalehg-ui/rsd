"""رصد - جامع أخبار NewsAPI
يجمع الأخبار من مصادر عالمية عبر NewsAPI
"""
import hashlib
import httpx
import json
import logging
from datetime import datetime, timezone
from typing import List
from ..models.database import Event, get_session_factory
from ..config import get_settings

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

                                    from sqlalchemy import select
                                    existing = await session.execute(
                                        select(Event).where(Event.source_id == source_id)
                                    )
                                    if existing.scalar_one_or_none():
                                        continue

                                    title = article.get("title", "")
                                    description = article.get("description", "")
                                    category, severity = _classify_article(title, description)
                                    country_code, country_name, lat, lon = _geolocate(title, description)

                                    event = Event(
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

                                    session.add(event)
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


# إحداثيات مراكز الدول
COUNTRY_COORDS = {
    "PS": (31.5, 34.47, "فلسطين"), "IL": (31.77, 35.23, "إسرائيل"),
    "YE": (15.55, 48.52, "اليمن"), "SY": (34.8, 38.99, "سوريا"),
    "LB": (33.87, 35.51, "لبنان"), "IR": (35.69, 51.39, "إيران"),
    "IQ": (33.31, 44.37, "العراق"), "SA": (24.71, 46.68, "السعودية"),
    "EG": (30.04, 31.24, "مصر"), "JO": (31.95, 35.93, "الأردن"),
    "TR": (39.93, 32.86, "تركيا"), "LY": (32.9, 13.18, "ليبيا"),
    "SD": (15.59, 32.53, "السودان"),
}


def _classify_article(title: str, description: str) -> tuple:
    """تصنيف المقال"""
    text = f"{title} {description}".lower()

    nuclear_kw = ["nuclear", "uranium", "enrichment", "iaea", "atomic", "نووي", "تخصيب"]
    military_kw = ["attack", "strike", "bomb", "missile", "troops", "airstrike", "drone",
                   "kill", "dead", "هجوم", "قصف", "صاروخ", "غارة", "قتل"]
    diplomatic_kw = ["diplomat", "peace", "ceasefire", "negotiate", "summit", "treaty",
                     "دبلوماسي", "سلام", "هدنة", "مفاوضات"]
    humanitarian_kw = ["humanitarian", "refugee", "aid", "civilian", "displaced", "famine",
                       "إنساني", "لاجئ", "مساعدات", "مجاعة"]
    economic_kw = ["sanctions", "oil", "economic", "trade", "عقوبات", "نفط", "اقتصاد"]

    if any(kw in text for kw in nuclear_kw):
        return "nuclear", "high"
    if any(kw in text for kw in military_kw):
        return "military", "critical" if any(w in text for w in ["kill", "dead", "قتل"]) else "high"
    if any(kw in text for kw in diplomatic_kw):
        return "diplomatic", "medium"
    if any(kw in text for kw in humanitarian_kw):
        return "humanitarian", "medium"
    if any(kw in text for kw in economic_kw):
        return "economic", "low"

    return "general", "low"


def _geolocate(title: str, description: str) -> tuple:
    """تحديد الموقع الجغرافي من النص"""
    text = f"{title} {description}".lower()

    country_keywords = {
        "PS": ["gaza", "palestine", "west bank", "غزة", "فلسطين", "الضفة"],
        "IL": ["israel", "tel aviv", "jerusalem", "إسرائيل", "تل أبيب"],
        "YE": ["yemen", "houthi", "sanaa", "اليمن", "حوثي", "صنعاء"],
        "SY": ["syria", "damascus", "aleppo", "سوريا", "دمشق", "حلب"],
        "LB": ["lebanon", "beirut", "hezbollah", "لبنان", "بيروت", "حزب الله"],
        "IR": ["iran", "tehran", "إيران", "طهران"],
        "IQ": ["iraq", "baghdad", "العراق", "بغداد"],
        "SA": ["saudi", "riyadh", "السعودية", "الرياض"],
        "EG": ["egypt", "cairo", "sinai", "مصر", "القاهرة", "سيناء"],
        "JO": ["jordan", "amman", "الأردن", "عمان"],
        "TR": ["turkey", "ankara", "تركيا", "أنقرة"],
        "LY": ["libya", "tripoli", "ليبيا", "طرابلس"],
        "SD": ["sudan", "khartoum", "السودان", "الخرطوم"],
    }

    for code, keywords in country_keywords.items():
        if any(kw in text for kw in keywords):
            coords = COUNTRY_COORDS.get(code, (0, 0, ""))
            return code, coords[2], coords[0], coords[1]

    return "", "", None, None


def _parse_date(date_str: str) -> datetime:
    """تحويل تاريخ ISO"""
    if date_str:
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass
    return datetime.now(timezone.utc)
