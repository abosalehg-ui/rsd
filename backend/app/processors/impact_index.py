"""رصد - مؤشر «الأثر على المملكة» على صفوف خفيفة: الحساب وتحميل الصفوف.

يشترك فيه `api/impact` (العدسة) و`api/markets` (التزامن اليومي) بدل أن تستورد
نقطةٌ صنفًا خاصًا من أخرى. الحساب نقي؛ `load_impact_rows` وحدها تقرأ قاعدة
البيانات (باستيراد متأخر كما في `processors/causal`).

المؤشر بصيغة المؤشر النووي نفسها (60% أعلى أثر منفرد + 40% متوسط أعلى عشر
قصص)، محسوبًا على ممثّلي القصص: الخبر المكرّر من عشرة مصادر يُعدّ مرة.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .impact import parse_sectors

INDEX_MAX_WEIGHT = 0.6
INDEX_TOP_WEIGHT = 0.4
# عشر قصص لا خمس كالمؤشر النووي: العدسة تشمل كل الأحداث فحجمها أكبر بكثير
INDEX_TOP_N = 10
TREND_FLAT = 3.0          # فرق أقل من هذا (نقاط) = مستقر
# سقف الممثّلين المحمّلين لكل فترة. يُقصّ الأدنى أثرًا لا الأقدم، فلا يمسّ
# أعلى القصص التي يُبنى عليها المؤشر، ويُعلَن القصّ في الرد (`truncated`).
ROW_CAP = 8000


class ImpactRow:
    """صفّ خفيف للحساب: لا عنوان ولا وصف ولا extra_data."""

    __slots__ = ("id", "story", "date", "score", "sectors")

    def __init__(self, id_, cluster_id, date, score, sectors_raw):
        self.id = id_
        self.story = cluster_id or id_
        self.date = date if date is None or date.tzinfo else date.replace(tzinfo=timezone.utc)
        self.score = float(score or 0.0)
        self.sectors = parse_sectors(sectors_raw)


def story_reps(rows: list[ImpactRow]) -> list[ImpactRow]:
    """ممثّل واحد لكل قصة (الأعلى أثرًا)، مرتّبة تنازليًا."""
    best: dict[int, ImpactRow] = {}
    for r in rows:
        cur = best.get(r.story)
        if cur is None or r.score > cur.score:
            best[r.story] = r
    return sorted(best.values(), key=lambda r: r.score, reverse=True)


def snapshot(rows: list[ImpactRow]) -> dict:
    """المؤشر على صفوف: 60% أعلى أثر + 40% متوسط أعلى عشر قصص."""
    reps = story_reps(rows)
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


def trend_of(delta: float | None) -> str | None:
    if delta is None:
        return None
    if delta >= TREND_FLAT:
        return "up"
    if delta <= -TREND_FLAT:
        return "down"
    return "flat"


async def load_impact_rows(
    session, since: datetime, until: datetime, *, story_level: bool = True, cap: int | None = ROW_CAP,
) -> tuple[list[ImpactRow], bool]:
    """(الصفوف، هل قُصّت) لأحداث لها `ksa_impact` بين `since` (شاملًا) و`until`.

    `story_level=True` يختصر في SQL كل قصة إلى صفّها الأعلى أثرًا لكل طقم
    قطاعات (`ROW_NUMBER` على `(القصة، القطاعات)`)، فيُحسب المؤشر وتوزيع
    القطاعات كما لو حُمّلت كل الأخبار، بحجم يقارب عدد القصص لا عدد المصادر.
    `story_level=False` يعيد الصفوف الخام (التزامن اليومي يحتاج أخبار كل يوم).
    `cap=None` بلا سقف.
    """
    from sqlalchemy import and_, func, select

    from ..models.database import Event

    cols = (Event.id, Event.cluster_id, Event.event_date, Event.ksa_impact, Event.impact_sectors)
    window = and_(Event.event_date >= since, Event.event_date < until, Event.ksa_impact.isnot(None))
    if story_level:
        rank = func.row_number().over(
            partition_by=(func.coalesce(Event.cluster_id, Event.id), Event.impact_sectors),
            order_by=(Event.ksa_impact.desc(), Event.id),
        ).label("rank")
        sub = select(*cols, rank).where(window).subquery()
        query = (
            select(sub.c.id, sub.c.cluster_id, sub.c.event_date, sub.c.ksa_impact, sub.c.impact_sectors)
            .where(sub.c.rank == 1)
            .order_by(sub.c.ksa_impact.desc(), sub.c.id)
        )
    else:
        query = select(*cols).where(window).order_by(Event.ksa_impact.desc(), Event.id)
    if cap is None:
        return [ImpactRow(*r) for r in (await session.execute(query)).all()], False
    rows = (await session.execute(query.limit(cap + 1))).all()
    return [ImpactRow(*r) for r in rows[:cap]], len(rows) > cap
