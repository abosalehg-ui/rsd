"""رصد - جامع خلاصات RSS
يجمع الأخبار من مصادر RSS عربية ودولية
مع دعم خاص لأخبار النووي ☣️
"""
import feedparser
import httpx
import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
from ..models.database import Event, get_session_factory

logger = logging.getLogger("rasad.rss")

# ===== خلاصات RSS =====

RSS_FEEDS = {
    # ☣️ أخبار نووية
    "nuclear": [
        {
            "name": "World Nuclear News",
            "url": "https://www.world-nuclear-news.org/rss",
            "category": "nuclear",
            "icon": "☣️",
        },
        {
            "name": "IAEA News",
            "url": "https://www.iaea.org/feeds/topnews",
            "category": "nuclear",
            "icon": "☣️",
        },
        {
            "name": "Arms Control Association",
            "url": "https://www.armscontrol.org/rss.xml",
            "category": "nuclear",
            "icon": "☣️",
        },
    ],
    # 📰 أخبار عربية
    "arabic_news": [
        {
            "name": "الجزيرة - أخبار عاجلة",
            "url": "https://www.aljazeera.net/aljazeerarss/a7c186be-1baa-4bd4-9d80-a84db769f779/73d0e1b4-532f-45ef-b135-bfdff8b8cab9",
            "category": "general",
        },
        {
            "name": "العربية",
            "url": "https://english.alarabiya.net/feed/rss2/en.xml",
            "category": "general",
        },
        {
            "name": "BBC Arabic",
            "url": "https://feeds.bbci.co.uk/arabic/rss.xml",
            "category": "general",
        },
        {
            "name": "Al Jazeera English",
            "url": "https://www.aljazeera.com/xml/rss/all.xml",
            "category": "general",
        },
        {
            "name": "BBC Middle East",
            "url": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
            "category": "general",
        },
        {
            "name": "France24 Arabic",
            "url": "https://www.france24.com/ar/middle-east/rss",
            "category": "general",
        },
        {
            "name": "Sky News Arabia",
            "url": "https://www.skynewsarabia.com/web/rss",
            "category": "general",
        },
        {
            "name": "RT Arabic",
            "url": "https://arabic.rt.com/rss/",
            "category": "general",
        },
    ],
    # 🌍 تحليلات دولية
    "analysis": [
        {
            "name": "Al-Monitor",
            "url": "https://www.al-monitor.com/rss",
            "category": "diplomatic",
        },
        {
            "name": "Defense One",
            "url": "https://www.defenseone.com/rss/all/",
            "category": "military",
        },
        {
            "name": "War on the Rocks",
            "url": "https://warontherocks.com/feed/",
            "category": "military",
        },
        {
            "name": "The Drive - War Zone",
            "url": "https://www.thedrive.com/the-war-zone/rss",
            "category": "military",
        },
        {
            "name": "Breaking Defense",
            "url": "https://breakingdefense.com/feed/",
            "category": "military",
        },
    ],
    # 🔔 تنبيهات جوجل
    "google_alerts": [
        {"name": "GA - Middle East Airstrikes", "url": "https://www.google.com/alerts/feeds/03099333582095282205/11659520722795202396", "category": "military", "icon": "🔔"},
        {"name": "GA - الشرق الأوسط قصف", "url": "https://www.google.com/alerts/feeds/03099333582095282205/5316973900883303604", "category": "military", "icon": "🔔"},
        {"name": "GA - Gaza Yemen Syria", "url": "https://www.google.com/alerts/feeds/03099333582095282205/3704117853613500610", "category": "military", "icon": "🔔"},
        {"name": "GA - Houthi حوثي", "url": "https://www.google.com/alerts/feeds/03099333582095282205/4862309048616988909", "category": "military", "icon": "🔔"},
        {"name": "GA - Red Sea", "url": "https://www.google.com/alerts/feeds/03099333582095282205/17256916378475925143", "category": "military", "icon": "🔔"},
        {"name": "GA - Iran Nuclear", "url": "https://www.google.com/alerts/feeds/03099333582095282205/3683748354562264", "category": "nuclear", "icon": "🔔☣️"},
        {"name": "GA - تخصيب يورانيوم", "url": "https://www.google.com/alerts/feeds/03099333582095282205/11383354201955942199", "category": "nuclear", "icon": "🔔☣️"},
        {"name": "GA - Ceasefire Peace", "url": "https://www.google.com/alerts/feeds/03099333582095282205/17652965731898852232", "category": "diplomatic", "icon": "🔔"},
        {"name": "GA - هدنة مفاوضات", "url": "https://www.google.com/alerts/feeds/03099333582095282205/12614443505161566016", "category": "diplomatic", "icon": "🔔"},
        {"name": "GA - Gulf Diplomatic", "url": "https://www.google.com/alerts/feeds/03099333582095282205/7725246414336098267", "category": "diplomatic", "icon": "🔔"},
        {"name": "GA - Humanitarian Crisis", "url": "https://www.google.com/alerts/feeds/03099333582095282205/17364646303340517861", "category": "humanitarian", "icon": "🔔"},
        {"name": "GA - أزمة إنسانية", "url": "https://www.google.com/alerts/feeds/03099333582095282205/8365977631792071341", "category": "humanitarian", "icon": "🔔"},
    ],
}


async def collect_rss_feeds() -> int:
    """جمع الأخبار من جميع خلاصات RSS"""
    count = 0
    session_factory = get_session_factory()
    if not session_factory:
        return 0

    all_feeds = []
    for category_feeds in RSS_FEEDS.values():
        all_feeds.extend(category_feeds)

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        for feed_config in all_feeds:
            try:
                feed_count = await _process_feed(client, feed_config)
                count += feed_count
            except Exception as e:
                logger.error(f"خطأ في خلاصة {feed_config['name']}: {e}")
                continue

    logger.info(f"RSS: تم جمع {count} خبر جديد من {len(all_feeds)} خلاصة")
    return count


async def _process_feed(client: httpx.AsyncClient, feed_config: Dict) -> int:
    """معالجة خلاصة RSS واحدة"""
    count = 0
    session_factory = get_session_factory()

    try:
        response = await client.get(feed_config["url"])
        if response.status_code != 200:
            logger.warning(f"RSS {feed_config['name']}: HTTP {response.status_code}")
            return 0

        feed = feedparser.parse(response.text)

        async with session_factory() as session:
            for entry in feed.entries[:20]:  # أحدث 20 مقال
                try:
                    title = entry.get("title", "").strip()
                    if not title:
                        continue

                    link = entry.get("link", "")
                    source_id = f"rss_{hashlib.md5(link.encode()).hexdigest()}"

                    from sqlalchemy import select
                    existing = await session.execute(
                        select(Event).where(Event.source_id == source_id)
                    )
                    if existing.scalar_one_or_none():
                        continue

                    description = entry.get("summary", entry.get("description", ""))
                    # تنظيف HTML
                    import re
                    description = re.sub(r'<[^>]+>', '', description)[:500]

                    # التصنيف
                    base_category = feed_config.get("category", "general")
                    category, severity = _classify_rss(title, description, base_category)

                    # الموقع
                    country_code, country_name, lat, lon = _geolocate_rss(title, description)

                    # الصورة
                    image_url = ""
                    if hasattr(entry, "media_content") and entry.media_content:
                        image_url = entry.media_content[0].get("url", "")
                    elif hasattr(entry, "enclosures") and entry.enclosures:
                        image_url = entry.enclosures[0].get("href", "")

                    # التاريخ
                    event_date = datetime.now(timezone.utc)
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        try:
                            from time import mktime
                            event_date = datetime.fromtimestamp(
                                mktime(entry.published_parsed), tz=timezone.utc
                            )
                        except (TypeError, ValueError, OverflowError):
                            pass

                    icon = feed_config.get("icon", "")
                    display_title = f"{icon} {title}" if icon else title

                    event = Event(
                        source="rss",
                        source_id=source_id,
                        title=display_title,
                        description=description,
                        url=link,
                        image_url=image_url,
                        category=category,
                        severity=severity,
                        latitude=lat,
                        longitude=lon,
                        country=country_name,
                        country_code=country_code,
                        location_name=feed_config["name"],
                        event_date=event_date,
                        extra_data=json.dumps({
                            "feed_name": feed_config["name"],
                            "feed_category": base_category,
                            "is_nuclear": category == "nuclear",
                        }),
                    )

                    session.add(event)
                    count += 1

                except Exception as e:
                    logger.error(f"خطأ في مقال RSS: {e}")
                    continue

            await session.commit()

    except Exception as e:
        logger.error(f"خطأ في جلب {feed_config['name']}: {e}")

    return count


def _classify_rss(title: str, description: str, base_category: str) -> tuple:
    """تصنيف خبر RSS"""
    if base_category == "nuclear":
        return "nuclear", "high"

    text = f"{title} {description}".lower()

    nuclear_kw = ["nuclear", "uranium", "enrichment", "iaea", "atomic", "reactor",
                  "نووي", "يورانيوم", "تخصيب", "مفاعل", "ذري"]
    if any(kw in text for kw in nuclear_kw):
        return "nuclear", "high"

    military_kw = ["attack", "strike", "bomb", "missile", "war", "troops", "drone",
                   "killed", "هجوم", "قصف", "صاروخ", "غارة", "حرب", "قتل"]
    if any(kw in text for kw in military_kw):
        return "military", "high"

    diplomatic_kw = ["ceasefire", "peace", "diplomat", "negotiate", "summit",
                     "هدنة", "سلام", "دبلوماسي", "مفاوضات", "قمة"]
    if any(kw in text for kw in diplomatic_kw):
        return "diplomatic", "medium"

    humanitarian_kw = ["humanitarian", "refugee", "aid", "إنساني", "لاجئ", "إغاثة"]
    if any(kw in text for kw in humanitarian_kw):
        return "humanitarian", "medium"

    return base_category, "medium"


# نفس إحداثيات الدول
COUNTRY_COORDS = {
    "PS": (31.5, 34.47, "فلسطين"), "IL": (31.77, 35.23, "إسرائيل"),
    "YE": (15.55, 48.52, "اليمن"), "SY": (34.8, 38.99, "سوريا"),
    "LB": (33.87, 35.51, "لبنان"), "IR": (35.69, 51.39, "إيران"),
    "IQ": (33.31, 44.37, "العراق"), "SA": (24.71, 46.68, "السعودية"),
    "EG": (30.04, 31.24, "مصر"), "JO": (31.95, 35.93, "الأردن"),
    "TR": (39.93, 32.86, "تركيا"),
}


def _geolocate_rss(title: str, description: str) -> tuple:
    """تحديد الموقع"""
    text = f"{title} {description}".lower()
    country_keywords = {
        "PS": ["gaza", "palestine", "west bank", "غزة", "فلسطين"],
        "IL": ["israel", "tel aviv", "إسرائيل"],
        "YE": ["yemen", "houthi", "اليمن", "حوثي"],
        "SY": ["syria", "damascus", "سوريا", "دمشق"],
        "LB": ["lebanon", "beirut", "hezbollah", "لبنان", "بيروت"],
        "IR": ["iran", "tehran", "إيران", "طهران"],
        "IQ": ["iraq", "baghdad", "العراق", "بغداد"],
        "SA": ["saudi", "riyadh", "السعودية", "الرياض"],
        "EG": ["egypt", "cairo", "مصر", "القاهرة"],
        "JO": ["jordan", "الأردن"],
        "TR": ["turkey", "تركيا"],
    }
    for code, keywords in country_keywords.items():
        if any(kw in text for kw in keywords):
            coords = COUNTRY_COORDS.get(code, (0, 0, ""))
            return code, coords[2], coords[0], coords[1]
    return "", "", None, None
