"""رصد - جدولة جمع البيانات"""
import logging
from datetime import datetime, timezone

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

    # الفواصل كلها من الإعدادات (قابلة للضبط عبر .env) — لا نُعلّق قيماً حرفية
    # هنا كي لا تنحرف التعليقات عن القيم الفعلية.
    scheduler.add_job(
        collect_gdelt_events,
        "interval",
        seconds=settings.gdelt_interval,
        id="gdelt_collector",
        name="جامع GDELT",
        max_instances=1,
    )

    scheduler.add_job(
        collect_news,
        "interval",
        seconds=settings.newsapi_interval,
        id="newsapi_collector",
        name="جامع الأخبار",
        max_instances=1,
    )

    scheduler.add_job(
        collect_rss_feeds,
        "interval",
        seconds=settings.rss_interval,
        id="rss_collector",
        name="جامع RSS",
        max_instances=1,
    )

    scheduler.add_job(
        collect_ucdp_events,
        "interval",
        seconds=settings.ucdp_interval,
        id="ucdp_collector",
        name="جامع UCDP",
        max_instances=1,
    )

    # الطيران — بحدّ أدنى 30 ثانية (حماية حصة adsb.lol).
    # ملاحظة: بقيّة المجمّعات تُجمَع مرة عند الإقلاع في lifespan، لذا لا نمرّر لها
    # next_run_time تجنّبًا لتشغيل متزامن مزدوج يُسبّب تعارض المفتاح الفريد.
    # الطيران وحده غير مشمول في جمع الإقلاع (ولا يعتمد source_id فريد)، فنُبقيه فوريًا.
    scheduler.add_job(
        collect_flights,
        "interval",
        seconds=settings.effective_adsb_interval,
        id="adsb_collector",
        name="متتبع الطيران",
        max_instances=1,
        next_run_time=datetime.now(timezone.utc),
    )

    scheduler.add_job(
        collect_iran_osint,
        "interval",
        seconds=settings.iran_osint_interval,
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
