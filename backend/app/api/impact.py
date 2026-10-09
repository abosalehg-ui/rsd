"""رصد - نقاط API لعدسة «الأثر على المملكة».

- `/ksa`      المؤشر العام مع اتجاهه وسلسلته الزمنية، والتوزيع حسب القطاع،
              والأحداث الأعلى أثرًا بمكوّناتها، وبنود «راقِب».
- `/sectors`  القطاعات ومعاملات المعادلة (لشرح المؤشر في الواجهة).

المؤشر بصيغة المؤشر النووي نفسها (60% أعلى أثر منفرد + 40% متوسط أعلى عشر
قصص)، محسوبًا على ممثّلي القصص: الخبر المكرّر من عشرة مصادر يُعدّ مرة.
بنود «راقِب» قاعدية لا مولَّدة: كل قطاع ارتفع مؤشره عن الفترة السابقة بـ
`WATCH_MIN_DELTA` نقطة فأكثر وبلغ `WATCH_MIN_INDEX`.

المنهجية الكاملة: docs/ksa-impact-methodology.md.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query
from sqlalchemy import and_, func, or_, select

from .. import cache
from ..config import get_settings
from ..models.database import Event, get_session_factory
from ..processors.impact import (
    MENTION_FACTOR,
    PROXIMITY_FACTOR,
    SECTOR_KEYS,
    SEVERITY_FACTOR,
)
from ..processors.impact_index import (  # noqa: F401 - TREND_FLAT يُعاد تصديره
    INDEX_MAX_WEIGHT,
    INDEX_TOP_N,
    INDEX_TOP_WEIGHT,
    TREND_FLAT,
    ImpactRow,
    load_impact_rows,
    snapshot,
    trend_of,
)
from ..processors.nuclear import SOURCE_TRUST, severity_from_score
from ._stories import serialize_story

router = APIRouter(prefix="/api/impact", tags=["impact"])

TOP_EVENTS = 10
WATCH_MIN_DELTA = 10.0    # ارتفاع قطاع بهذا القدر فأكثر عن الفترة السابقة…
WATCH_MIN_INDEX = 25.0    # …وبلوغه هذا الحد = بند «راقِب»
_SERIES_BUCKETS = 12


def _sector_breakdown(current: list[ImpactRow], previous: list[ImpactRow] | None) -> list[dict]:
    """`previous=None`: الفترة السابقة خارج نافذة الاحتفاظ، فلا مقارنة."""
    out = []
    for key in SECTOR_KEYS:
        cur = snapshot([r for r in current if key in r.sectors])
        prev_index = None if previous is None else snapshot([r for r in previous if key in r.sectors])["index"]
        delta = None if prev_index is None else round(cur["index"] - prev_index, 1)
        out.append({
            "key": key,
            "index": cur["index"],
            "prev_index": prev_index,
            "delta": delta,
            "trend": trend_of(delta),
            "stories": cur["stories"],
            "max": cur["max"],
            "top_event_id": cur["reps"][0].id if cur["reps"] else None,
        })
    out.sort(key=lambda s: (s["index"], s["stories"]), reverse=True)
    return out


def watch_items(sectors: list[dict]) -> list[dict]:
    """بنود «راقِب»: قطاعات ارتفع أثرها بوضوح عن الفترة السابقة."""
    items = [
        {k: s[k] for k in ("key", "index", "prev_index", "delta", "stories", "top_event_id")}
        for s in sectors
        if s["delta"] is not None and s["delta"] >= WATCH_MIN_DELTA and s["index"] >= WATCH_MIN_INDEX
    ]
    items.sort(key=lambda s: s["delta"], reverse=True)
    return items


def _series(current: list[ImpactRow], since: datetime, hours: int) -> list[dict]:
    step = timedelta(hours=hours) / _SERIES_BUCKETS
    buckets: list[list[ImpactRow]] = [[] for _ in range(_SERIES_BUCKETS)]
    for r in current:
        if r.date is None:
            continue
        idx = min(int((r.date - since) / step), _SERIES_BUCKETS - 1)
        if idx >= 0:
            buckets[idx].append(r)
    series = []
    for i, bucket in enumerate(buckets):
        s = snapshot(bucket)
        series.append({"t": (since + step * (i + 1)).isoformat(), "value": s["index"], "stories": s["stories"]})
    return series


async def _top_stories(session, reps: list[ImpactRow], since: datetime, until: datetime) -> list[dict]:
    """أعلى القصص أثرًا مسلسلة كاملة (بمصادرها ومكوّنات أثرها) — أخبار القصة
    في الفترة تُجلب هنا لأن `load_impact_rows` تحمّل ممثّليها وحدهم."""
    top = reps[:TOP_EVENTS]
    if not top:
        return []
    wanted = [r.story for r in top]
    events = (await session.execute(
        select(Event).where(and_(
            or_(Event.cluster_id.in_(wanted), Event.id.in_(wanted)),
            Event.event_date >= since, Event.event_date < until, Event.ksa_impact.isnot(None),
        ))
    )).scalars().all()
    by_story: dict[int, list[Event]] = {}
    for e in events:
        by_story.setdefault(e.cluster_id or e.id, []).append(e)
    stories = []
    for r in top:
        group = by_story.get(r.story)
        if not group:
            continue
        rep = next((e for e in group if e.id == r.id), None)
        stories.append(serialize_story(group, rep=rep))
    return stories


async def _count_events(session, since: datetime, until: datetime) -> int:
    return (await session.execute(
        select(func.count(Event.id)).where(and_(
            Event.event_date >= since, Event.event_date < until, Event.ksa_impact.isnot(None),
        ))
    )).scalar() or 0


def formula() -> dict:
    return {
        "max_weight": INDEX_MAX_WEIGHT,
        "top_mean_weight": INDEX_TOP_WEIGHT,
        "top_n": INDEX_TOP_N,
        "severity": SEVERITY_FACTOR,
        "proximity": PROXIMITY_FACTOR,
        "mention": MENTION_FACTOR,
        "source_trust": SOURCE_TRUST,
        "watch_min_delta": WATCH_MIN_DELTA,
        "watch_min_index": WATCH_MIN_INDEX,
    }


async def build_ksa_impact(hours: int, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(hours=hours)
    prev_since = since - timedelta(hours=hours)
    # الفترة السابقة أقدم من نافذة الاحتفاظ = بياناتها محذوفة لا «صفر أثر»؛
    # مقارنتها بالحالية تعلن صعودًا وبنود «راقِب» كاذبة
    comparable = prev_since >= now - timedelta(days=get_settings().retention_events_days)
    async with get_session_factory()() as session:
        current, truncated = await load_impact_rows(session, since, now)
        previous = None
        if comparable:
            previous, prev_truncated = await load_impact_rows(session, prev_since, since)
            truncated = truncated or prev_truncated
        snap = snapshot(current)
        top_events = await _top_stories(session, snap["reps"], since, now)
        events = await _count_events(session, since, now)

    prev_index = snapshot(previous)["index"] if previous is not None else None
    delta = None if prev_index is None else round(snap["index"] - prev_index, 1)
    sectors = _sector_breakdown(current, previous)
    return {
        "period_hours": hours,
        "generated_at": now.isoformat(),
        "index": snap["index"],
        "level": severity_from_score(snap["index"]),
        "prev_index": prev_index,
        "delta": delta,
        "trend": trend_of(delta),
        "comparable": comparable,
        "components": {
            "max": snap["max"],
            "top_mean": snap["top_mean"],
            "max_weight": INDEX_MAX_WEIGHT,
            "top_mean_weight": INDEX_TOP_WEIGHT,
            "top_n": INDEX_TOP_N,
        },
        "stories": snap["stories"],
        "events": events,
        "truncated": truncated,
        "series": _series(current, since, hours),
        "sectors": sectors,
        "watch": watch_items(sectors),
        "top_events": top_events,
        "formula": formula(),
    }


@router.get("/ksa")
async def ksa_impact(hours: int = Query(default=48, ge=1, le=720)):
    """مؤشر الأثر على المملكة (0-100) مع اتجاهه وقطاعاته وأعلى الأحداث أثرًا."""
    ttl = get_settings().response_cache_seconds
    return await cache.cached(("impact.ksa", hours), ttl, lambda: build_ksa_impact(hours))


@router.get("/sectors")
async def list_sectors():
    """القطاعات ومعاملات المعادلة — مرجع شرح المؤشر."""
    return {"sectors": list(SECTOR_KEYS), "formula": formula()}
