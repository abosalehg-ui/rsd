"""رصد (Rasad) - إعدادات المشروع"""
import os
import sys
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_app_data_dir() -> Path:
    """مجلّد بيانات قابل للكتابة (قاعدة البيانات + إعدادات المستخدم).

    عند التشغيل كتطبيق مُجمّع (PyInstaller) لا يمكن الكتابة داخل Program Files،
    لذا نستخدم %LOCALAPPDATA%\\Rasad على ويندوز (أو ~/.rasad غير ذلك).
    في وضع التطوير نُبقي المجلّد الحالي للحفاظ على السلوك السابق.
    """
    if getattr(sys, "frozen", False):
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        d = Path(base) / "Rasad" if base else Path.home() / ".rasad"
    else:
        d = Path.cwd()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _default_database_url() -> str:
    """قاعدة البيانات الافتراضية — في مجلّد قابل للكتابة عند التجميد."""
    if getattr(sys, "frozen", False):
        db_path = (get_app_data_dir() / "rasad.db").as_posix()
        return f"sqlite+aiosqlite:///{db_path}"
    return "sqlite+aiosqlite:///./rasad.db"


def _env_files():
    """ملفات .env المعتمدة. عند التجميد نقرأ أيضاً .env من مجلّد بيانات المستخدم
    (قابل للكتابة) ليتمكّن المستخدم من إضافة مفاتيح مثل NEWSAPI_KEY."""
    if getattr(sys, "frozen", False):
        return (".env", str(get_app_data_dir() / ".env"))
    return ".env"


class Settings(BaseSettings):
    # NewsAPI
    newsapi_key: str = ""

    # OpenSky
    opensky_client_id: str = ""
    opensky_client_secret: str = ""

    # خلاصات Google Alerts — روابط خاصة بحساب المستخدم (تُعامَل كأسرار).
    # الصيغة: عناصر مفصولة بفواصل، كل عنصر "الاسم|التصنيف|الرابط".
    # مثال: "GA - Red Sea|military|https://www.google.com/alerts/feeds/…"
    google_alert_feeds: str = ""

    # Database
    database_url: str = Field(default_factory=_default_database_url)

    # Intervals (seconds)
    gdelt_interval: int = 900
    newsapi_interval: int = 600
    rss_interval: int = 120
    ucdp_interval: int = 86400
    adsb_interval: int = 10
    iran_osint_interval: int = 1800  # مصدر واحد للفاصل بدل تكراره في scheduler/main

    @property
    def effective_adsb_interval(self) -> int:
        """فاصل ADS-B مع حدّ أدنى 30 ثانية (حماية حصة adsb.lol)."""
        return max(self.adsb_interval, 30)

    # Server — الافتراضي محلي فقط. لا تفتحه على 0.0.0.0 إلا خلف وكيل عكسي
    # ومصادقة، فالـ API بلا حسابات مستخدمين.
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000

    # ثقة ترويسات الوكيل (X-Forwarded-For). افتراضياً False: لا نثق بها فلا
    # يستطيع عميل مباشر انتحال IP لتجاوز حدّ المعدل. فعّلها (True) فقط حين يكون
    # الخادم حصراً خلف وكيل عكسي موثوق يضبط الترويسة بنفسه.
    trust_proxy_headers: bool = False

    # أمن الشبكة — أصول CORS المسموح بها (سلسلة مفصولة بفواصل)
    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:8000,http://127.0.0.1:8000"
    )

    # مفتاح حماية العمليات المكلفة (/api/refresh). فارغ = معطّل (وضع محلي).
    # عند ضبطه يجب إرسال الترويسة: X-API-Key: <القيمة>
    api_key: str = ""

    # حدّ المعدل لكل عنوان IP على مسارات /api (نافذة منزلقة)
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60

    # سياسة الاحتفاظ بالبيانات (أيام)
    retention_events_days: int = 30
    retention_flights_days: int = 7

    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """قائمة الأصول المسموح بها بعد التقسيم والتنظيف."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def google_alert_feeds_list(self) -> list[dict]:
        """تحليل GOOGLE_ALERT_FEEDS إلى قائمة إعدادات خلاصات.

        كل عنصر "الاسم|التصنيف|الرابط". العناصر المشوّهة تُتجاهل بصمت هنا
        ويُبلَّغ عنها في الجامع (حيث يتوفّر السجل).
        """
        feeds: list[dict] = []
        for raw in self.google_alert_feeds.split(","):
            entry = raw.strip()
            if not entry:
                continue
            parts = [p.strip() for p in entry.split("|")]
            if len(parts) == 3:
                name, category, url = parts
            elif len(parts) == 1:
                name, category, url = "Google Alert", "general", parts[0]
            else:
                continue
            if not url.startswith("https://"):
                continue
            feeds.append({"name": name, "category": category, "url": url, "icon": "🔔"})
        return feeds


@lru_cache()
def get_settings() -> Settings:
    return Settings()
