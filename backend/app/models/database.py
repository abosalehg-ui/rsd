"""رصد (Rasad) - نماذج قاعدة البيانات"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, Index
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timezone


class Base(DeclarativeBase):
    pass


class Event(Base):
    """جدول الأحداث - يخزن جميع الأحداث من كل المصادر"""
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False)           # gdelt, newsapi, rss, ucdp, adsb
    source_id = Column(String(255), unique=True)           # معرف فريد من المصدر
    title = Column(Text, nullable=False)                   # عنوان الحدث
    description = Column(Text)                             # وصف تفصيلي
    url = Column(Text)                                     # رابط المصدر
    image_url = Column(Text)                               # صورة الحدث

    # التصنيف
    category = Column(String(50), default="general")       # military, diplomatic, humanitarian, nuclear, economic
    severity = Column(String(20), default="medium")        # critical, high, medium, low
    event_type = Column(String(100))                       # نوع فرعي

    # الموقع الجغرافي
    latitude = Column(Float)
    longitude = Column(Float)
    country = Column(String(100))
    country_code = Column(String(10))
    location_name = Column(String(255))

    # التوقيت
    event_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    collected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # بيانات إضافية (JSON string)
    extra_data = Column(Text)

    __table_args__ = (
        Index("idx_events_date", "event_date"),
        Index("idx_events_category", "category"),
        Index("idx_events_country", "country_code"),
        Index("idx_events_source", "source"),
        Index("idx_events_severity", "severity"),
    )


class FlightTrack(Base):
    """جدول تتبع الطيران"""
    __tablename__ = "flight_tracks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    icao24 = Column(String(10), nullable=False)            # ICAO24 transponder address
    callsign = Column(String(20))                          # إشارة النداء
    origin_country = Column(String(100))                   # بلد المنشأ

    latitude = Column(Float)
    longitude = Column(Float)
    altitude = Column(Float)                               # بالمتر
    velocity = Column(Float)                               # بالمتر/ثانية
    heading = Column(Float)                                # الاتجاه بالدرجات
    vertical_rate = Column(Float)                          # معدل الصعود/الهبوط
    on_ground = Column(Boolean, default=False)

    is_military = Column(Boolean, default=False)           # هل عسكرية
    aircraft_type = Column(String(50))                     # نوع الطائرة
    squawk = Column(String(10))                            # رمز السكواك

    tracked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_flight_icao", "icao24"),
        Index("idx_flight_military", "is_military"),
        Index("idx_flight_time", "tracked_at"),
    )


# إعداد محرك قاعدة البيانات
_engine = None
_session_factory = None


async def init_db(database_url: str = "sqlite+aiosqlite:///./data/rasad.db"):
    """تهيئة قاعدة البيانات وإنشاء الجداول"""
    global _engine, _session_factory

    _engine = create_async_engine(database_url, echo=False)
    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return _engine


def get_session_factory():
    return _session_factory
