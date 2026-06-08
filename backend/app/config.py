"""رصد (Rasad) - إعدادات المشروع"""
import os
import sys
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


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

    # Database
    database_url: str = Field(default_factory=_default_database_url)

    # Intervals (seconds)
    gdelt_interval: int = 900
    newsapi_interval: int = 600
    rss_interval: int = 120
    ucdp_interval: int = 86400
    adsb_interval: int = 10

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    class Config:
        env_file = _env_files()
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
