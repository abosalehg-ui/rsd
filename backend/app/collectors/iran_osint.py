"""رصد - جامع أحداث إيران OSINT
يجمع الضربات والإطلاقات والتحركات العسكرية مع تصنيف الثقة HIGH/MEDIUM/LOW
"""
import feedparser
import httpx
import json
import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import List, Dict, Tuple
from ..models.database import Event, IranianLeaderNews, get_session_factory
from sqlalchemy import select

logger = logging.getLogger("rasad.iran_osint")

# ===== تصنيف الثقة بالمصادر =====
# HIGH = مصادر موثوقة ومتخصصة
# MEDIUM = صحفيون ومصادر دفاعية
# LOW = أخبار عامة أو غير موثقة

IRAN_OSINT_FEEDS = [
    # HIGH CONFIDENCE - مصادر OSINT متخصصة
    {
        "name": "ISW - Institute for the Study of War",
        "url": "https://www.understandingwar.org/rss.xml",
        "confidence": "HIGH",
        "icon": "🎯",
    },
    {
        "name": "Calibre Obscura",
        "url": "https://calibreobscura.com/feed/",
        "confidence": "HIGH",
        "icon": "🎯",
    },
    {
        "name": "The Drive - War Zone",
        "url": "https://www.thedrive.com/the-war-zone/rss",
        "confidence": "HIGH",
        "icon": "🎯",
    },
    {
        "name": "OSINTdefender (via Nitter RSS)",
        "url": "https://nitter.poast.org/OSINTdefender/rss",
        "confidence": "HIGH",
        "icon": "🎯",
    },
    # MEDIUM CONFIDENCE - صحافة دفاعية
    {
        "name": "Breaking Defense",
        "url": "https://breakingdefense.com/feed/",
        "confidence": "MEDIUM",
        "icon": "📡",
    },
    {
        "name": "Defense One",
        "url": "https://www.defenseone.com/rss/all/",
        "confidence": "MEDIUM",
        "icon": "📡",
    },
    {
        "name": "Al-Monitor - Iran",
        "url": "https://www.al-monitor.com/rss",
        "confidence": "MEDIUM",
        "icon": "📡",
    },
    {
        "name": "Iran International",
        "url": "https://www.iranintl.com/en/rss",
        "confidence": "MEDIUM",
        "icon": "📡",
    },
    # LOW CONFIDENCE - أخبار عامة
    {
        "name": "Reuters - Middle East",
        "url": "https://feeds.reuters.com/Reuters/worldNews",
        "confidence": "LOW",
        "icon": "📰",
    },
    {
        "name": "BBC - Middle East",
        "url": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
        "confidence": "LOW",
        "icon": "📰",
    },
]

# قائمة القادة الإيرانيين للمتابعة
IRANIAN_LEADERS = [
    {"id": 1, "name": "علي خامنئي", "name_en": "Ali Khamenei", "role": "المرشد الأعلى", "role_en": "Supreme Leader", "icon": "👤", "keywords": ["khamenei", "خامنئي"]},
    {"id": 2, "name": "مسعود بزشكيان", "name_en": "Masoud Pezeshkian", "role": "الرئيس", "role_en": "President", "icon": "👤", "keywords": ["pezeshkian", "بزشكيان"]},
    {"id": 3, "name": "حسين سلامي", "name_en": "Hossein Salami", "role": "قائد الحرس الثوري", "role_en": "IRGC Commander", "icon": "⚔️", "keywords": ["salami", "سلامي", "irgc commander"]},
    {"id": 4, "name": "محمد باقري", "name_en": "Mohammad Bagheri", "role": "رئيس الأركان", "role_en": "Chief of Staff", "icon": "⚔️", "keywords": ["bagheri", "باقري", "chief of staff iran"]},
    {"id": 5, "name": "أمير علي حاجي زاده", "name_en": "Amir Ali Hajizadeh", "role": "قائد الفضاء IRGC", "role_en": "IRGC Aerospace", "icon": "🚀", "keywords": ["hajizadeh", "حاجي زاده", "irgc aerospace"]},
    {"id": 6, "name": "عباس عراقچي", "name_en": "Abbas Araghchi", "role": "وزير الخارجية", "role_en": "Foreign Minister", "icon": "🤝", "keywords": ["araghchi", "عراقچي", "iran foreign minister"]},
    {"id": 7, "name": "إسماعيل قاآني", "name_en": "Ismail Qaani", "role": "قائد قوة القدس", "role_en": "Quds Force Commander", "icon": "⚔️", "keywords": ["qaani", "قاآني", "quds force"]},
    {"id": 8, "name": "محمد إسلامي", "name_en": "Mohammad Eslami", "role": "رئيس منظمة الطاقة الذرية", "role_en": "AEOI Chief", "icon": "☢️", "keywords": ["eslami", "إسلامي", "atomic energy iran"]},
    {"id": 9, "name": "عزيز نصيرزاده", "name_en": "Aziz Nasirzadeh", "role": "قائد سلاح الجو", "role_en": "Air Force Commander", "icon": "✈️", "keywords": ["nasirzadeh", "نصيرزاده", "iran air force"]},
    {"id": 10, "name": "علي شمخاني", "name_en": "Ali Shamkhani", "role": "مستشار المرشد", "role_en": "Supreme Leader Advisor", "icon": "👤", "keywords": ["shamkhani", "شمخاني"]},
]

# الكلمات المفتاحية للضربات والإطلاقات
STRIKE_KEYWORDS = [
    "strike", "airstrike", "missile", "bomb", "explosion", "attack", "launch",
    "drone attack", "ballistic", "cruise missile", "rocket", "shahab", "fateh",
    "ضربة", "صاروخ", "قصف", "انفجار", "هجوم", "إطلاق", "مسيّرة",
]

LAUNCH_KEYWORDS = [
    "launch", "fired", "launched", "test", "missile test", "ballistic missile",
    "irbm", "icbm", "hypersonic", "shahab", "sajjil", "emad",
    "أُطلق", "اختبار", "صاروخ باليستي",
]

MILITARY_MOVE_KEYWORDS = [
    "deploy", "exercise", "troops", "warship", "submarine", "military movement",
    "irgc", "pasdaran", "revolutionary guard", "naval", "drills",
    "نشر", "مناورة", "قوات", "حرس ثوري", "بحرية",
]

# مواقع إيران الرئيسية للأحداث
IRAN_LOCATIONS = {
    "tehran": (35.6892, 51.3890, "طهران", "IR"),
    "isfahan": (32.6539, 51.6660, "أصفهان", "IR"),
    "natanz": (33.7265, 51.7269, "نطنز", "IR"),
    "fordow": (34.8846, 50.5765, "فردو", "IR"),
    "bushehr": (28.9684, 50.8385, "بوشهر", "IR"),
    "arak": (34.0954, 49.6890, "أراك", "IR"),
    "tabriz": (38.0800, 46.2919, "تبريز", "IR"),
    "ahvaz": (31.3183, 48.6706, "الأهواز", "IR"),
    "bandar abbas": (27.1832, 56.2666, "بندر عباس", "IR"),
    "strait of hormuz": (26.5667, 56.2500, "مضيق هرمز", "IR"),
    "persian gulf": (26.0000, 54.0000, "الخليج العربي", "IR"),
}


async def collect_iran_osint() -> int:
    """جمع أحداث إيران OSINT من المصادر المتخصصة"""
    count = 0
    session_factory = get_session_factory()
    if not session_factory:
        return 0

    async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
        for feed_config in IRAN_OSINT_FEEDS:
            try:
                feed_count = await _process_iran_feed(client, feed_config)
                count += feed_count
            except Exception as e:
                logger.error(f"خطأ في {feed_config['name']}: {e}")
                continue

    logger.info(f"Iran OSINT: تم جمع {count} حدث جديد")
    return count


async def _process_iran_feed(client: httpx.AsyncClient, feed_config: Dict) -> int:
    count = 0
    session_factory = get_session_factory()

    try:
        response = await client.get(feed_config["url"])
        if response.status_code != 200:
            return 0

        feed = feedparser.parse(response.text)

        async with session_factory() as session:
            for entry in feed.entries[:15]:
                try:
                    title = entry.get("title", "").strip()
                    if not title:
                        continue

                    description = entry.get("summary", entry.get("description", ""))
                    description = re.sub(r'<[^>]+>', '', description)[:600]
                    text = f"{title} {description}".lower()

                    # تصفية: فقط الأحداث المتعلقة بإيران أو الشرق الأوسط
                    iran_related = any(kw in text for kw in [
                        "iran", "irgc", "tehran", "إيران", "حرس ثوري",
                        "middle east", "israel", "gaza", "yemen", "houthi",
                        "hezbollah", "syria", "iraq", "saudi", "hormuz",
                    ])
                    if not iran_related:
                        continue

                    # تحديد نوع الحدث
                    event_subtype, category = _classify_iran_event(text)
                    if not event_subtype:
                        continue

                    link = entry.get("link", "")
                    source_id = f"iran_{hashlib.md5(link.encode()).hexdigest()}"

                    existing = await session.execute(
                        select(Event).where(Event.source_id == source_id)
                    )
                    if existing.scalar_one_or_none():
                        continue

                    # الموقع
                    lat, lon, location_name, country_code = _geolocate_iran(text)

                    # التاريخ
                    event_date = datetime.now(timezone.utc)
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        try:
                            from time import mktime
                            event_date = datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
                        except Exception:
                            pass

                    # رابط الفيديو (إذا وجد)
                    video_url = ""
                    if hasattr(entry, "media_content"):
                        for m in entry.get("media_content", []):
                            if "video" in m.get("type", ""):
                                video_url = m.get("url", "")
                                break

                    # حدة الخطورة بناءً على نوع الحدث
                    severity = "high" if event_subtype in ["strike", "launch"] else "medium"
                    if feed_config["confidence"] == "HIGH":
                        severity = "critical" if event_subtype == "strike" else severity

                    icon = feed_config.get("icon", "📡")
                    conf = feed_config["confidence"]
                    conf_icon = "🟢" if conf == "HIGH" else "🟡" if conf == "MEDIUM" else "🔵"

                    event = Event(
                        source="iran_osint",
                        source_id=source_id,
                        title=f"{icon} {title}",
                        description=description,
                        url=link,
                        video_url=video_url,
                        category=category,
                        severity=severity,
                        confidence=conf,
                        event_type=event_subtype,
                        latitude=lat,
                        longitude=lon,
                        country=location_name or "إيران / الشرق الأوسط",
                        country_code=country_code or "IR",
                        location_name=location_name,
                        event_date=event_date,
                        extra_data=json.dumps({
                            "feed_name": feed_config["name"],
                            "confidence": conf,
                            "confidence_icon": conf_icon,
                            "event_subtype": event_subtype,
                            "is_iran_osint": True,
                        }),
                    )
                    session.add(event)
                    count += 1

                    # تحقق من ذكر القادة
                    await _check_leader_mentions(session, title, description, link, event_date)

                except Exception as e:
                    logger.error(f"خطأ في مقال: {e}")
                    continue

            await session.commit()

    except Exception as e:
        logger.error(f"خطأ في جلب {feed_config['name']}: {e}")

    return count


def _classify_iran_event(text: str) -> Tuple[str, str]:
    """تصنيف نوع الحدث الإيراني"""
    if any(kw in text for kw in STRIKE_KEYWORDS):
        return "strike", "military"
    if any(kw in text for kw in LAUNCH_KEYWORDS):
        return "launch", "military"
    if any(kw in text for kw in MILITARY_MOVE_KEYWORDS):
        return "movement", "military"
    if any(kw in text for kw in ["nuclear", "uranium", "enrichment", "iaea", "نووي", "يورانيوم"]):
        return "nuclear", "nuclear"
    if any(kw in text for kw in ["sanction", "negotiat", "deal", "talk", "ceasefire", "عقوبات", "مفاوضات"]):
        return "diplomatic", "diplomatic"
    # إذا ذكر إيران لكن لا يتطابق مع أي نوع محدد
    return None, None


def _geolocate_iran(text: str) -> Tuple:
    """تحديد الموقع الجغرافي للحدث الإيراني"""
    for loc_key, (lat, lon, name_ar, code) in IRAN_LOCATIONS.items():
        if loc_key in text:
            return lat, lon, name_ar, code

    # مواقع دول الشرق الأوسط
    other_locations = {
        "israel": (31.7683, 35.2137, "إسرائيل", "IL"),
        "gaza": (31.5002, 34.4668, "غزة", "PS"),
        "lebanon": (33.8886, 35.4955, "لبنان", "LB"),
        "syria": (33.5138, 36.2765, "سوريا", "SY"),
        "iraq": (33.3152, 44.3661, "العراق", "IQ"),
        "yemen": (15.5527, 48.5164, "اليمن", "YE"),
        "saudi": (24.7136, 46.6753, "السعودية", "SA"),
        "red sea": (20.0000, 38.0000, "البحر الأحمر", "YE"),
    }
    for loc_key, (lat, lon, name_ar, code) in other_locations.items():
        if loc_key in text:
            return lat, lon, name_ar, code

    return 35.6892, 51.3890, "إيران", "IR"


async def _check_leader_mentions(session, title: str, description: str, url: str, event_date: datetime):
    """تحقق من ذكر القادة الإيرانيين في الخبر"""
    text = f"{title} {description}".lower()
    for leader in IRANIAN_LEADERS:
        if any(kw in text for kw in leader["keywords"]):
            try:
                news = IranianLeaderNews(
                    leader_id=leader["id"],
                    leader_name=leader["name_en"],
                    title=title[:300],
                    url=url,
                    news_date=event_date,
                )
                session.add(news)
            except Exception:
                pass


def get_leaders_list() -> List[Dict]:
    """إرجاع قائمة القادة الإيرانيين"""
    return IRANIAN_LEADERS