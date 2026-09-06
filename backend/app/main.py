"""
╔══════════════════════════════════════════════════════════════╗
║                    رصد (Rsd)                             ║
║         منصة استخبارات المصادر المفتوحة - OSINT            ║
║              الشرق الأوسط - لوحة تحكم شخصية                ║
╚══════════════════════════════════════════════════════════════╝

مصنع التطبيق فقط: دورة الحياة، توصيل الطبقات، تسجيل المسارات، وتخديم الواجهة
المبنية. المسارات نفسها تعيش في `api/`.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .api.events import router as events_router
from .api.flights import router as flights_router
from .api.infrastructure import router as infrastructure_router
from .api.iran import router as iran_router
from .api.nuclear import router as nuclear_router
from .api.system import router as system_router
from .api.system import run_all_collectors
from .config import Settings, get_settings
from .middleware.cache import ETagCacheMiddleware
from .middleware.ratelimit import RateLimitMiddleware
from .middleware.security_headers import SecurityHeadersMiddleware
from .models.database import init_db
from .scheduler import start_scheduler, stop_scheduler

# إعداد السجل
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("rasad")

_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost", ""}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """إدارة دورة حياة التطبيق"""
    logger.info("🚀 بدء تشغيل رصد (Rasad)...")

    settings = get_settings()
    await init_db(settings.database_url)
    logger.info("✅ قاعدة البيانات جاهزة")

    # تحذير من سوء إعداد صامت: خادم مكشوف على الشبكة بلا مفتاح API يعني
    # واجهة مفتوحة بالكامل. نُبرز هذا بدل تركه fail-open صامتاً.
    if settings.backend_host not in _LOOPBACK_HOSTS and not settings.api_key:
        logger.warning(
            "⚠️ الخادم يستمع على %s بلا API_KEY — الواجهة مكشوفة بلا مصادقة. "
            "اضبط API_KEY وضعه خلف وكيل عكسي + TLS قبل النشر.",
            settings.backend_host,
        )

    logger.info("📡 جمع البيانات الأولي...")
    try:
        summary, total = await run_all_collectors()
        for name, result in summary.items():
            if result["status"] == "ok":
                logger.info(f"✅ {name}: {result['new_events']} حدث")
            else:
                logger.warning(f"⚠️ {name}: {result['message']}")
        logger.info(f"📊 الجمع الأولي: {total} حدث جديد")
    except Exception as e:
        logger.error(f"خطأ في الجمع الأولي: {e}")

    start_scheduler()
    logger.info("✅ رصد يعمل الآن!")

    yield

    stop_scheduler()
    logger.info("⏹️ تم إيقاف رصد")


def _frontend_dist() -> Path | None:
    """مجلّد الواجهة المبنية إن وُجد (وضع سطح المكتب أو بعد `npm run build`)."""
    import sys

    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(getattr(sys, "_MEIPASS", ".")) / "frontend_dist")
    # مستودع التطوير: backend/app/main.py → ../../frontend/dist
    candidates.append(Path(__file__).resolve().parent.parent.parent / "frontend" / "dist")
    for candidate in candidates:
        if (candidate / "index.html").exists():
            return candidate
    return None


def create_app(settings: Settings | None = None, *, with_lifespan: bool = True) -> FastAPI:
    """يبني تطبيق FastAPI كاملاً.

    `with_lifespan=False` يُنشئ التطبيق نفسه بلا مجدول ولا جمع خارجي —
    تستعمله الاختبارات بدل إعادة تركيب تطبيق ناقص يدويًا.
    """
    settings = settings or get_settings()

    app = FastAPI(
        title="رصد (Rasad)",
        description="منصة استخبارات المصادر المفتوحة للشرق الأوسط",
        version=__version__,
        lifespan=lifespan if with_lifespan else None,
    )

    # ترتيب الطبقات — في Starlette آخر `add_middleware` يُسجَّل هو الأبعد للخارج
    # (يلفّ الباقي)، لذا نُسجّل من الداخل للخارج:
    #   1) ETag  (الأعمق، الأقرب للتطبيق)
    #   2) RateLimit  (يرفض مبكراً قبل هدر عمل على طلب مرفوض)
    #   3) CORS  (يلفّ استجابات RateLimit فتحمل 429 ترويسات CORS ويستطيع
    #             المتصفح قراءة Retry-After؛ ويلتقط preflight بلا استهلاك الحصة)
    #   4) SecurityHeaders  (الأبعد؛ يُلبس صفحات الواجهة ترويسات الأمان)
    app.add_middleware(ETagCacheMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
        trust_proxy_headers=settings.trust_proxy_headers,
    )
    # أصول محدّدة من الإعدادات بدل "*" (لا credentials؛ لا جلسات مستخدم).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["ETag", "Cache-Control"],
    )
    app.add_middleware(SecurityHeadersMiddleware)

    app.include_router(system_router)
    app.include_router(events_router)
    app.include_router(flights_router)
    app.include_router(iran_router)
    app.include_router(nuclear_router)
    app.include_router(infrastructure_router)

    # تخديم الواجهة المبنية (الوضع المُجمّع / سطح المكتب). يُركَّب أخيراً على "/"
    # فتبقى مسارات /api و/docs أعلى أولوية.
    dist = _frontend_dist()
    if dist is not None:
        from fastapi.staticfiles import StaticFiles

        app.mount("/", StaticFiles(directory=str(dist), html=True), name="frontend")
        logger.info(f"🖥️  تخديم الواجهة من: {dist}")

    return app


app = create_app()
