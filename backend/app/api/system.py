"""رصد - نقاط النظام: الصحة، المصادر، صحة الجامعين، والتحديث اليدوي.

كانت هذه المسارات داخل `main.py` مع إعداد التطبيق ودورة الحياة وتخديم الملفات
الثابتة، فيضطر ملف الاختبارات لبناء تطبيق ثانٍ يدويًا. فصلها هنا يجعلها قابلة
للتركيب والاختبار كبقية المسارات.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta, timezone
from typing import Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, or_, select

from .. import __version__
from ..auth import require_api_key
from ..collectors import (
    collect_gdelt_events,
    collect_iran_osint,
    collect_news,
    collect_rss_feeds,
    collect_ucdp_events,
)
from ..config import get_settings
from ..models.database import Event, get_session_factory
from ..processors.dates import utcnow

logger = logging.getLogger("rasad.system")

router = APIRouter(prefix="/api", tags=["system"])

#: الجامعون الدوريّون باسمهم. مصدر واحد بدل مصفوفتين متوازيتين كان يُطابَق
#: بينهما بالعين (إعادة ترتيب واحدة تنسب النتيجة للمصدر الخطأ بلا خطأ).
#: يُقرأ وقت الاستدعاء لا وقت الاستيراد، فتستطيع الاختبارات استبداله.
COLLECTORS: dict[str, Callable[[], Awaitable[int]]] = {
    "gdelt": collect_gdelt_events,
    "newsapi": collect_news,
    "rss": collect_rss_feeds,
    "ucdp": collect_ucdp_events,
    "iran_osint": collect_iran_osint,
}

# حدّ أدنى بين تحديثين يدويّين — يمنع قصف المصادر الخارجية بطلبات متتالية.
# متغيّر عملية واحدة: كافٍ لتطبيق سطح المكتب وuvicorn بعامل واحد؛ مع عدة
# عمّال يصير لكل عامل عدّاده، فاعتمد على حدّ الوكيل العكسي حينها.
REFRESH_COOLDOWN_SECONDS = 120
_last_manual_refresh: float = 0.0


async def run_all_collectors() -> tuple[dict, int]:
    """يشغّل كل الجامعين بالتوازي ويعيد (ملخّص لكل مصدر، مجموع الجديد).

    لا نُعيد نصّ الاستثناء الخام للعميل — قد يحوي روابط httpx تتضمّن مفاتيح
    (apiKey في مسار NewsAPI مثلاً). نُسجّل التفصيل ونُعيد رسالة عامة.
    """
    names = list(COLLECTORS)
    results = await asyncio.gather(
        *(COLLECTORS[name]() for name in names), return_exceptions=True
    )

    summary: dict = {}
    total = 0
    for name, result in zip(names, results):
        if isinstance(result, Exception):
            logger.warning("فشل الجامع %s: %s", name, result)
            summary[name] = {"status": "error", "message": "تعذّر الجمع من هذا المصدر"}
        else:
            summary[name] = {"status": "ok", "new_events": result}
            total += result
    return summary, total


@router.get("/health")
async def health_check():
    """فحص صحة النظام"""
    return {
        "status": "running",
        "name": "رصد (Rasad)",
        "version": __version__,
    }


@router.post("/refresh", dependencies=[Depends(require_api_key)])
async def manual_refresh():
    """تحديث يدوي — جلب من كل المصادر (بحدّ أدنى بين الطلبات).

    محمي بحارس CSRF (`X-Rasad-Client`) وبـ `X-API-Key` عند ضبط `API_KEY`،
    لأنه يُطلق خمسة جامعين خارجيين لكل استدعاء.
    """
    global _last_manual_refresh
    now = time.time()
    elapsed = now - _last_manual_refresh
    if elapsed < REFRESH_COOLDOWN_SECONDS:
        retry_after = round(REFRESH_COOLDOWN_SECONDS - elapsed)
        raise HTTPException(
            status_code=429,
            detail=f"التحديث اليدوي محدود — أعد المحاولة بعد {retry_after} ثانية",
            headers={"Retry-After": str(retry_after)},
        )
    _last_manual_refresh = now

    summary, total = await run_all_collectors()
    elapsed_seconds = round(time.time() - now, 1)
    logger.info(f"🔄 تحديث يدوي: {total} خبر جديد في {elapsed_seconds} ثانية")

    return {
        "status": "ok",
        "total_new": total,
        "elapsed_seconds": elapsed_seconds,
        "sources": summary,
    }


def _collector_intervals(settings) -> dict[str, int]:
    return {
        "gdelt": settings.gdelt_interval,
        "newsapi": settings.newsapi_interval,
        "rss": settings.rss_interval,
        "ucdp": settings.ucdp_interval,
        "iran_osint": settings.iran_osint_interval,
    }


@router.get("/collectors/status")
async def get_collectors_status():
    """صحة جامعي البيانات — تُقاس مقابل فاصل الجمع الفعلي لكل مصدر، لا بعدد
    أحداث آخر ساعة (كان يُظهر UCDP اليومي وإيران نصف الساعي كأنهما معطّلان).

    استعلامان مُجمَّعان بدل استعلامَين لكل مصدر (كانت عشرة تسلسلية)، وكلاهما
    يستغلّ الفهرس المركّب `idx_events_source_collected`.
    """
    settings = get_settings()
    intervals = _collector_intervals(settings)
    now = utcnow()

    # نافذة العدّ لكل مصدر: ساعة للمصادر السريعة، وفاصلها الكامل للبطيئة
    windows = {
        src: timedelta(hours=1) if interval < 3600 else timedelta(seconds=interval)
        for src, interval in intervals.items()
    }

    session_factory = get_session_factory()
    async with session_factory() as session:
        last_rows = (await session.execute(
            select(Event.source, func.max(Event.collected_at))
            .where(Event.source.in_(list(intervals)))
            .group_by(Event.source)
        )).all()
        last_by_source = dict(last_rows)

        # شرط واحد لكل مصدر بنافذته، مجموعة بـ OR — استعلام واحد لكل المصادر
        count_rows = (await session.execute(
            select(Event.source, func.count(Event.id))
            .where(or_(*[
                and_(Event.source == src, Event.collected_at >= now - window)
                for src, window in windows.items()
            ]))
            .group_by(Event.source)
        )).all()
        counts_by_source = dict(count_rows)

    status = {}
    for src, interval in intervals.items():
        last_collect = last_by_source.get(src)
        if last_collect is not None and last_collect.tzinfo is None:
            last_collect = last_collect.replace(tzinfo=timezone.utc)

        status[src] = {
            "last_collect": last_collect.isoformat() if last_collect else None,
            "recent_count": counts_by_source.get(src, 0),
            "interval_seconds": interval,
            # صحّي إذا جُمع خلال ضعف فاصله المتوقّع (هامش تسامح)
            "healthy": bool(
                last_collect and (now - last_collect) < timedelta(seconds=interval * 2)
            ),
        }
    return status


@router.get("/sources")
async def get_sources():
    """المصادر المتاحة. المصدر الذي ينقصه اعتماد يُعلَن `disabled` بدل
    `active` — كان NewsAPI بلا مفتاح وUCDP بلا رمز يظهران فعّالين وهما لا
    يجمعان شيئًا."""
    s = get_settings()

    def _fmt(seconds: int) -> str:
        if seconds >= 86400:
            return "يومي"
        if seconds >= 3600:
            return f"كل {seconds // 3600} ساعة"
        if seconds >= 60:
            return f"كل {seconds // 60} دقيقة"
        return f"كل {seconds} ثانية"

    def _state(enabled: bool) -> str:
        return "active" if enabled else "disabled"

    return {
        "active": [
            {"id": "gdelt", "name": "GDELT Project", "interval": _fmt(s.gdelt_interval), "status": "active"},
            {"id": "newsapi", "name": "NewsAPI", "interval": _fmt(s.newsapi_interval), "status": _state(bool(s.newsapi_key))},
            {"id": "rss", "name": "RSS Feeds", "interval": _fmt(s.rss_interval), "status": "active"},
            {"id": "ucdp", "name": "UCDP Uppsala", "interval": _fmt(s.ucdp_interval), "status": _state(bool(s.ucdp_access_token))},
            {"id": "iran_osint", "name": "Iran OSINT", "interval": _fmt(s.iran_osint_interval), "status": "active"},
            {"id": "adsb", "name": "adsb.lol ADS-B", "interval": _fmt(s.effective_adsb_interval), "status": "active"},
        ],
        "planned": [
            {"id": "telegram", "name": "Telegram", "status": "phase_2"},
            {"id": "ai", "name": "Ollama/Qwen AI", "status": "phase_2"},
        ],
    }
