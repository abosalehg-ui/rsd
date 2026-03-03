"""رصد - جدولة جمع البيانات"""
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .config import get_settings
from .collectors import (
    collect_gdelt_events,
    collect_news,
    collect_rss_feeds,
    collect_ucdp_events,
    collect_flights,
)

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
        next_run_time=datetime.now(),
    )

    # NewsAPI - كل 10 دقائق
    scheduler.add_job(
        collect_news,
        "interval",
        seconds=settings.newsapi_interval,
        id="newsapi_collector",
        name="جامع الأخبار",
              max_instances=1,
        next_run_time=datetime.now(),
    )

    # RSS - كل 5 دقائق
    scheduler.add_job(
        collect_rss_feeds,
        "interval",
        seconds=settings.rss_interval,
        id="rss_collector",
        name="جامع RSS",
        max_instances=1,
        next_run_time=datetime.now(),
    )

    # UCDP - كل يوم
    scheduler.add_job(
        collect_ucdp_events,
        "interval",
        seconds=settings.ucdp_interval,
        id="ucdp_collector",
        name="جامع UCDP",
        max_instances=1,
        next_run_time=datetime.now(),
    )

    # الطيران - كل 30 ثانية (مخفف عن 10 ثوان لحماية الحصة)
    scheduler.add_job(
        collect_flights,
        "interval",
        seconds=max(settings.adsb_interval, 30),
        id="adsb_collector",
        name="متتبع الطيران",
              max_instances=1,
        next_run_time=datetime.now(),
    )

    scheduler.start()
    logger.info("✅ تم بدء جدولة جمع البيانات")


def stop_scheduler():
    """إيقاف الجدولة"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("⏹️ تم إيقاف الجدولة")
