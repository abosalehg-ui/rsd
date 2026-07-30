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
import logging
import re
from typing import Awaitable, Callable, Optional

import feedparser
import httpx

logger = logging.getLogger("rasad.feeds")

_TAG_RE = re.compile(r"<[^>]+>")

# عدد الخلاصات المجلوبة بالتوازي — يوازن بين السرعة وعدم إغراق الشبكة/المزوّدين
_FEED_CONCURRENCY = 6


def clean_html(raw: str, cap: int) -> str:
    """يزيل وسوم HTML البسيطة ويقتطع الوصف إلى `cap` حرفاً."""
    return _TAG_RE.sub("", raw or "")[:cap]


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


def _mapper_result(fields: Optional[dict]) -> Optional[dict]:
    """تحقّق دفاعي: mapper يعيد dict أو None."""
    return fields if isinstance(fields, dict) else None
