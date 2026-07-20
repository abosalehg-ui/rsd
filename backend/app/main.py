"""
╔══════════════════════════════════════════════════════════════╗
║                    رصد (Rsd)                             ║
║         منصة استخبارات المصادر المفتوحة - OSINT            ║
║              الشرق الأوسط - لوحة تحكم شخصية                ║
╚══════════════════════════════════════════════════════════════╝
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .api.events import router as events_router
from .api.flights import router as flights_router
from .api.infrastructure import router as infrastructure_router
from .api.iran import router as iran_router
from .api.nuclear import router as nuclear_router
from .collectors import (
    collect_gdelt_events,
    collect_iran_osint,
    collect_news,
    collect_rss_feeds,
    collect_ucdp_events,
)
from .config import get_settings
from .middleware.cache import ETagCacheMiddleware
from .models.database import init_db
from .scheduler import start_scheduler, stop_scheduler

# إعداد السجل
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("rasad")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """إدارة دورة حياة التطبيق"""
    logger.info("🚀 بدء تشغيل رصد (Rasad)...")

    # تهيئة قاعدة البيانات
    settings = get_settings()
    await init_db(settings.database_url)
    logger.info("✅ قاعدة البيانات جاهزة")

    # جمع أولي للبيانات
    logger.info("📡 جمع البيانات الأولي...")
    try:
        results = await asyncio.gather(
            collect_gdelt_events(),
            collect_news(),
            collect_rss_feeds(),
            collect_ucdp_events(),
            collect_iran_osint(),
            return_exceptions=True,
        )
        for i, name in enumerate(["GDELT", "NewsAPI", "RSS", "UCDP", "Iran OSINT"]):
            if isinstance(results[i], Exception):
                logger.warning(f"⚠️ {name}: {results[i]}")
            else:
                logger.info(f"✅ {name}: {results[i]} حدث")
    except Exception as e:
        logger.error(f"خطأ في الجمع الأولي: {e}")

    # بدء الجدولة
    start_scheduler()
    logger.info("✅ رصد يعمل الآن!")

    yield

    # إيقاف
    stop_scheduler()
    logger.info("⏹️ تم إيقاف رصد")


# إنشاء التطبيق
app = FastAPI(
    title="رصد (Rasad)",
    description="منصة استخبارات المصادر المفتوحة للشرق الأوسط",
    version=__version__,
    lifespan=lifespan,
)

# CORS — أصول محدّدة من الإعدادات بدل "*" (لا credentials؛ لا جلسات مستخدم).
_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["ETag", "Cache-Control"],
)

# ETag + Cache-Control (v1.4) — يُسجَّل بعد CORS ليكون أعمق في السلسلة
app.add_middleware(ETagCacheMiddleware)

# تسجيل نقاط API
app.include_router(events_router)
app.include_router(flights_router)
app.include_router(iran_router)
app.include_router(nuclear_router)
app.include_router(infrastructure_router)


@app.get("/api/health")
async def health_check():
    """فحص صحة النظام"""
    return {
        "status": "running",
        "name": "رصد (Rasad)",
        "version": __version__,
    }


# تحديد معدل التحديث اليدوي — يمنع قصف المصادر الخارجية بطلبات متتالية
_REFRESH_COOLDOWN_SECONDS = 120
_last_manual_refresh: float = 0.0


@app.post("/api/refresh")
async def manual_refresh():
    """تحديث يدوي - جلب أخبار جديدة من جميع المصادر (بحدّ أدنى بين الطلبات)"""
    global _last_manual_refresh
    now = time.time()
    elapsed_since_last = now - _last_manual_refresh
    if elapsed_since_last < _REFRESH_COOLDOWN_SECONDS:
        retry_after = round(_REFRESH_COOLDOWN_SECONDS - elapsed_since_last)
        raise HTTPException(
            status_code=429,
            detail=f"التحديث اليدوي محدود — أعد المحاولة بعد {retry_after} ثانية",
            headers={"Retry-After": str(retry_after)},
        )
    _last_manual_refresh = now
    start = now

    results = await asyncio.gather(
        collect_gdelt_events(),
        collect_news(),
        collect_rss_feeds(),
        collect_ucdp_events(),
        collect_iran_osint(),
        return_exceptions=True,
    )

    sources = ["gdelt", "newsapi", "rss", "ucdp", "iran_osint"]
    summary = {}
    total = 0

    for i, name in enumerate(sources):
        if isinstance(results[i], Exception):
            summary[name] = {"status": "error", "message": str(results[i])}
        else:
            summary[name] = {"status": "ok", "new_events": results[i]}
            total += results[i]

    elapsed = round(time.time() - start, 1)
    logger.info(f"🔄 تحديث يدوي: {total} خبر جديد في {elapsed} ثانية")

    return {
        "status": "ok",
        "total_new": total,
        "elapsed_seconds": elapsed,
        "sources": summary,
    }

@app.get("/api/collectors/status")
async def get_collectors_status():
    """حالة جامعي البيانات — الصحة تُقاس مقابل فاصل الجمع الفعلي لكل مصدر،
    لا بعدد أحداث آخر ساعة (كان يُظهر UCDP اليومي وإيران نصف الساعي كأنهما معطّلان)."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import func, select

    from .models.database import Event, get_session_factory

    settings = get_settings()
    # فاصل الجمع المتوقّع لكل مصدر (ثواني)
    intervals = {
        "gdelt": settings.gdelt_interval,
        "newsapi": settings.newsapi_interval,
        "rss": settings.rss_interval,
        "ucdp": settings.ucdp_interval,
        "iran_osint": 1800,
    }

    session_factory = get_session_factory()
    now = datetime.now(timezone.utc)
    async with session_factory() as session:
        status = {}
        for src, interval in intervals.items():
            last_collect = (await session.execute(
                select(func.max(Event.collected_at)).where(Event.source == src)
            )).scalar()

            window = timedelta(hours=1) if interval < 3600 else timedelta(seconds=interval)
            recent_count = (await session.execute(
                select(func.count(Event.id)).where(
                    Event.source == src, Event.collected_at >= now - window
                )
            )).scalar()

            # صحّي إذا جُمع خلال ضعف فاصله المتوقّع (هامش تسامح)
            if last_collect is not None and last_collect.tzinfo is None:
                last_collect_aware = last_collect.replace(tzinfo=timezone.utc)
            else:
                last_collect_aware = last_collect
            healthy = bool(
                last_collect_aware
                and (now - last_collect_aware) < timedelta(seconds=interval * 2)
            )

            status[src] = {
                "last_collect": last_collect.isoformat() if last_collect else None,
                "recent_count": recent_count,
                "interval_seconds": interval,
                "healthy": healthy,
            }

        return status

@app.get("/api/sources")
async def get_sources():
    """المصادر المتاحة — الفواصل مشتقّة من الإعدادات الفعلية."""
    s = get_settings()

    def _fmt(seconds: int) -> str:
        if seconds >= 86400:
            return "يومي"
        if seconds >= 3600:
            return f"كل {seconds // 3600} ساعة"
        if seconds >= 60:
            return f"كل {seconds // 60} دقيقة"
        return f"كل {seconds} ثانية"

    return {
        "active": [
            {"id": "gdelt", "name": "GDELT Project", "interval": _fmt(s.gdelt_interval), "status": "active"},
            {"id": "newsapi", "name": "NewsAPI", "interval": _fmt(s.newsapi_interval), "status": "active"},
            {"id": "rss", "name": "RSS Feeds", "interval": _fmt(s.rss_interval), "status": "active"},
            {"id": "ucdp", "name": "UCDP Uppsala", "interval": _fmt(s.ucdp_interval), "status": "active"},
            {"id": "iran_osint", "name": "Iran OSINT", "interval": "كل 30 دقيقة", "status": "active"},
            {"id": "adsb", "name": "adsb.lol ADS-B", "interval": _fmt(max(s.adsb_interval, 30)), "status": "active"},
        ],
        "planned": [
            {"id": "telegram", "name": "Telegram", "status": "phase_2"},
            {"id": "ai", "name": "Ollama/Qwen AI", "status": "phase_2"},
        ],
    }


# ──────────────────────────────────────────────────────────────────────────
# تخديم الواجهة المبنية (الوضع المُجمّع / سطح المكتب)
#
# عند توفّر مجلّد frontend/dist (يُحزَم داخل تطبيق PyInstaller) نُقدّمه على "/".
# يُسجَّل آخر شيء، فتبقى مسارات /api و /docs أعلى أولوية. لا يؤثّر على وضع
# التطوير أو Docker أو الاختبارات (حيث لا يوجد dist).
# ──────────────────────────────────────────────────────────────────────────
def _frontend_dist():
    import sys
    from pathlib import Path

    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(getattr(sys, "_MEIPASS", ".")) / "frontend_dist")
    # مستودع التطوير: backend/app/main.py → ../../frontend/dist
    candidates.append(Path(__file__).resolve().parent.parent.parent / "frontend" / "dist")
    for c in candidates:
        if (c / "index.html").exists():
            return c
    return None


_dist = _frontend_dist()
if _dist is not None:
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="frontend")
    logger.info(f"🖥️  تخديم الواجهة من: {_dist}")
