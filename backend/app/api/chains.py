"""رصد - نقاط API لسلاسل السبب والأثر (انظر processors/causal).

- `/api/events/{id}/chain`  أسباب قصة الحدث وآثارها المباشرة
- `/api/chains`             أطول السلاسل في الفترة، لكل رابط علاقته وثقته وقاعدته
- `/api/chains/rules`       القوالب وأوزانها ومعاملات المعادلة (لشرحها في الواجهة)

الروابط بين قصص: الطرفان معرّفا قصتين (`cluster_id` = أول خبر فيها)، فكل طرف
حدث حقيقي يفتحه `/api/events/{id}`.

ثقة السلسلة = ثقة **أضعف** روابطها: السلسلة لا تكون أمتن من أضعف حلقة.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import aliased

from .. import cache
from ..config import get_settings
from ..models.database import Event, EventLink, get_session_factory
from ..processors.causal import (
    DEFAULT_MIN_CONFIDENCE,
    ENTITY_FACTOR,
    MAX_CAUSES_PER_EFFECT,
    MIN_GAP,
    TIME_FLOOR,
    WINDOW,
    describe_templates,
)
from ._serializers import serialize_event

router = APIRouter(prefix="/api", tags=["chains"])

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


@router.get("/events/{event_id}/chain")
async def event_chain(
    event_id: int,
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0),
):
    """أسباب قصة الحدث المحتملة (upstream) وآثارها (downstream)، كلٌّ بعلاقته
    وثقته والقاعدة التي أنتجته وأدلّتها."""
    async with get_session_factory()() as session:
        event = await session.get(Event, event_id)
        if event is None:
            raise HTTPException(status_code=404, detail=f"حدث غير موجود: {event_id}")
        story = event.cluster_id or event.id
        links = list((await session.execute(
            select(EventLink)
            .where(
                or_(EventLink.cause_id == story, EventLink.effect_id == story),
                EventLink.confidence >= min_confidence,
            )
            .order_by(EventLink.confidence.desc())
        )).scalars())
        nodes = await _events_by_id(
            session, [lk.cause_id if lk.effect_id == story else lk.effect_id for lk in links],
        )

    causes, effects = [], []
    for lk in links:
        upstream = lk.effect_id == story
        other = nodes.get(lk.cause_id if upstream else lk.effect_id)
        if other is None:          # طرف حُذف بانتهاء مدة الاحتفاظ
            continue
        (causes if upstream else effects).append({**_link(lk), "event": _node(other)})
    return {"event_id": event_id, "story_id": story, "causes": causes, "effects": effects}


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


@router.get("/chains")
async def chains(
    hours: int = Query(default=72, ge=1, le=720),
    min_confidence: float | None = Query(default=None, ge=0.0, le=1.0),
    limit: int = Query(default=10, ge=1, le=50),
):
    """أطول سلاسل «سبب ← أثر» في الفترة، لكل رابط علاقته وثقته وقاعدته.
    `min_confidence` يُسقط الروابط الأضعف قبل بناء السلاسل (الافتراضي حدّ
    التخزين `CAUSAL_MIN_CONFIDENCE`)."""
    threshold = _default_min() if min_confidence is None else min_confidence
    ttl = get_settings().response_cache_seconds
    return await cache.cached(
        ("chains", hours, threshold, limit), ttl, lambda: build_chains(hours, threshold, limit),
    )


@router.get("/chains/rules")
async def chain_rules():
    """القوالب وأوزانها ومعاملات المعادلة — مرجع شرح الروابط في الواجهة."""
    return {
        "rules": describe_templates(),
        "formula": {
            "entity": ENTITY_FACTOR,
            "time_floor": TIME_FLOOR,
            "window_hours": WINDOW.total_seconds() / 3600,
            "min_gap_hours": MIN_GAP.total_seconds() / 3600,
            "max_causes_per_effect": MAX_CAUSES_PER_EFFECT,
            "min_confidence": _default_min(),
            "default_min_confidence": DEFAULT_MIN_CONFIDENCE,
        },
    }
