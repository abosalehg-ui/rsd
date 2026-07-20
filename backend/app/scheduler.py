"""رصد - جدولة جمع البيانات"""
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .collectors import (
    collect_flights,
    collect_gdelt_events,
    collect_iran_osint,
    collect_news,
    collect_rss_feeds,
    collect_ucdp_events,
)
from .config import get_settings
from .models.database import prune_old_data

logger = logging.getLogger("rasad.scheduler")

scheduler = AsyncIOScheduler()


def start_scheduler():
    """بدء جدولة جمع البيانات"""
    settings = get_settings()

    # GDELT - كل 15 دقيقة
    scheduler.add_job(
        collect_gdelt_events,
        "interval",
        seconds=settings.gdelt_interval,
        id="gdelt_collector",
        name="جامع GDELT",
        max_instances=1,
    )

    # NewsAPI - كل 10 دقائق
    scheduler.add_job(
        collect_news,
        "interval",
        seconds=settings.newsapi_interval,
        id="newsapi_collector",
        name="جامع الأخبار",
        max_instances=1,
    )

    # RSS - كل 5 دقائق
    scheduler.add_job(
        collect_rss_feeds,
        "interval",
        seconds=settings.rss_interval,
        id="rss_collector",
        name="جامع RSS",
        max_instances=1,
    )

    # UCDP - كل يوم
    scheduler.add_job(
        collect_ucdp_events,
        "interval",
        seconds=settings.ucdp_interval,
        id="ucdp_collector",
        name="جامع UCDP",
        max_instances=1,
    )

    # الطيران - كل 30 ثانية (مخفف عن 10 ثوان لحماية الحصة)
    # ملاحظة: بقيّة المجمّعات تُجمَع مرة عند الإقلاع في lifespan، لذا لا نمرّر لها
    # next_run_time تجنّبًا لتشغيل متزامن مزدوج يُسبّب تعارض المفتاح الفريد.
    # الطيران وحده غير مشمول في جمع الإقلاع (ولا يعتمد source_id فريد)، فنُبقيه فوريًا.
    scheduler.add_job(
        collect_flights,
        "interval",
        seconds=max(settings.adsb_interval, 30),
        id="adsb_collector",
        name="متتبع الطيران",
        max_instances=1,
        next_run_time=datetime.now(),
    )

    # Iran OSINT - كل 30 دقيقة (مثل iranstrikemap)
    scheduler.add_job(
        collect_iran_osint,
        "interval",
        seconds=1800,
        id="iran_osint_collector",
        name="جامع إيران OSINT",
        max_instances=1,
    )

    # تنظيف البيانات القديمة — يومياً (يمنع نمو قاعدة البيانات بلا حدود)
    async def _prune():
        s = get_settings()
        await prune_old_data(
            events_days=s.retention_events_days,
            flights_days=s.retention_flights_days,
        )

    scheduler.add_job(
        _prune,
        "interval",
        hours=24,
        id="data_pruner",
        name="منظّف البيانات",
        max_instances=1,
    )

    scheduler.start()
    logger.info("✅ تم بدء جدولة جمع البيانات")


def stop_scheduler():
    """إيقاف الجدولة"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("⏹️ تم إيقاف الجدولة")
