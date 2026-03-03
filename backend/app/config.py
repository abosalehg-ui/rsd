"""رصد (Rasad) - إعدادات المشروع"""
from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # NewsAPI
    newsapi_key: str = ""

    # OpenSky
    opensky_client_id: str = ""
    opensky_client_secret: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///./rasad.db"

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
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
