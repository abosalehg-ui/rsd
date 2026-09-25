"""رصد - أساس مشترك لجامعي الخلاصات (RSS + Iran OSINT).

كان جامعا `rss_feeds` و`iran_osint` يكرّران ~60 سطراً متطابقة تقريباً (جلب →
تحليل → فتح جلسة → حلقة إدخالات → commit → معالجة أخطاء). هذه الوحدة تحمل
المنطق المشترك، فيكتفي كل جامع بدالة `mapper(entry, cfg) -> dict | None`
تحوّل إدخال الخلاصة إلى حقول حدث (أو None للتجاهل).

كما تعالج مشكلتين هيكليتين:
- `feedparser.parse` تحليل XML متزامن؛ نشغّله عبر `asyncio.to_thread` كي لا
  يحجب حلقة الأحداث ويجمّد بقية طلبات الـ API.
- الخلاصات كانت تُجلب تسلسلياً (16 خلاصة × مهلة 20s قد تتجاوز فاصل الجمع)؛
  نجلبها الآن بتزامن محدود عبر Semaphore.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Awaitable, Callable

import feedparser
import httpx

from ..processors.normalize import clean_text, split_source_suffix
from ..processors.text_analysis import Analysis, analyze, event_fields

logger = logging.getLogger("rasad.feeds")

# عدد الخلاصات المجلوبة بالتوازي — يوازن بين السرعة وعدم إغراق الشبكة/المزوّدين
_FEED_CONCURRENCY = 6


# ترويسة عامة: بعض الخوادم (IAEA، Google News) تردّ 403 على عميل بلا User-Agent
FEED_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Rasad-OSINT/2.0)"}


def clean_html(raw: str, cap: int) -> str:
    """نص صالح للعرض: كيانات مفكوكة، بلا وسوم، مقتطع إلى `cap` حرفًا.

    كانت تزيل الوسوم فقط ولا تفكّ الكيانات، والعناوين لم تمرّ بها أصلًا —
    فظهرت `&quot;` و`<b>` في شريط الأخبار العاجلة."""
    return clean_text(raw, cap)


def clean_title(raw: str, known_source: str = "") -> tuple[str, str]:
    """(عنوان نظيف، اسم مصدر مفصول من لاحقته إن وُجد)."""
    return split_source_suffix(clean_text(raw, 500), known_source)


def analyzed_fields(
    title: str,
    description: str = "",
    *,
    base_category: str = "general",
    source_kind: str = "news",
    extra: dict | None = None,
) -> tuple[dict, Analysis]:
    """حقول الحدث المشتقّة من التحليل + `extra_data` مدموجة، مع التحليل نفسه.

    مصدر واحد لكل الجامعين: التصنيف والموقع ودرجة الخطر النووي تُحسب هنا
    بالطريقة نفسها أيًّا كان المصدر."""
    analysis = analyze(title, description, base_category=base_category, source_kind=source_kind)
    fields = event_fields(analysis)
    fields["extra_data"] = json.dumps({**(extra or {}), **analysis.extra}, ensure_ascii=False)
    return fields, analysis


def make_source_id(prefix: str, url: str) -> str:
    """معرّف مصدر ثابت من رابط المقال — موحّد عبر كل الجامعين.

    `usedforsecurity=False` كي لا تفشل على أنظمة FIPS (md5 هنا لإزالة التكرار
    لا للأمن)، مع إبقاء نفس البصمة السابقة فلا تتكرّر الصفوف القائمة."""
    digest = hashlib.md5(url.encode(), usedforsecurity=False).hexdigest()
    return f"{prefix}_{digest}"


async def parse_feed_async(text: str):
    """تحليل خلاصة خارج خيط حلقة الأحداث (feedparser متزامن)."""
    return await asyncio.to_thread(feedparser.parse, text)


async def process_feeds(
    client: httpx.AsyncClient,
    feeds: list[dict],
    processor: Callable[[httpx.AsyncClient, dict], Awaitable[int]],
    *,
    label: str,
    concurrency: int = _FEED_CONCURRENCY,
) -> int:
    """يشغّل `processor(client, cfg)` لكل خلاصة بتزامن محدود ويعيد المجموع.

    فشل خلاصة واحدة يُسجَّل ولا يُسقط الباقي (جمع جزئي). لكن إن فشلت *كل*
    الخلاصات نرفع استثناءً — إشارة صادقة بأن الجامع معطّل (لا مجرد "لا جديد")
    يلتقطها `asyncio.gather(return_exceptions=True)` في main.
    """
    if not feeds:
        return 0

    sem = asyncio.Semaphore(concurrency)

    async def _one(cfg: dict) -> int:
        async with sem:
            return await processor(client, cfg)

    results = await asyncio.gather(*(_one(c) for c in feeds), return_exceptions=True)

    total = 0
    errors = 0
    for cfg, res in zip(feeds, results):
        if isinstance(res, Exception):
            errors += 1
            logger.error("خطأ في خلاصة %s: %s", cfg.get("name", "?"), res)
        else:
            total += res

    if errors == len(feeds):
        raise RuntimeError(f"{label}: فشلت كل الخلاصات ({errors}/{len(feeds)})")
    return total
