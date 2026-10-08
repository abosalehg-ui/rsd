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
from sqlalchemy import and_, desc, select

from ..models.database import Event, get_session_factory
from ..processors.impact import (
    MENTION_FACTOR,
    PROXIMITY_FACTOR,
    SECTOR_KEYS,
    SEVERITY_FACTOR,
    parse_sectors,
)
from ..processors.nuclear import SOURCE_TRUST, severity_from_score
from ._stories import serialize_story

router = APIRouter(prefix="/api/impact", tags=["impact"])

INDEX_MAX_WEIGHT = 0.6
INDEX_TOP_WEIGHT = 0.4
# عشر قصص لا خمس كالمؤشر النووي: العدسة تشمل كل الأحداث فحجمها أكبر بكثير
INDEX_TOP_N = 10
TOP_EVENTS = 10
TREND_FLAT = 3.0          # فرق أقل من هذا (نقاط) = مستقر
WATCH_MIN_DELTA = 10.0    # ارتفاع قطاع بهذا القدر فأكثر عن الفترة السابقة…
WATCH_MIN_INDEX = 25.0    # …وبلوغه هذا الحد = بند «راقِب»
_SERIES_BUCKETS = 12
# سقف الصفوف المحمّلة لكل فترة (أعمدة خفيفة فقط؛ الصفوف الكاملة لأعلى القصص)
_ROW_CAP = 8000


class _Row:
    """صفّ خفيف للحساب: لا عنوان ولا وصف ولا extra_data."""

    __slots__ = ("id", "story", "date", "score", "sectors")

    def __init__(self, id_, cluster_id, date, score, sectors_raw):
        self.id = id_
        self.story = cluster_id or id_
        self.date = date if date is None or date.tzinfo else date.replace(tzinfo=timezone.utc)
        self.score = float(score or 0.0)
        self.sectors = parse_sectors(sectors_raw)


async def _load_rows(session, since: datetime, until: datetime) -> list[_Row]:
    rows = (await session.execute(
        select(Event.id, Event.cluster_id, Event.event_date, Event.ksa_impact, Event.impact_sectors)
        .where(and_(Event.event_date >= since, Event.event_date < until, Event.ksa_impact.isnot(None)))
        .order_by(desc(Event.event_date))
        .limit(_ROW_CAP)
    )).all()
    return [_Row(*r) for r in rows]


def _story_reps(rows: list[_Row]) -> list[_Row]:
    """ممثّل واحد لكل قصة (الأعلى أثرًا)، مرتّبة تنازليًا."""
    best: dict[int, _Row] = {}
    for r in rows:
        cur = best.get(r.story)
        if cur is None or r.score > cur.score:
            best[r.story] = r
    return sorted(best.values(), key=lambda r: r.score, reverse=True)


def snapshot(rows: list[_Row]) -> dict:
    """المؤشر على صفوف: 60% أعلى أثر + 40% متوسط أعلى عشر قصص."""
    reps = _story_reps(rows)
    if not reps:
        return {"index": 0.0, "max": 0.0, "top_mean": 0.0, "stories": 0, "reps": []}
    top = reps[:INDEX_TOP_N]
    peak = top[0].score
    top_mean = sum(r.score for r in top) / len(top)
    return {
        "index": round(INDEX_MAX_WEIGHT * peak + INDEX_TOP_WEIGHT * top_mean, 1),
        "max": round(peak, 1),
        "top_mean": round(top_mean, 1),
        "stories": len(reps),
        "reps": reps,
    }


def trend_of(delta: float) -> str:
    if delta >= TREND_FLAT:
        return "up"
    if delta <= -TREND_FLAT:
        return "down"
    return "flat"


def _sector_breakdown(current: list[_Row], previous: list[_Row]) -> list[dict]:
    out = []
    for key in SECTOR_KEYS:
        cur = snapshot([r for r in current if key in r.sectors])
        prev = snapshot([r for r in previous if key in r.sectors])
        delta = round(cur["index"] - prev["index"], 1)
        out.append({
            "key": key,
            "index": cur["index"],
            "prev_index": prev["index"],
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
        if s["delta"] >= WATCH_MIN_DELTA and s["index"] >= WATCH_MIN_INDEX
    ]
    items.sort(key=lambda s: s["delta"], reverse=True)
    return items


def _series(current: list[_Row], since: datetime, hours: int) -> list[dict]:
    step = timedelta(hours=hours) / _SERIES_BUCKETS
    buckets: list[list[_Row]] = [[] for _ in range(_SERIES_BUCKETS)]
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


async def _top_stories(session, reps: list[_Row], current: list[_Row]) -> list[dict]:
    """أعلى القصص أثرًا مسلسلة كاملة (بمصادرها ومكوّنات أثرها)."""
    top = reps[:TOP_EVENTS]
    if not top:
        return []
    wanted = {r.story for r in top}
    ids = [r.id for r in current if r.story in wanted]
    events = (await session.execute(select(Event).where(Event.id.in_(ids)))).scalars().all()
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
    async with get_session_factory()() as session:
        current = await _load_rows(session, since, now)
        previous = await _load_rows(session, prev_since, since)
        snap = snapshot(current)
        prev = snapshot(previous)
        top_events = await _top_stories(session, snap["reps"], current)

    delta = round(snap["index"] - prev["index"], 1)
    sectors = _sector_breakdown(current, previous)
    return {
        "period_hours": hours,
        "generated_at": now.isoformat(),
        "index": snap["index"],
        "level": severity_from_score(snap["index"]),
        "prev_index": prev["index"],
        "delta": delta,
        "trend": trend_of(delta),
        "components": {
            "max": snap["max"],
            "top_mean": snap["top_mean"],
            "max_weight": INDEX_MAX_WEIGHT,
            "top_mean_weight": INDEX_TOP_WEIGHT,
            "top_n": INDEX_TOP_N,
        },
        "stories": snap["stories"],
        "events": len(current),
        "series": _series(current, since, hours),
        "sectors": sectors,
        "watch": watch_items(sectors),
        "top_events": top_events,
        "formula": formula(),
    }


@router.get("/ksa")
async def ksa_impact(hours: int = Query(default=48, ge=1, le=720)):
    """مؤشر الأثر على المملكة (0-100) مع اتجاهه وقطاعاته وأعلى الأحداث أثرًا."""
    return await build_ksa_impact(hours)


@router.get("/sectors")
async def list_sectors():
    """القطاعات ومعاملات المعادلة — مرجع شرح المؤشر."""
    return {"sectors": list(SECTOR_KEYS), "formula": formula()}
