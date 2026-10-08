"""رصد - طيّ الأحداث المتشابهة في «قصص» عند الإخراج.

`cluster_id` يُسنده `processors/clustering` دوريًا. هنا نطوي قائمة أحداث
مرتّبة (الأحدث أولًا) إلى قصة واحدة لكل مجموعة: الممثّل هو الأعلى خطرًا
ثم الأحدث، ومعه قائمة المصادر الأخرى — فتعرض الواجهة «٣ مصادر» بدل ثلاث
بطاقات متطابقة. تعدّد المصادر المستقلة مؤشر ثقة بحد ذاته.
"""
from __future__ import annotations

from ..models.database import Event
from ..processors.clustering import story_rank as _rank
from ._serializers import serialize_event

MAX_RELATED = 8


def group_stories(events: list[Event]) -> list[list[Event]]:
    """مجموعات بترتيب أول ظهور (يحفظ ترتيب الاستعلام)."""
    groups: dict[int, list[Event]] = {}
    for ev in events:
        groups.setdefault(ev.cluster_id or ev.id, []).append(ev)
    return list(groups.values())


def representatives(events: list[Event]) -> list[Event]:
    """ممثّل واحد لكل قصة — للمؤشرات التي يجب ألّا تعدّ الخبر الواحد مرات."""
    return [max(g, key=_rank) for g in group_stories(events)]


def serialize_story(group: list[Event], rep: Event | None = None) -> dict:
    """قصة بممثّلها ومصادرها. `rep` يفرض الممثّل (رابط مشاركة لخبر بعينه، أو
    الأعلى أثرًا في عدسة المملكة) بدل الأعلى خطرًا."""
    rep = rep if rep is not None else max(group, key=_rank)
    # تسلسل واحد لكل حدث: كل استدعاء يفكّ extra_data ويُنظّف العنوان والوصف
    serialized = {e.id: serialize_event(e) for e in group}
    data = serialized[rep.id]
    others = [e for e in sorted(group, key=lambda e: e.event_date or 0) if e.id != rep.id]
    sources = {s["source_name"] for s in serialized.values()}
    dates = [e.event_date for e in group if e.event_date]
    data.update({
        "story_size": len(group),
        "story_source_count": len(sources),
        "story_first_seen": min(dates).isoformat() if dates else data["event_date"],
        "story_related": [
            {
                "id": e.id,
                "title": serialized[e.id]["title"],
                "source_name": serialized[e.id]["source_name"],
                "url": e.url,
                "event_date": e.event_date.isoformat() if e.event_date else None,
            }
            for e in others[:MAX_RELATED]
        ],
    })
    return data


def collapse(events: list[Event], limit: int) -> list[dict]:
    return [serialize_story(g) for g in group_stories(events)[:limit]]
