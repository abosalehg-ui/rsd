"""رصد (Rasad) - نماذج قاعدة البيانات"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    delete,
    event,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger("rasad.database")


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

    # Iran OSINT additions
    confidence = Column(String(10), default="LOW")   # HIGH, MEDIUM, LOW
    video_url = Column(Text)                          # رابط فيديو OSINT

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


class IranianLeaderNews(Base):
    """أخبار القادة الإيرانيين"""
    __tablename__ = "iranian_leader_news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    leader_id = Column(Integer, nullable=False)
    leader_name = Column(String(100))
    title = Column(Text)
    url = Column(Text)
    news_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    collected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_leader_news_id", "leader_id"),
        Index("idx_leader_news_date", "news_date"),
    )

# إعداد محرك قاعدة البيانات
_engine = None
_session_factory = None


def _register_sqlite_pragmas(engine) -> None:
    """تفعيل WAL + مهلة قفل على اتصالات SQLite لتفادي 'database is locked'
    مع الكتّاب المتزامنين (6 وظائف مجدولة + طلبات API)."""
    if not engine.url.get_backend_name().startswith("sqlite"):
        return

    @event.listens_for(engine.sync_engine, "connect")
    def _set_pragma(dbapi_conn, _record):  # pragma: no cover - callback بسيط
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.close()


async def init_db(database_url: str = "sqlite+aiosqlite:///./data/rasad.db"):
    """تهيئة قاعدة البيانات وإنشاء الجداول"""
    global _engine, _session_factory

    _engine = create_async_engine(database_url, echo=False)
    _register_sqlite_pragmas(_engine)
    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return _engine


def get_session_factory():
    return _session_factory


async def insert_event_if_new(session, **fields) -> bool:
    """إدراج حدث مع تجاهل التعارض على source_id ذرّياً (INSERT ... ON CONFLICT
    DO NOTHING). يعيد True إذا أُدرِج فعلاً، False إذا كان مكرّراً.

    يحل محل نمط 'SELECT ثم add' الذي يسبب سباقاً يُسقط دفعات كاملة عند التزامن،
    ويلغي استعلام SELECT لكل مقال (تحسين أداء)."""
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    stmt = (
        sqlite_insert(Event)
        .values(**fields)
        .on_conflict_do_nothing(index_elements=["source_id"])
    )
    result = await session.execute(stmt)
    return bool(result.rowcount)


async def prune_old_data(events_days: int = 30, flights_days: int = 7) -> dict:
    """حذف البيانات الأقدم من عتبات الاحتفاظ — يمنع نمو قاعدة البيانات بلا حدود.

    - الأحداث وأخبار القادة: أقدم من events_days.
    - مسارات الطيران (تنمو الأسرع): أقدم من flights_days.
    يعيد عدد الصفوف المحذوفة لكل جدول.
    """
    if not _session_factory:
        return {}

    now = datetime.now(timezone.utc)
    events_cutoff = now - timedelta(days=events_days)
    flights_cutoff = now - timedelta(days=flights_days)
    removed: dict = {}

    async with _session_factory() as session:
        r1 = await session.execute(delete(Event).where(Event.collected_at < events_cutoff))
        r2 = await session.execute(
            delete(FlightTrack).where(FlightTrack.tracked_at < flights_cutoff)
        )
        r3 = await session.execute(
            delete(IranianLeaderNews).where(IranianLeaderNews.collected_at < events_cutoff)
        )
        await session.commit()
        removed = {
            "events": r1.rowcount or 0,
            "flight_tracks": r2.rowcount or 0,
            "iranian_leader_news": r3.rowcount or 0,
        }

    total = sum(removed.values())
    if total:
        logger.info(f"🧹 تنظيف البيانات: حُذف {total} صفاً {removed}")
    return removed
