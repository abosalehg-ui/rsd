"""
╔══════════════════════════════════════════════════════════════╗
║                    رصد (Rsd) v1.0                        ║
║         منصة استخبارات المصادر المفتوحة - OSINT            ║
║              الشرق الأوسط - لوحة تحكم شخصية                ║
╚══════════════════════════════════════════════════════════════╝
"""
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .config import get_settings
from .models.database import init_db
from .api.events import router as events_router
from .api.flights import router as flights_router
from .scheduler import start_scheduler, stop_scheduler
from .collectors import (
    collect_gdelt_events,
    collect_news,
    collect_rss_feeds,
    collect_ucdp_events,
)

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
            return_exceptions=True,
        )
        for i, name in enumerate(["GDELT", "NewsAPI", "RSS", "UCDP"]):
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
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# تسجيل نقاط API
app.include_router(events_router)
app.include_router(flights_router)


@app.get("/api/health")
async def health_check():
    """فحص صحة النظام"""
    return {
        "status": "running",
        "name": "رصد (Rasad)",
        "version": "1.0.0",
    }


@app.post("/api/refresh")
async def manual_refresh():
    """تحديث يدوي - جلب أخبار جديدة من جميع المصادر"""
    import time
    start = time.time()
    
    results = await asyncio.gather(
        collect_gdelt_events(),
        collect_news(),
        collect_rss_feeds(),
        collect_ucdp_events(),
        return_exceptions=True,
    )
    
    sources = ["gdelt", "newsapi", "rss", "ucdp"]
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
    """حالة جامعي البيانات"""
    from .models.database import Event, get_session_factory
    from sqlalchemy import select, func
    from datetime import datetime, timedelta, timezone
    
    session_factory = get_session_factory()
    async with session_factory() as session:
        sources = ["gdelt", "newsapi", "rss", "ucdp"]
        status = {}
        
        for src in sources:
            # آخر خبر من هذا المصدر
            query = select(func.max(Event.collected_at)).where(Event.source == src)
            last_collect = (await session.execute(query)).scalar()
            
            # عدد الأخبار في آخر ساعة
            hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            count_query = select(func.count(Event.id)).where(
                Event.source == src,
                Event.collected_at >= hour_ago
            )
            recent_count = (await session.execute(count_query)).scalar()
            
            status[src] = {
                "last_collect": last_collect.isoformat() if last_collect else None,
                "recent_count": recent_count,
                "healthy": recent_count > 0
            }
        
        return status

@app.get("/api/sources")
async def get_sources():
    """المصادر المتاحة"""
    return {
        "active": [
            {"id": "gdelt", "name": "GDELT Project", "interval": "15 دقيقة", "status": "active"},
            {"id": "newsapi", "name": "NewsAPI", "interval": "10 دقائق", "status": "active"},
            {"id": "rss", "name": "RSS Feeds", "interval": "5 دقائق", "status": "active"},
            {"id": "ucdp", "name": "UCDP Uppsala", "interval": "يومي", "status": "active"},
            {"id": "adsb", "name": "OpenSky ADS-B", "interval": "30 ثانية", "status": "active"},
        ],
        "planned": [
            {"id": "telegram", "name": "Telegram", "status": "phase_2"},
            {"id": "ai", "name": "Ollama/Qwen AI", "status": "phase_2"},
        ],
    }
