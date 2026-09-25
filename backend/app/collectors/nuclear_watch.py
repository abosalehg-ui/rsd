"""رصد - جامع الرصد النووي والإشعاعي.

مصدران:

1. **خلاصات متخصصة** (الوكالة الدولية للطاقة الذرية، World Nuclear News،
   NucNet، ANS، NEI، رابطة الحدّ من التسلح، Arms Control Wonk). كل ما تنشره
   نووي بطبيعته، فيُقيَّم نوويًا حتى لو لم يذكر الكلمة (`force`)، ويُعامَل
   مصدرها `official`/`specialist` في درجة الخطر.

2. **بحث Google News** بالعربية والإنجليزية: يلتقط الأخبار الإقليمية
   (الصحف الخليجية والعربية، وبيانات هيئات الرقابة) التي لا تغطيها الخلاصات
   المتخصصة. نتائجه تمرّ ببوابة الصلة النووية — «الحمض النووي» مثلًا يُسقط —
   ومصدرها `aggregator`.

عناوين Google News بصيغة «العنوان - المصدر»؛ نفصل المصدر إلى `source_name`
كي يبقى العنوان نظيفًا للعرض والتجميع.
"""
from __future__ import annotations

import logging
from typing import Dict
from urllib.parse import quote

import httpx

from ..models.database import get_session_factory, insert_event_if_new
from ..processors.dates import parse_entry_date
from ._feed_base import (
    FEED_HEADERS,
    analyzed_fields,
    clean_html,
    clean_title,
    make_source_id,
    parse_feed_async,
    process_feeds,
)

logger = logging.getLogger("rasad.nuclear_watch")

_ENTRY_CAP = 25
_DESC_CAP = 600


def _google_news(query: str, lang: str) -> str:
    region = {"ar": ("ar", "SA", "SA:ar"), "en": ("en", "US", "US:en")}[lang]
    hl, gl, ceid = region
    return f"https://news.google.com/rss/search?q={quote(query)}&hl={hl}&gl={gl}&ceid={ceid}"


NUCLEAR_FEEDS: list[Dict] = [
    # ===== رسمي / متخصص =====
    {"name": "IAEA News", "url": "https://www.iaea.org/feeds/topnews",
     "kind": "official", "force": True},
    {"name": "World Nuclear News", "url": "https://www.world-nuclear-news.org/rss",
     "kind": "specialist", "force": True},
    {"name": "NucNet", "url": "https://www.nucnet.org/feed.rss",
     "kind": "specialist", "force": True},
    {"name": "ANS Nuclear Newswire", "url": "https://www.ans.org/news/feed/",
     "kind": "specialist", "force": True},
    {"name": "Nuclear Engineering International", "url": "https://www.neimagazine.com/rss/",
     "kind": "specialist", "force": True},
    # تحليل ورأي: موثوقة لكنها تناقش سيناريوهات، فمعامل ثقتها أدنى
    {"name": "Arms Control Association", "url": "https://www.armscontrol.org/rss.xml",
     "kind": "analysis", "force": True},
    {"name": "Arms Control Wonk", "url": "https://www.armscontrolwonk.com/feed/",
     "kind": "analysis", "force": True},
    # ===== بحث إقليمي عبر Google News (آخر يومين) =====
    {"name": "Google News · نووي/إشعاعي",
     "url": _google_news('(نووي OR إشعاعي OR "الطاقة الذرية" OR يورانيوم OR "مواد مشعة") when:2d', "ar"),
     "kind": "aggregator"},
    {"name": "Google News · الجهات الرقابية",
     "url": _google_news(
         '("هيئة الرقابة النووية والإشعاعية" OR "الرقابة النووية" OR "الهيئة الاتحادية للرقابة النووية" '
         'OR "هيئة الرقابة النووية والإشعاعية المصرية") when:7d', "ar"),
     "kind": "aggregator"},
    {"name": "Google News · Middle East nuclear",
     "url": _google_news(
         '(nuclear OR radiation OR radioactive OR IAEA OR uranium) '
         '(Iran OR Israel OR Saudi OR UAE OR Gulf OR Barakah OR Bushehr OR Egypt OR Turkey) when:2d', "en"),
     "kind": "aggregator"},
    {"name": "Google News · Radiological incidents",
     "url": _google_news(
         '("radioactive source" OR "radioactive material" OR "radiation leak" OR "dirty bomb") when:7d', "en"),
     "kind": "aggregator"},
]


async def collect_nuclear_watch() -> int:
    """جمع الأخبار النووية والإشعاعية (بتزامن محدود؛ يرفع إن فشلت كل الخلاصات)."""
    session_factory = get_session_factory()
    if not session_factory:
        return 0

    async with httpx.AsyncClient(timeout=25.0, follow_redirects=True, headers=FEED_HEADERS) as client:
        count = await process_feeds(client, NUCLEAR_FEEDS, _process_feed, label="Nuclear watch")

    logger.info(f"الرصد النووي: تم جمع {count} خبر جديد من {len(NUCLEAR_FEEDS)} خلاصة")
    return count


async def _process_feed(client: httpx.AsyncClient, feed_config: Dict) -> int:
    response = await client.get(feed_config["url"])
    if response.status_code != 200:
        raise RuntimeError(f"Nuclear watch {feed_config['name']}: HTTP {response.status_code}")

    feed = await parse_feed_async(response.text)
    count = 0
    session_factory = get_session_factory()
    async with session_factory() as session:
        for entry in feed.entries[:_ENTRY_CAP]:
            try:
                if await _store_entry(session, entry, feed_config):
                    count += 1
            except Exception as e:  # noqa: BLE001 - مقال معطوب لا يُسقط الخلاصة
                logger.error(f"خطأ في مقال نووي ({feed_config['name']}): {e}")
        await session.commit()
    return count


async def _store_entry(session, entry, feed_config: Dict) -> bool:
    publisher = ""
    source = entry.get("source")
    if isinstance(source, dict):
        publisher = source.get("title", "") or ""

    title, suffix = clean_title(entry.get("title", ""), publisher)
    if not title:
        return False
    publisher = publisher or suffix or feed_config["name"]

    # وصف Google News مجرد رابط مكرّر للعنوان — لا قيمة له
    description = "" if feed_config["kind"] == "aggregator" else clean_html(
        entry.get("summary", entry.get("description", "")), _DESC_CAP
    )

    fields, analysis = analyzed_fields(
        title, description,
        base_category="nuclear" if feed_config.get("force") else "general",
        source_kind=feed_config["kind"],
        extra={
            "feed_name": feed_config["name"],
            "source_name": publisher,
            "source_kind": feed_config["kind"],
        },
    )
    # بحث Google News واسع؛ ما لا يجتاز بوابة الصلة النووية ليس من شأن هذا الجامع
    if not analysis.is_nuclear:
        return False

    link = entry.get("link", "")
    return await insert_event_if_new(
        session,
        source="nuclear_watch",
        source_id=make_source_id("nuc", link),
        title=title,
        description=description,
        url=link,
        image_url="",
        location_name=analysis.location.place_name or publisher,
        event_date=parse_entry_date(entry),
        **fields,
    )
