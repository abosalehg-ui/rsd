"""رصد - خدمة سلاسل السبب والأثر: تحميل الروابط وترتيب أطول السلاسل.

تستعملها `api/chains` (المسارات) و`api/nuclear` (موجز التقرير). ثقة السلسلة =
ثقة **أضعف** روابطها: السلسلة لا تكون أمتن من أضعف حلقة.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.orm import aliased

from ..api._serializers import serialize_event
from ..config import get_settings
from ..models.database import Event, EventLink, get_session_factory

MAX_DEPTH = 6          # أقصى عدد روابط في سلسلة
MAX_PATHS = 2000       # سقف المسارات المعدودة (حماية من انفجار تركيبي)
_LINK_CAP = 3000


def _node(ev: Event) -> dict:
    """تمثيل مختصر لطرف رابط (قصة) — ما يكفي لعرضه وفتحه."""
    s = serialize_event(ev)
    return {k: s[k] for k in (
        "id", "title", "url", "category", "severity", "event_date", "country_code", "country",
        "source_name", "topic", "risk_score", "ksa_impact",
    )}


def _link(link: EventLink) -> dict:
    try:
        evidence = json.loads(link.evidence) if link.evidence else {}
    except (json.JSONDecodeError, TypeError):
        evidence = {}
    return {
        "id": link.id,
        "cause_id": link.cause_id,
        "effect_id": link.effect_id,
        "relation_ar": link.relation_ar,
        "relation_en": link.relation_en,
        "confidence": link.confidence,
        "method": link.method,
        "rule_id": link.rule_id,
        "evidence": evidence,
    }


async def _events_by_id(session, ids) -> dict[int, Event]:
    ids = list(set(ids))
    out: dict[int, Event] = {}
    for i in range(0, len(ids), 500):
        rows = (await session.execute(select(Event).where(Event.id.in_(ids[i:i + 500])))).scalars()
        out.update({e.id: e for e in rows})
    return out


def _default_min() -> float:
    return get_settings().causal_min_confidence


def _paths(adj: dict[int, list[dict]], sources: list[int]) -> list[list[dict]]:
    """كل المسارات العظمى (من مصدر بلا سبب إلى أثر بلا أثر) بحدّ عمق وعدد.

    الرسم لا دوائر فيه: الأثر بعد السبب بساعة على الأقل دائمًا."""
    out: list[list[dict]] = []

    def walk(node: int, path: list[dict]) -> None:
        if len(out) >= MAX_PATHS:
            return
        nxt = adj.get(node, [])
        if not nxt or len(path) >= MAX_DEPTH:
            if path:
                out.append(list(path))
            return
        for lk in nxt:
            path.append(lk)
            walk(lk["effect_id"], path)
            path.pop()

    for s in sources:
        walk(s, [])
    return out


def rank_chains(links: list[dict], limit: int) -> list[list[dict]]:
    """أطول السلاسل أولًا، ثم الأمتن (أضعف حلقة أعلى، ثم مجموع الثقة)، ثم الأحدث؛ وتُسقط
    السلسلة التي كل روابطها ظهرت في سلسلة مختارة قبلها (جزء من أطول منها)."""
    adj: dict[int, list[dict]] = {}
    has_cause: set[int] = set()
    for lk in links:
        adj.setdefault(lk["cause_id"], []).append(lk)
        has_cause.add(lk["effect_id"])
    for lst in adj.values():
        lst.sort(key=lambda lk: -lk["confidence"])
    # الأحدث أولًا (المعرّفات تتزايد مع الزمن): إن بلغ العدّ سقف `MAX_PATHS`
    # فالمتروك سلاسل قديمة لا سلاسل اليوم
    sources = sorted((n for n in adj if n not in has_cause), reverse=True)
    paths = _paths(adj, sources)
    paths.sort(key=lambda p: (
        -len(p),
        -min(lk["confidence"] for lk in p),
        -sum(lk["confidence"] for lk in p),
        -p[-1]["effect_id"],
    ))
    chosen: list[list[dict]] = []
    covered: set[int] = set()
    for p in paths:
        ids = {lk["id"] for lk in p}
        if ids <= covered:
            continue
        chosen.append(p)
        covered |= ids
        if len(chosen) >= limit:
            break
    return chosen


async def build_chains(hours: int, min_confidence: float, limit: int, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(hours=hours)
    cause_ev, effect_ev = aliased(Event), aliased(Event)
    async with get_session_factory()() as session:
        # رابط في الفترة: أثره رُصد خلالها، وطرفاه ما زالا مخزّنين — يُصفّى في
        # SQL فلا تُحمَّل روابط الشهر كله لعرض ثلاثة أيام
        rows = list((await session.execute(
            select(EventLink)
            .join(effect_ev, effect_ev.id == EventLink.effect_id)
            .join(cause_ev, cause_ev.id == EventLink.cause_id)
            .where(and_(
                EventLink.confidence >= min_confidence,
                effect_ev.event_date >= since, effect_ev.event_date <= now,
            ))
            .order_by(EventLink.id.desc())
            .limit(_LINK_CAP + 1)
        )).scalars())
        truncated = len(rows) > _LINK_CAP
        rows = rows[:_LINK_CAP]
        nodes = await _events_by_id(session, [i for lk in rows for i in (lk.cause_id, lk.effect_id)])

    links = [_link(lk) for lk in rows if lk.cause_id in nodes and lk.effect_id in nodes]
    chains = []
    for path in rank_chains(links, limit):
        ids = [path[0]["cause_id"]] + [lk["effect_id"] for lk in path]
        chains.append({
            "length": len(path),
            "confidence": min(lk["confidence"] for lk in path),
            "nodes": [_node(nodes[i]) for i in ids],
            "links": path,
        })
    return {
        "period_hours": hours,
        "generated_at": now.isoformat(),
        "min_confidence": min_confidence,
        "links": len(links),
        "truncated": truncated,
        "chains": chains,
    }
