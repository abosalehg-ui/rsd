"""رصد - الدورة التحليلية: تجميع القصص، ربط سلاسل السبب والأثر، وإعادة تحليل
الصفوف المخزّنة بمحرّك أقدم.

منطق تطبيقي ينسّق المعالجات (`processors/`) فوق قاعدة البيانات، لا نموذج
بيانات — فمكانه خارج `models/database.py` الذي يبقى للجداول والجلسة والترقية
وسياسة الاحتفاظ. يستدعيه المجدول (`scheduler.py`) والإقلاع (`main.py`)
والتحديث اليدوي (`api/system.py`).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from . import cache
from .config import get_settings
from .models.database import Event, get_session_factory
from .processors.causal import link_story_chains
from .processors.clustering import assign_story_clusters
from .processors.impact import impact_fields
from .processors.normalize import clean_text, parse_extra
from .processors.text_analysis import analyze, event_fields

logger = logging.getLogger("rasad.analysis")


# مصادر يحدّد جامعها التصنيف والموقع بنفسه (بيانات منظّمة) فلا يُعاد تحليلها
_BACKFILL_SKIP_SOURCES = ("ucdp", "iran_osint")


async def backfill_analysis(batch: int = 500) -> int:
    """يعيد تحليل الأحداث المخزّنة بمحرّك أقدم من الحالي.

    قاعدة سطح المكتب تبقى بين الإصدارات، فبدون هذا تظهر أحداث الأيام الثلاثين
    الماضية بلا موضوع نووي ولا درجة خطر ولا أثر على المملكة حتى تنتهي صلاحيتها.
    مرحلتان على دفعات، كل منهما تتوقّف حين لا يبقى شيء؛ تشغيله مرة ثانية لا
    يفعل شيئًا:

    1. صفوف ما قبل v2.0 (لا `geo_precision`): تصنيف وموقع ودرجة خطر نووي.
    2. صفوف بلا `ksa_impact` (كل المصادر، ومنها الصفوف المعاد تحليلها للتو):
       وسم القطاعات ودرجة الأثر من الحقول المخزّنة.
    """
    session_factory = get_session_factory()
    if not session_factory:
        return 0
    total = await _backfill_v2(batch)
    impacted = await _backfill_impact(batch)
    if total:
        logger.info("🔁 إعادة تحليل %s حدثًا مخزّنًا بمحرّك v2.0", total)
    if impacted:
        logger.info("🔁 حساب الأثر على المملكة لـ %s حدثًا مخزّنًا", impacted)
    return total + impacted


async def _backfill_v2(batch: int) -> int:
    session_factory = get_session_factory()
    total = 0
    while True:
        async with session_factory() as session:
            rows = (await session.execute(
                select(Event)
                .where(Event.geo_precision.is_(None), Event.source.notin_(_BACKFILL_SKIP_SOURCES))
                .limit(batch)
            )).scalars().all()
            if not rows:
                break
            for ev in rows:
                title = clean_text(ev.title)
                description = clean_text(ev.description)
                extra = parse_extra(ev.extra_data)
                kind = extra.get("source_kind", "news")
                forced = extra.get("feed_category") == "nuclear" or kind in ("official", "specialist")
                a = analyze(
                    title, description,
                    base_category="nuclear" if forced else "general",
                    source_kind=kind,
                )
                for key, value in event_fields(a).items():
                    setattr(ev, key, value)
                ev.title = title
                ev.description = description
                ev.extra_data = json.dumps({**extra, **a.extra}, ensure_ascii=False)
                # التصنيف والموقع تغيّرا: الأثر المحسوب سابقًا (إن وُجد) لم يعد صالحًا
                ev.ksa_impact = None
            await session.commit()
            total += len(rows)
    return total


_IMPACT_INPUTS = (
    "title", "description", "severity", "latitude", "longitude", "source", "confidence", "extra_data",
)


async def _backfill_impact(batch: int) -> int:
    session_factory = get_session_factory()
    total = 0
    while True:
        async with session_factory() as session:
            rows = (await session.execute(
                select(Event).where(Event.ksa_impact.is_(None)).limit(batch)
            )).scalars().all()
            if not rows:
                break
            for ev in rows:
                derived = impact_fields({k: getattr(ev, k) for k in _IMPACT_INPUTS})
                for key, value in derived.items():
                    setattr(ev, key, value)
            await session.commit()
            total += len(rows)
    return total


# وقت آخر تحليل مكتمل (تجميع القصص بعد الجمع) — يعرضه الهيدر عبر /api/schedule.
# متغيّر عملية: يكفي لتطبيق سطح المكتب وuvicorn بعامل واحد.
_last_analysis_at: datetime | None = None


def last_analysis_at() -> datetime | None:
    return _last_analysis_at


async def run_story_clustering(hours: int = 72) -> int:
    """يُسند القصص للأحداث الجديدة خلال آخر `hours` ساعة (انظر processors/clustering)."""
    global _last_analysis_at
    session_factory = get_session_factory()
    if not session_factory:
        return 0

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    async with session_factory() as session:
        assigned = await assign_story_clusters(session, since)
    _last_analysis_at = datetime.now(timezone.utc)
    return assigned


_llm_notice_logged = False


async def run_causal_linking(hours: int = 72, min_confidence: float | None = None) -> dict:
    """يعيد حساب روابط السبب والأثر للقصص المرصودة خلال آخر `hours` ساعة
    (انظر processors/causal). يعمل بعد تجميع القصص لأن الروابط بين القصص."""
    global _llm_notice_logged
    session_factory = get_session_factory()
    if not session_factory:
        return {}

    settings = get_settings()
    if settings.llm_assist_enabled and not _llm_notice_logged:
        # محجوز لخطوة اختيارية لاحقة (processors/causal.Refiner) — غير منفّذة
        logger.warning("LLM_ASSIST_ENABLED مضبوط لكن الخطوة غير متوفرة في هذا الإصدار؛ الروابط قاعدية فقط.")
        _llm_notice_logged = True
    threshold = settings.causal_min_confidence if min_confidence is None else min_confidence
    async with session_factory() as session:
        return await link_story_chains(
            session, datetime.now(timezone.utc), hours=hours, min_confidence=threshold,
        )


async def run_analysis_cycle() -> dict:
    """الدورة التحليلية الدورية: تجميع القصص ثم ربط السلاسل بينها (بالترتيب)."""
    global _last_analysis_at

    assigned = await run_story_clustering()
    try:
        links = await run_causal_linking()
    except Exception as e:  # noqa: BLE001 - فشل الربط لا يوقف التجميع ولا الجدولة
        logger.error("تعذّر ربط سلاسل السبب والأثر: %s", e)
        links = {}
    # «آخر تحليل» في الهيدر = بعد الربط أيضًا، لا بعد التجميع وحده
    _last_analysis_at = datetime.now(timezone.utc)
    cache.invalidate()
    return {"clustered": assigned, "links": links}
