"""رصد - جامع أحداث إيران OSINT
يجمع الضربات والإطلاقات والتحركات العسكرية مع تصنيف الثقة HIGH/MEDIUM/LOW.

المطابقة كلها بحدود الكلمة (`processors.matching.KeywordSet`) والموقع من
المعجم المشترك (`processors.gazetteer`) — لا بحث عن جزء نص: «Barakah» تحوي
«arak» و«الإسلامية» تحوي «إسلامي»، فالبحث بجزء النص يضع محطة براكة الإماراتية
في أراك ويُنسب كل خبر عن الجمهورية الإسلامية لرئيس منظمة الطاقة الذرية.

الخلاصات التي تحمل `category` إقليمية عامة مسجّلة هنا وحدها (لا في جامع RSS
أيضًا، وإلا خُزّن مقالها مرتين بمعرّفين): ما يُصنَّف حدثًا إيرانيًا يُخزَّن
بثقته ونوعه، وما لا يُصنَّف يُخزَّن خبر RSS عاديًا بتصنيف الخلاصة.
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import httpx

from ..models.database import IranianLeaderNews, get_session_factory, insert_event_if_new
from ..processors.dates import parse_entry_date
from ..processors.gazetteer import locate
from ..processors.matching import KeywordSet
from ..processors.normalize import normalize_for_match
from ..processors.text_analysis import analyze, event_fields
from ..static_data import iranian_leaders
from ._feed_base import (
    FEED_HEADERS,
    clean_html,
    clean_title,
    make_source_id,
    parse_feed_async,
    process_feeds,
)
from .rss_feeds import store_rss_entry

logger = logging.getLogger("rasad.iran_osint")

_ENTRY_CAP = 15
_DESC_CAP = 600

# ===== تصنيف الثقة بالمصادر =====
# HIGH = مصادر OSINT متخصصة موثوقة
# MEDIUM = صحافة دفاعية
# LOW = أخبار عامة
#
# `category` = الخلاصة تُغطّي المنطقة عمومًا لا إيران وحدها؛ ما لا يُصنَّف
# حدثًا إيرانيًا يُخزَّن خبر RSS عاديًا بهذا التصنيف بدل إسقاطه.
#
# الروابط مُتحقَّق من حيويّتها في 2026-09 (يفحصها CI أسبوعيًا:
# .github/workflows/feed-health.yml).

IRAN_OSINT_FEEDS = [
    # HIGH CONFIDENCE - مصادر OSINT متخصصة
    {
        "name": "The War Zone (TWZ)",
        "url": "https://www.twz.com/feed",
        "confidence": "HIGH",
        "icon": "🎯",
        "category": "military",
    },
    {
        "name": "Bellingcat",
        "url": "https://www.bellingcat.com/feed/",
        "confidence": "HIGH",
        "icon": "🎯",
    },
    {
        "name": "FDD's Long War Journal",
        "url": "https://www.longwarjournal.org/feed",
        "confidence": "HIGH",
        "icon": "🎯",
    },
    {
        "name": "Oryx",
        "url": "https://www.oryxspioenkop.com/feeds/posts/default",
        "confidence": "HIGH",
        "icon": "🎯",
    },
    # MEDIUM CONFIDENCE - صحافة دفاعية
    # (Al-Monitor يردّ 403 لعملاء بايثون — جدار حماية ببصمة TLS — وIran
    #  International تعيد صفحة HTML لا RSS؛ أُزيلا حتى يعود لهما مسار خلاصة.)
    {
        "name": "Breaking Defense",
        "url": "https://breakingdefense.com/feed/",
        "confidence": "MEDIUM",
        "icon": "📡",
        "category": "military",
    },
    {
        "name": "Defense One",
        "url": "https://www.defenseone.com/rss/all/",
        "confidence": "MEDIUM",
        "icon": "📡",
        "category": "military",
    },
    # LOW CONFIDENCE - أخبار عامة
    {
        "name": "BBC - Middle East",
        "url": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
        "confidence": "LOW",
        "icon": "📰",
        "category": "general",
    },
]

#: قائمة القادة الإيرانيين — من `data/iranian_leaders.json` (مصدر واحد مع الـ API)
IRANIAN_LEADERS: List[Dict] = iranian_leaders()

#: مطابقات القادة بحدود الكلمة، مُترجمة مرة واحدة
_LEADER_MATCHERS: list[tuple[Dict, KeywordSet]] = [
    (leader, KeywordSet(leader["keywords"])) for leader in IRANIAN_LEADERS
]

# الكلمات المفتاحية للضربات والإطلاقات — بحدود كلمة (matching.KeywordSet)،
# فلا تطابق "test" كلمتي "latest" و"protest".
STRIKE_KEYWORDS = KeywordSet([
    "strike", "airstrike", "missile", "bomb", "explosion", "attack", "launch",
    "drone attack", "ballistic", "cruise missile", "rocket", "shahab", "fateh",
    "ضربة", "صاروخ", "قصف", "انفجار", "هجوم", "إطلاق", "مسيّرة",
])

LAUNCH_KEYWORDS = KeywordSet([
    "launch", "fired", "launched", "test", "missile test", "ballistic missile",
    "irbm", "icbm", "hypersonic", "shahab", "sajjil", "emad",
    "أُطلق", "اختبار", "صاروخ باليستي",
])

MILITARY_MOVE_KEYWORDS = KeywordSet([
    "deploy", "exercise", "troops", "warship", "submarine", "military movement",
    "irgc", "pasdaran", "revolutionary guard", "naval", "drills",
    "نشر", "مناورة", "قوات", "حرس ثوري", "بحرية",
])

_REGION_KEYWORDS = KeywordSet([
    "iran", "irgc", "tehran", "إيران", "حرس ثوري", "الحرس الثوري",
    "middle east", "israel", "gaza", "yemen", "houthi", "houthis",
    "hezbollah", "syria", "iraq", "saudi", "hormuz", "gulf",
])
_NUCLEAR_KEYWORDS = KeywordSet(["nuclear", "uranium", "enrich*", "iaea", "نووي", "يورانيوم", "تخصيب"])
_DIPLOMATIC_KEYWORDS = KeywordSet([
    "sanction*", "negotiat*", "deal", "talks", "ceasefire", "عقوبات", "مفاوضات", "محادثات",
])

# الافتراضي عند تعذّر استخلاص أي موقع: طهران، بدقة «دولة» لأن الموقع مفترض لا مستخلص
_TEHRAN = (35.6892, 51.3890, "إيران", "IR")


async def collect_iran_osint() -> int:
    """جمع أحداث إيران OSINT (بتزامن محدود؛ يرفع إن فشلت كل الخلاصات)."""
    session_factory = get_session_factory()
    if not session_factory:
        return 0

    async with httpx.AsyncClient(timeout=25.0, follow_redirects=True, headers=FEED_HEADERS) as client:
        count = await process_feeds(client, IRAN_OSINT_FEEDS, _process_iran_feed, label="Iran OSINT")

    logger.info(f"Iran OSINT: تم جمع {count} حدث جديد")
    return count


async def _process_iran_feed(client: httpx.AsyncClient, feed_config: Dict) -> int:
    """معالجة خلاصة إيران واحدة. أخطاء الجلب/التحليل تُرفَع؛ أخطاء المقال تُبتلَع."""
    count = 0
    session_factory = get_session_factory()

    response = await client.get(feed_config["url"])
    if response.status_code != 200:
        # نرفع كي يعدّها `process_feeds` فشلًا — خطأ HTTP أشيع أشكال العطل،
        # وابتلاعه يجعل خلاصة ماتت منذ أسابيع بلا أثر في أي مكان.
        raise RuntimeError(f"Iran OSINT {feed_config['name']}: HTTP {response.status_code}")

    feed = await parse_feed_async(response.text)

    async with session_factory() as session:
        for entry in feed.entries[:_ENTRY_CAP]:
            try:
                if await _store_iran_entry(session, entry, feed_config):
                    count += 1
            except Exception as e:
                logger.error(f"خطأ في مقال: {e}")
                continue
        await session.commit()

    return count


async def _store_iran_entry(session, entry, feed_config: Dict) -> bool:
    """يحوّل إدخال خلاصة إيران إلى حدث ويُدرجه؛ يعيد True إن أُدرِج فعلاً.

    ما لا يُصنَّف حدثًا إيرانيًا يُخزَّن خبر RSS عاديًا إن حملت الخلاصة
    `category` (خلاصة إقليمية عامة)، وإلا يُتجاهل.
    """
    title, _ = clean_title(entry.get("title", ""))
    if not title:
        return False

    description = clean_html(entry.get("summary", entry.get("description", "")), _DESC_CAP)
    text = normalize_for_match(f"{title} {description}")

    # تصفية: فقط الأحداث المتعلقة بإيران أو الشرق الأوسط
    event_subtype, category = (None, None)
    if _REGION_KEYWORDS.matches(text):
        event_subtype, category = _classify_iran_event(text)
    if not event_subtype:
        return await _store_fallback(session, entry, feed_config)

    link = entry.get("link", "")
    lat, lon, location_name, country_code, precision = _locate_iran(f"{title} {description}")
    event_date = parse_entry_date(entry)

    video_url = ""
    if hasattr(entry, "media_content"):
        for m in entry.get("media_content", []):
            if "video" in m.get("type", ""):
                video_url = m.get("url", "")
                break

    severity = "high" if event_subtype in ["strike", "launch"] else "medium"
    if feed_config["confidence"] == "HIGH":
        severity = "critical" if event_subtype == "strike" else severity

    conf = feed_config["confidence"]
    conf_icon = "🟢" if conf == "HIGH" else "🟡" if conf == "MEDIUM" else "🔵"

    extra = {
        "feed_name": feed_config["name"],
        "source_name": feed_config["name"],
        "confidence": conf,
        "confidence_icon": conf_icon,
        "event_subtype": event_subtype,
        "is_iran_osint": True,
    }

    # الخبر النووي/الإشعاعي يُقيَّم بالمحرّك المشترك كي يظهر في الرصد النووي
    # بدرجة خطر محسوبة كبقية المصادر (ضربة على منشأة ≠ ضربة على مستودع).
    nuclear_fields: dict = {}
    analysis = analyze(title, description, source_kind="specialist" if conf == "HIGH" else "news")
    if analysis.is_nuclear:
        derived = event_fields(analysis)
        category, severity = derived["category"], derived["severity"]
        nuclear_fields = {k: derived[k] for k in ("topic", "risk_score", "facility_id")}
        extra.update(analysis.extra)
    extra["geo_precision"] = precision

    inserted = await insert_event_if_new(
        session,
        source="iran_osint",
        source_id=make_source_id("iran", link),
        title=title,
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
        country_code=country_code,
        location_name=location_name,
        event_date=event_date,
        geo_precision=precision,
        extra_data=json.dumps(extra, ensure_ascii=False),
        **nuclear_fields,
    )
    if not inserted:
        return False

    # تحقق من ذكر القادة (للأحداث الجديدة فقط) داخل savepoint كي لا يُفسد فشلُ
    # خبرِ قائدٍ إدراجَ الحدث نفسه.
    await _check_leader_mentions(session, title, description, link, event_date)
    return True


async def _store_fallback(session, entry, feed_config: Dict) -> bool:
    """خلاصة إقليمية عامة: المقال غير الإيراني يُخزَّن خبر RSS بتصنيف الخلاصة."""
    if not feed_config.get("category"):
        return False
    return await store_rss_entry(session, entry, {
        "name": feed_config["name"],
        "url": feed_config["url"],
        "category": feed_config["category"],
        "source_kind": "specialist" if feed_config["confidence"] == "HIGH" else "news",
    })


def _classify_iran_event(text: str) -> Tuple[Optional[str], Optional[str]]:
    """تصنيف نوع الحدث الإيراني — (النوع الفرعي، التصنيف) أو (None, None)
    إذا لم يطابق النص أي نوع معروف (فيُتجاهل الخبر)."""
    text = normalize_for_match(text)
    if STRIKE_KEYWORDS.matches(text):
        return "strike", "military"
    if LAUNCH_KEYWORDS.matches(text):
        return "launch", "military"
    if MILITARY_MOVE_KEYWORDS.matches(text):
        return "movement", "military"
    if _NUCLEAR_KEYWORDS.matches(text):
        return "nuclear", "nuclear"
    if _DIPLOMATIC_KEYWORDS.matches(text):
        return "diplomatic", "diplomatic"
    # إذا ذكر إيران لكن لا يتطابق مع أي نوع محدد
    return None, None


def _locate_iran(text: str) -> Tuple[float, float, str, str, str]:
    """(lat, lon, الاسم، رمز الدولة، الدقة) عبر المعجم المشترك.

    المعجم يعرف المواقع الإيرانية الدقيقة (نطنز، فوردو، بوشهر، بارشين…) بحدود
    كلمة، ويعيد رمز دولة فارغًا للمسطّحات المائية (هرمز، الخليج، البحر الأحمر)
    كي لا تُنسب لإيران فتضخّم مؤشرها. الافتراضي طهران بدقة «دولة».
    """
    loc = locate(text)
    if loc.lat is not None:
        return loc.lat, loc.lon, loc.place_name or loc.country_name, loc.country_code, loc.precision
    lat, lon, name, code = _TEHRAN
    return lat, lon, name, code, "country"


def _geolocate_iran(text: str) -> Tuple[float, float, str, str]:
    """(lat, lon, الاسم، رمز الدولة) — واجهة التوافق الخلفي فوق `_locate_iran`."""
    lat, lon, name, code, _ = _locate_iran(text)
    return lat, lon, name, code


def leaders_mentioned(title: str, description: str = "") -> List[Dict]:
    """القادة المذكورون بالاسم في النص — مطابقة بحدود الكلمة."""
    norm = normalize_for_match(f"{title} {description}")
    return [leader for leader, matcher in _LEADER_MATCHERS if matcher.matches(norm)]


async def _check_leader_mentions(session, title: str, description: str, url: str, event_date: datetime):
    """يربط الخبر بالقادة المذكورين فيه.

    نُدرج داخل savepoint (`begin_nested`) — session.add لا يرفع شيئاً، والفشل
    الفعلي يقع عند التنفيذ/commit؛ فالـsavepoint هو ما يحمي الحدث الأصلي من
    السقوط بسبب خبر قائد معطوب."""
    for leader in leaders_mentioned(title, description):
        try:
            async with session.begin_nested():
                session.add(IranianLeaderNews(
                    leader_id=leader["id"],
                    leader_name=leader["name_en"],
                    title=title[:300],
                    url=url,
                    news_date=event_date,
                ))
        except Exception as e:  # noqa: BLE001 - لا نُسقط الحدث بسبب خبر قائد
            logger.warning(f"تعذّر ربط خبر بالقائد {leader['name_en']}: {e}")


def get_leaders_list() -> List[Dict]:
    """إرجاع قائمة القادة الإيرانيين"""
    return IRANIAN_LEADERS
