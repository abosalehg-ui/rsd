"""رصد (Rasad) - نماذج قاعدة البيانات"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    delete,
    event,
    func,
    select,
    text,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .. import cache

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

    # التوقيت — timezone=True كي لا يُجرَّد الإزاحة عند الكتابة (تبقى القيم aware
    # وتُقارَن صحيحاً حتى على PostgreSQL).
    event_date = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    collected_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # بيانات إضافية (JSON string)
    extra_data = Column(Text)

    # Iran OSINT additions
    confidence = Column(String(10), default="LOW")   # HIGH, MEDIUM, LOW
    video_url = Column(Text)                          # رابط فيديو OSINT

    # الرصد النووي والإشعاعي (v2.0) — تُملأ من `processors.text_analysis.analyze`
    topic = Column(String(40))              # موضوع نووي/إشعاعي (processors/nuclear.TOPICS)
    risk_score = Column(Float)              # درجة الخطر 0-100 (للأحداث النووية/الإشعاعية فقط)
    facility_id = Column(String(40))        # منشأة مذكورة (data/nuclear_facilities.json)
    geo_precision = Column(String(12))      # facility | city | region | country | none
    cluster_id = Column(Integer)            # معرّف «القصة»: أول حدث في مجموعة الأخبار المتشابهة

    # عدسة الأثر على المملكة — تُملأ من `processors.impact` لكل الأحداث
    impact_sectors = Column(Text)           # JSON: قائمة القطاعات (processors/impact.SECTOR_KEYS)
    ksa_impact = Column(Float)              # درجة الأثر 0-100؛ مكوّناتها في extra_data.impact

    __table_args__ = (
        Index("idx_events_date", "event_date"),
        Index("idx_events_category", "category"),
        Index("idx_events_country", "country_code"),
        Index("idx_events_source", "source"),
        Index("idx_events_severity", "severity"),
        # يستخدمه prune_old_data و/api/collectors/status — بدونه مسح كامل
        Index("idx_events_collected", "collected_at"),
        # مركّب: /api/collectors/status يبحث بـ (source, collected_at) معاً
        Index("idx_events_source_collected", "source", "collected_at"),
        Index("idx_events_topic", "topic"),
        Index("idx_events_cluster", "cluster_id"),
        Index("idx_events_facility", "facility_id"),
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

    tracked_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_flight_icao", "icao24"),
        Index("idx_flight_military", "is_military"),
        Index("idx_flight_time", "tracked_at"),
        # مركّب: /flights/military/* يفلتر بـ (is_military, tracked_at) معاً
        Index("idx_flight_mil_time", "is_military", "tracked_at"),
    )


class IranianLeaderNews(Base):
    """أخبار القادة الإيرانيين"""
    __tablename__ = "iranian_leader_news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    leader_id = Column(Integer, nullable=False)
    leader_name = Column(String(100))
    title = Column(Text)
    url = Column(Text)
    news_date = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    collected_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_leader_news_id", "leader_id"),
        Index("idx_leader_news_date", "news_date"),
        # تستخدمه وظيفة الاحتفاظ (prune_old_data) — بدونه مسح كامل للجدول
        Index("idx_leader_news_collected", "collected_at"),
    )


class MarketQuote(Base):
    """قيم يومية لسلاسل الطاقة والأسواق من FRED (انظر collectors/markets).

    `observed_at` تاريخ الملاحظة كما ينشره FRED (يوم تداول، لا لحظة جلب)،
    و`fetched_at` وقت آخر جلب لها. صف واحد لكل (رمز، تاريخ): FRED يراجع
    القيم أحيانًا فيُحدَّث الصف بدل تكراره.
    """
    __tablename__ = "market_quotes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), nullable=False)               # رمز سلسلة FRED، مثل DCOILBRENTEU
    observed_at = Column(Date, nullable=False)
    value = Column(Float, nullable=False)
    fetched_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("code", "observed_at", name="uq_market_code_date"),
        Index("idx_market_observed", "observed_at"),
    )


class EventLink(Base):
    """رابط «سبب ← أثر» محتمل بين قصتين مختلفتين (انظر processors/causal).

    `cause_id` و`effect_id` معرّفا القصتين (`cluster_id` = معرّف أول خبر فيها)،
    لا الأخبار الخام. `method` = "rule" للمحرّك القاعدي (الوحيد حاليًا).
    `evidence` (JSON) يحمل الكيانات المشتركة والفارق الزمني ومكوّنات الثقة
    والعبارات المطابِقة — تعرضها الواجهة كي يُفهم لماذا رُبط الحدثان.
    """
    __tablename__ = "event_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cause_id = Column(Integer, nullable=False)
    effect_id = Column(Integer, nullable=False)
    relation_ar = Column(Text, nullable=False)
    relation_en = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)              # 0-1
    method = Column(String(10), nullable=False, default="rule")
    rule_id = Column(String(60))
    evidence = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("cause_id", "effect_id", name="uq_event_link_pair"),
        Index("idx_event_links_effect", "effect_id"),
        Index("idx_event_links_confidence", "confidence"),
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


# أعمدة أُضيفت بعد الإصدار الأول — نضمن وجودها على قواعد بيانات قديمة.
# (source_id فريد؛ لا نُدرجه هنا لأنه من الإنشاء الأصلي.)
_EVENTS_ADDED_COLUMNS = {
    "confidence": "VARCHAR(10) DEFAULT 'LOW'",
    "video_url": "TEXT",
    "topic": "VARCHAR(40)",
    "risk_score": "FLOAT",
    "facility_id": "VARCHAR(40)",
    "geo_precision": "VARCHAR(12)",
    "cluster_id": "INTEGER",
    "impact_sectors": "TEXT",
    "ksa_impact": "FLOAT",
}


async def _migrate_sqlite(conn) -> None:
    """ترقية بسيطة لـSQLite: يضيف الأعمدة الناقصة على جدول قائم.

    `create_all` لا يضيف أعمدة لجدول موجود، فمستخدم يُرقّي تطبيق سطح المكتب
    (قاعدته تعيش في %LOCALAPPDATA% وتبقى بين الإصدارات) يصطدم بـ
    'no such column: confidence'. نفحص الأعمدة الحالية ونضيف الناقص.
    """
    rows = await conn.execute(text("PRAGMA table_info(events)"))
    existing = {r[1] for r in rows.fetchall()}
    for col, ddl in _EVENTS_ADDED_COLUMNS.items():
        if col not in existing:
            await conn.execute(text(f"ALTER TABLE events ADD COLUMN {col} {ddl}"))
            logger.info("🛠️ ترقية: أُضيف العمود events.%s", col)
    # create_all يتخطّى الجداول القائمة بفهارسها، فنُنشئ فهارس الأعمدة المضافة هنا
    for name, col in (
        ("idx_events_topic", "topic"),
        ("idx_events_cluster", "cluster_id"),
        ("idx_events_facility", "facility_id"),
    ):
        await conn.execute(text(f"CREATE INDEX IF NOT EXISTS {name} ON events ({col})"))


async def init_db(database_url: str):
    """تهيئة قاعدة البيانات وإنشاء/ترقية الجداول."""
    global _engine, _session_factory

    _engine = create_async_engine(database_url, echo=False)
    _register_sqlite_pragmas(_engine)
    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

    is_sqlite = _engine.url.get_backend_name().startswith("sqlite")
    async with _engine.begin() as conn:
        if is_sqlite:
            # نُرقّي قبل create_all كي نضيف الأعمدة لجدول قائم دون كسر.
            has_events = (await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='events'")
            )).first() is not None
            if has_events:
                await _migrate_sqlite(conn)
        await conn.run_sync(Base.metadata.create_all)

    return _engine


def get_session_factory():
    return _session_factory


def _upsert_insert(dialect_name: str):
    """`insert()` الخاص باللهجة والداعم لـ ON CONFLICT.

    SQLite و PostgreSQL يدعمان `on_conflict_do_nothing`. غيرهما يقع على
    المسار الاحتياطي في `insert_event_if_new`.
    """
    if dialect_name == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        return sqlite_insert
    if dialect_name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        return pg_insert
    return None


def _with_impact(fields: dict) -> dict:
    """يضيف حقول الأثر على المملكة إن لم يحسبها الجامع — نقطة واحدة تغطّي
    كل الجامعين بدل تكرار الاستدعاء في كل منها."""
    if "ksa_impact" in fields:
        return fields
    from ..processors.impact import impact_fields

    return {**fields, **impact_fields(fields)}


async def insert_event_if_new(session, **fields) -> bool:
    """إدراج حدث مع تجاهل التعارض على source_id ذرّياً (INSERT ... ON CONFLICT
    DO NOTHING). يعيد True إذا أُدرِج فعلاً، False إذا كان مكرّراً.

    يحل محل نمط 'SELECT ثم add' الذي يسبب سباقاً يُسقط دفعات كاملة عند التزامن،
    ويلغي استعلام SELECT لكل مقال (تحسين أداء).

    يختار اللهجة من الاتصال (DATABASE_URL يقبل أي محرّك) ويسقط على
    SAVEPOINT + IntegrityError لما عدا SQLite وPostgreSQL.
    """
    fields = _with_impact(fields)
    dialect_name = session.bind.dialect.name if session.bind is not None else "sqlite"
    insert_fn = _upsert_insert(dialect_name)

    if insert_fn is not None:
        stmt = (
            insert_fn(Event)
            .values(**fields)
            .on_conflict_do_nothing(index_elements=["source_id"])
        )
        result = await session.execute(stmt)
        return bool(result.rowcount)

    # مسار احتياطي محايد: نحاول الإدراج داخل SAVEPOINT ونبتلع تعارض التفرّد
    # وحده — يبقى ذرّياً ولا يُفسد المعاملة الجارية عند الفشل.
    try:
        async with session.begin_nested():
            session.add(Event(**fields))
        return True
    except IntegrityError:
        return False


async def prune_old_data(
    events_days: int = 30, flights_days: int = 7, markets_days: int = 400,
) -> dict:
    """حذف البيانات الأقدم من عتبات الاحتفاظ — يمنع نمو قاعدة البيانات بلا حدود.

    - الأحداث وأخبار القادة: أقدم من events_days.
    - مسارات الطيران (تنمو الأسرع): أقدم من flights_days.
    - قيم الأسواق: أقدم من markets_days بتاريخ الملاحظة (صف يومي لكل سلسلة،
      فالنافذة أطول بكثير من الأحداث ليبقى مخطط التسعين يومًا ممتلئًا).
    - روابط السبب والأثر: كل رابط حُذفت قصة أحد طرفيه (يتبع الأحداث).
    يعيد عدد الصفوف المحذوفة لكل جدول.
    """
    if not _session_factory:
        return {}

    now = datetime.now(timezone.utc)
    events_cutoff = now - timedelta(days=events_days)
    flights_cutoff = now - timedelta(days=flights_days)
    markets_cutoff = (now - timedelta(days=markets_days)).date()
    removed: dict = {}

    async with _session_factory() as session:
        r1 = await session.execute(delete(Event).where(Event.collected_at < events_cutoff))
        r2 = await session.execute(
            delete(FlightTrack).where(FlightTrack.tracked_at < flights_cutoff)
        )
        r3 = await session.execute(
            delete(IranianLeaderNews).where(IranianLeaderNews.collected_at < events_cutoff)
        )
        r4 = await session.execute(
            delete(MarketQuote).where(MarketQuote.observed_at < markets_cutoff)
        )
        # طرفا الرابط معرّفا قصتين (`cluster_id` = أول خبر فيها)، وأول خبر هو
        # أقدمها جمعًا فأول ما يُحذف — القصة حيّة ما بقي فيها خبر واحد
        live_stories = select(func.coalesce(Event.cluster_id, Event.id))
        r5 = await session.execute(
            delete(EventLink).where(
                EventLink.cause_id.notin_(live_stories) | EventLink.effect_id.notin_(live_stories)
            )
        )
        await session.commit()
        removed = {
            "events": r1.rowcount or 0,
            "flight_tracks": r2.rowcount or 0,
            "iranian_leader_news": r3.rowcount or 0,
            "market_quotes": r4.rowcount or 0,
            "event_links": r5.rowcount or 0,
        }

    total = sum(removed.values())
    if total:
        cache.invalidate()
        logger.info(f"🧹 تنظيف البيانات: حُذف {total} صفاً {removed}")
    return removed
