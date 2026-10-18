"""رصد - نقاط API لسلاسل السبب والأثر (انظر processors/causal).

- `/api/events/{id}/chain`  أسباب قصة الحدث وآثارها المباشرة
- `/api/chains`             أطول السلاسل في الفترة، لكل رابط علاقته وثقته وقاعدته
- `/api/chains/rules`       القوالب وأوزانها ومعاملات المعادلة (لشرحها في الواجهة)

الروابط بين قصص: الطرفان معرّفا قصتين (`cluster_id` = أول خبر فيها)، فكل طرف
حدث حقيقي يفتحه `/api/events/{id}`.

ثقة السلسلة = ثقة **أضعف** روابطها: السلسلة لا تكون أمتن من أضعف حلقة.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import or_, select

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
from ..services.chains import (  # noqa: F401 - الخدمة مصدر المنطق؛ تُعاد هنا للتوافق
    MAX_DEPTH,
    MAX_PATHS,
    _default_min,
    _events_by_id,
    _link,
    _node,
    build_chains,
    rank_chains,
)

router = APIRouter(prefix="/api", tags=["chains"])

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
