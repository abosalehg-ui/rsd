"""رصد - طيّ الأحداث المتشابهة في «قصص» عند الإخراج.

`cluster_id` يُسنده `processors/clustering` دوريًا. هنا نطوي قائمة أحداث
مرتّبة (الأحدث أولًا) إلى قصة واحدة لكل مجموعة: الممثّل هو الأعلى خطرًا
ثم الأحدث، ومعه قائمة المصادر الأخرى — فتعرض الواجهة «٣ مصادر» بدل ثلاث
بطاقات متطابقة. تعدّد المصادر المستقلة مؤشر ثقة بحد ذاته.
"""
from __future__ import annotations

from ..models.database import Event
from ._serializers import serialize_event

_SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}
MAX_RELATED = 8


def _rank(ev: Event) -> tuple:
    return (
        ev.risk_score if ev.risk_score is not None else -1,
        _SEVERITY_RANK.get(ev.severity or "", 0),
        ev.event_date.timestamp() if ev.event_date else 0,
    )


def group_stories(events: list[Event]) -> list[list[Event]]:
    """مجموعات بترتيب أول ظهور (يحفظ ترتيب الاستعلام)."""
    groups: dict[int, list[Event]] = {}
    for ev in events:
        groups.setdefault(ev.cluster_id or ev.id, []).append(ev)
    return list(groups.values())


def representatives(events: list[Event]) -> list[Event]:
    """ممثّل واحد لكل قصة — للمؤشرات التي يجب ألّا تعدّ الخبر الواحد مرات."""
    return [max(g, key=_rank) for g in group_stories(events)]


def serialize_story(group: list[Event]) -> dict:
    rep = max(group, key=_rank)
    data = serialize_event(rep)
    others = [e for e in sorted(group, key=lambda e: e.event_date or 0) if e.id != rep.id]
    sources = {serialize_event(e)["source_name"] for e in group}
    dates = [e.event_date for e in group if e.event_date]
    data.update({
        "story_size": len(group),
        "story_source_count": len(sources),
        "story_first_seen": min(dates).isoformat() if dates else data["event_date"],
        "story_related": [
            {
                "id": e.id,
                "title": serialize_event(e)["title"],
                "source_name": serialize_event(e)["source_name"],
                "url": e.url,
                "event_date": e.event_date.isoformat() if e.event_date else None,
            }
            for e in others[:MAX_RELATED]
        ],
    })
    return data


def collapse(events: list[Event], limit: int) -> list[dict]:
    return [serialize_story(g) for g in group_stories(events)[:limit]]
