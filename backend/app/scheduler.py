"""رصد - جدولة جمع البيانات"""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .collectors import (
    collect_flights,
    collect_gdelt_events,
    collect_iran_osint,
    collect_markets,
    collect_news,
    collect_nuclear_watch,
    collect_rss_feeds,
    collect_ucdp_events,
)
from .config import get_settings
from .models.database import prune_old_data, run_story_clustering

logger = logging.getLogger("rasad.scheduler")

# misfire_grace_time: الافتراضي ثانية واحدة، فحين تنشغل الحلقة (الجمع الأولي
# لسبعة مصادر عند الإقلاع، أو إعادة تحليل قاعدة سطح مكتب) تفوّت وظيفة RSS
# موعدها بأكثر من ثانية فتُسقَط. دقيقة كاملة مع دمج التشغيلات الفائتة في واحد.
JOB_DEFAULTS = {"misfire_grace_time": 60, "coalesce": True}

scheduler = AsyncIOScheduler(job_defaults=JOB_DEFAULTS)


def start_scheduler():
    """بدء جدولة جمع البيانات"""
    register_jobs(scheduler, get_settings())
    scheduler.start()
    logger.info("✅ تم بدء جدولة جمع البيانات")


def register_jobs(scheduler: AsyncIOScheduler, settings) -> None:
    """يسجّل كل الوظائف الدورية على `scheduler` دون تشغيله (قابل للاختبار)."""

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

    scheduler.add_job(
        collect_nuclear_watch,
        "interval",
        seconds=settings.nuclear_interval,
        id="nuclear_watch_collector",
        name="جامع الرصد النووي والإشعاعي",
        max_instances=1,
    )

    # أسعار الطاقة والأسواق (FRED) — يومية. ليست أحداثًا فلا تدخل جمع الإقلاع
    # في lifespan؛ تشغيل فوري هنا كي لا يبقى الشريط فارغًا يومًا كاملًا بعد
    # إضافة المفتاح. بلا مفتاح تعود الوظيفة فورًا بلا طلب.
    scheduler.add_job(
        collect_markets,
        "interval",
        seconds=settings.markets_interval,
        id="markets_collector",
        name="جامع الطاقة والأسواق (FRED)",
        max_instances=1,
        next_run_time=datetime.now(timezone.utc),
    )

    # تجميع القصص: كل جامع يكتب مستقلًا، فالتجميع وظيفة دورية واحدة بعدهم
    scheduler.add_job(
        run_story_clustering,
        "interval",
        seconds=settings.clustering_interval,
        id="story_clustering",
        name="تجميع القصص",
        max_instances=1,
    )

    # تنظيف البيانات القديمة — يومياً (يمنع نمو قاعدة البيانات بلا حدود)
    async def _prune():
        s = get_settings()
        await prune_old_data(
            events_days=s.retention_events_days,
            flights_days=s.retention_flights_days,
            markets_days=s.retention_markets_days,
        )

    scheduler.add_job(
        _prune,
        "interval",
        hours=24,
        id="data_pruner",
        name="منظّف البيانات",
        max_instances=1,
    )


def stop_scheduler():
    """إيقاف الجدولة"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("⏹️ تم إيقاف الجدولة")
