"""رصد - جامع خلاصات RSS
يجمع الأخبار من مصادر RSS عربية ودولية
مع دعم خاص لأخبار النووي ☣️
"""
import json
import logging
from typing import Dict

import httpx

from ..config import get_settings
from ..models.database import get_session_factory, insert_event_if_new
from ..processors.dates import parse_entry_date
from ..processors.text_analysis import classify, geolocate
from ._feed_base import clean_html, make_source_id, parse_feed_async, process_feeds

logger = logging.getLogger("rasad.rss")

_ENTRY_CAP = 20        # أحدث 20 مقالاً لكل خلاصة
_DESC_CAP = 500

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
    # 🔔 تنبيهات جوجل — تُقرأ من GOOGLE_ALERT_FEEDS في .env وليس من المصدر.
    # روابط Google Alerts تتضمّن معرّف حساب المستخدم وتُعامَل كأسرار شخصية،
    # فلا يجوز تثبيتها في مستودع عام (راجع .env.example).
}


def _all_feeds() -> list[Dict]:
    """كل الخلاصات: الثابتة في المصدر + خلاصات Google Alerts من الإعدادات."""
    feeds: list[Dict] = []
    for category_feeds in RSS_FEEDS.values():
        feeds.extend(category_feeds)

    settings = get_settings()
    google_feeds = settings.google_alert_feeds_list
    configured = len([e for e in settings.google_alert_feeds.split(",") if e.strip()])
    if configured and len(google_feeds) < configured:
        logger.warning(
            f"GOOGLE_ALERT_FEEDS: تم تجاهل {configured - len(google_feeds)} مُدخلاً مشوّهاً "
            '(الصيغة المتوقّعة: "الاسم|التصنيف|https://…")'
        )
    feeds.extend(google_feeds)
    return feeds


async def collect_rss_feeds() -> int:
    """جمع الأخبار من جميع خلاصات RSS (بتزامن محدود؛ يرفع إن فشلت كلها)."""
    session_factory = get_session_factory()
    if not session_factory:
        return 0

    all_feeds = _all_feeds()

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        count = await process_feeds(client, all_feeds, _process_feed, label="RSS")

    logger.info(f"RSS: تم جمع {count} خبر جديد من {len(all_feeds)} خلاصة")
    return count


async def _process_feed(client: httpx.AsyncClient, feed_config: Dict) -> int:
    """معالجة خلاصة RSS واحدة. أخطاء الجلب/التحليل تُرفَع (يلتقطها process_feeds)؛
    أخطاء المقال الواحد تُبتلَع فلا تُسقط بقية الخلاصة."""
    count = 0
    session_factory = get_session_factory()

    response = await client.get(feed_config["url"])
    if response.status_code != 200:
        logger.warning(f"RSS {feed_config['name']}: HTTP {response.status_code}")
        return 0

    feed = await parse_feed_async(response.text)

    async with session_factory() as session:
        for entry in feed.entries[:_ENTRY_CAP]:
            try:
                if await _store_entry(session, entry, feed_config):
                    count += 1
            except Exception as e:
                logger.error(f"خطأ في مقال RSS: {e}")
                continue
        await session.commit()

    return count


async def _store_entry(session, entry, feed_config: Dict) -> bool:
    """يحوّل إدخال خلاصة إلى حدث ويُدرجه ذرّياً؛ يعيد True إن أُدرِج فعلاً."""
    title = entry.get("title", "").strip()
    if not title:
        return False

    link = entry.get("link", "")
    description = clean_html(entry.get("summary", entry.get("description", "")), _DESC_CAP)

    base_category = feed_config.get("category", "general")
    category, severity = classify(title, description, base_category)
    country_code, country_name, lat, lon = geolocate(title, description)

    image_url = ""
    if hasattr(entry, "media_content") and entry.media_content:
        image_url = entry.media_content[0].get("url", "")
    elif hasattr(entry, "enclosures") and entry.enclosures:
        image_url = entry.enclosures[0].get("href", "")

    icon = feed_config.get("icon", "")
    display_title = f"{icon} {title}" if icon else title

    return await insert_event_if_new(
        session,
        source="rss",
        source_id=make_source_id("rss", link),
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
        event_date=parse_entry_date(entry),
        extra_data=json.dumps({
            "feed_name": feed_config["name"],
            "feed_category": base_category,
            "is_nuclear": category == "nuclear",
        }),
    )

