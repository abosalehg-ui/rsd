"""رصد - جامع خلاصات RSS
يجمع الأخبار من مصادر RSS عربية ودولية
مع دعم خاص لأخبار النووي ☣️
"""
import hashlib
import json
import logging
import re
from typing import Dict

import feedparser
import httpx

from ..models.database import get_session_factory, insert_event_if_new
from ..processors.text_analysis import classify, geolocate, parse_entry_date

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


async def _process_feed(client: httpx.AsyncClient, feed_config: Dict) -> int:  # noqa: C901
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

                    description = entry.get("summary", entry.get("description", ""))
                    description = re.sub(r'<[^>]+>', '', description)[:500]

                    base_category = feed_config.get("category", "general")
                    category, severity = classify(title, description, base_category)
                    country_code, country_name, lat, lon = geolocate(title, description)

                    # الصورة
                    image_url = ""
                    if hasattr(entry, "media_content") and entry.media_content:
                        image_url = entry.media_content[0].get("url", "")
                    elif hasattr(entry, "enclosures") and entry.enclosures:
                        image_url = entry.enclosures[0].get("href", "")

                    event_date = parse_entry_date(entry)

                    icon = feed_config.get("icon", "")
                    display_title = f"{icon} {title}" if icon else title

                    inserted = await insert_event_if_new(
                        session,
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
                    if inserted:
                        count += 1

                except Exception as e:
                    logger.error(f"خطأ في مقال RSS: {e}")
                    continue

            await session.commit()

    except Exception as e:
        logger.error(f"خطأ في جلب {feed_config['name']}: {e}")

    return count

