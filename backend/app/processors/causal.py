"""رصد - سلاسل السبب والأثر بين القصص (محرّك قاعدي قابل للتفسير).

`processors/clustering` يجمع الخبر **نفسه** من عدة مصادر في «قصة». هنا نربط
قصصًا **مختلفة** برابط «سبب ← أثر» محتمل، بقوالب علاقات صريحة (`TEMPLATES`)،
لا بنموذج لغوي. الرابط بين ممثّلي القصص (`cluster_id`) لا بين الأخبار الخام،
فلا يتكرّر الرابط لكل مصدر.

شروط أي رابط — كلها لازمة:

1. **القالب**: القصة الأولى تحقّق شرط «السبب» والثانية شرط «الأثر». قصة تحقّق
   شرط الأثر لا تُقبل سببًا في القالب نفسه (يُستبعد وصف الحادثة الواحدة مرتين).
2. **الترتيب الزمني**: أول رصد للأثر بعد أول رصد للسبب بساعة على الأقل
   (`MIN_GAP`) و72 ساعة على الأكثر (`WINDOW`).
3. **كيان مشترك**: دولة، أو مدينة، أو منشأة نووية، أو ممر مائي، أو قائد، أو
   أصل سعودي — مذكور في عنواني القصتين.
4. **ليستا الحادثة نفسها**: عنوانان متقاربان جدًا (كلمات مشتركة كثيرة دون
   عتبة التجميع) يُستبعدان.
5. **الثقة** فوق الحد الأدنى (0.4 افتراضًا، `CAUSAL_MIN_CONFIDENCE`):

       الثقة = قوة التطابق × ثقة المصدر
       قوة التطابق = وزن القالب × معامل الكيان المشترك × معامل الزمن
       ثقة المصدر = أضعف الطرفين (min)

ثم يُبقى لكل أثر أقوى سببين فقط (`MAX_CAUSES_PER_EFFECT`): أثرٌ يصلح لعشرة
أسباب لا يدلّ على أيّها.

**الدقة قبل الشمول**: الرابط الخاطئ يضلّل أكثر من غيابه. لذلك تُطابَق معاجم
الحدث على **العنوان وحده** (الوصف يذكر خلفيات وأحداثًا سابقة)، والكيانات من
العنوان ومعرّف المنشأة وحدهما، ومعاجم الأثر **عبارات عاقبة** («تعليق الرحلات»،
«ارتفاع أسعار النفط») لا أسماء قطاعات («مطار»، «ناقلة»).

كل رابط يحمل `evidence`: الكيانات المشتركة والفارق الزمني ومكوّنات المعادلة
والعبارات المطابِقة — تعرضها الواجهة كما تعرض معادلة الدرجة النووية.

الأوزان اجتهاد تشغيلي أولي قابل للمعايرة. المنهجية وحالات الفشل المعروفة:
docs/causal-links-methodology.md.
"""
from __future__ import annotations

import json
import logging
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Callable, Iterable, Sequence

from sqlalchemy import select

from .causal_entities import (  # noqa: F401 - تُعاد تصديرها للاختبارات والتوثيق
    _entity_labels,
    _entity_matchers,
    _leader_table,
    entity_label,
    extract_entities,
)
from .causal_lexicon import (  # noqa: F401 - المعاجم تُعاد تصديرها للاختبارات
    _MISSILE,
    _NON_KINETIC,
    _NON_MILITARY_LAUNCH,
    _NON_MILITARY_RESPONSE,
    _OPEC_POLICY,
    _OTHER_DRIVERS,
    ATTACK,
    AVIATION_DISRUPT,
    AVIATION_SUBJECT,
    DIPLOMATIC_MOVE,
    ENERGY_DISRUPT,
    ENERGY_SUBJECT,
    KINETIC,
    KSA_NEAR,
    LAUNCH,
    MARKET_SUBJECT,
    NUCLEAR_CAUSE_TOPICS,
    OIL_SUBJECT,
    PRICE_DOWN,
    PRICE_UP,
    PRICE_VOLATILE,
    RETALIATION_MARK,
    RETALIATION_SELF,
    SHIP_DISRUPT,
    SHIP_SUBJECT,
    STRIKE,
)
from .causal_rules import (  # noqa: F401 - تُعاد تصديرها للاختبارات والمسارات
    GULF_YEMEN,
    TEMPLATE_BY_ID,
    TEMPLATES,
    Evidence,
    Predicate,
    StoryFacts,
    Template,
    aviation_markets_effect,
    build_story_facts,
    describe_templates,
    diplomatic_effect,
    energy_shipping_effect,
    gulf_attack,
    is_attack,
    is_strike,
    ksa_asset_attack,
    launch_effect,
    nuclear_cause,
    retaliation_effect,
)
from .clustering import WINDOW as CLUSTER_WINDOW
from .clustering import story_rank
from .matching import KeywordSet

logger = logging.getLogger("rasad.causal")

METHOD_RULE = "rule"
WINDOW = timedelta(hours=72)
MIN_GAP = timedelta(hours=1)
FULL_TIME_HOURS = 24.0       # معامل الزمن 1.0 حتى هنا…
TIME_FLOOR = 0.75            # …ثم يتناقص خطيًا إلى هذا عند نهاية النافذة
DEFAULT_MIN_CONFIDENCE = 0.4
MAX_CAUSES_PER_EFFECT = 2
# «الحادثة نفسها»: أرخى قليلًا من عتبة التجميع (0.6) — ما فاته التجميع لفارق
# صياغة أو لأنه خارج نافذته يُلتقط هنا بدل أن يصير «سببًا» لنفسه
DUP_MIN_SHARED = 3
DUP_MIN_OVERLAP = 0.5

# معامل الكيان المشترك: الأخصّ أقوى. دولة واحدة مشتركة أضعف الأدلة.
ENTITY_FACTOR = {
    "facility": 1.0, "asset": 1.0, "waterway": 0.95, "leader": 0.95, "place": 0.9, "country": 0.8,
}
EXTRA_ENTITY_BONUS = 0.05    # لكل كيان مشترك إضافي، بسقف 1.0

# ===== التقييم =====

@dataclass(frozen=True)
class LinkCandidate:
    cause_id: int
    effect_id: int
    rule_id: str
    relation_ar: str
    relation_en: str
    confidence: float
    evidence: dict
    method: str = METHOD_RULE


def entity_factor(shared: Iterable[tuple[str, str]]) -> float:
    kinds = [kind for kind, _ in shared]
    if not kinds:
        return 0.0
    best = max(ENTITY_FACTOR[k] for k in kinds)
    return round(min(1.0, best + EXTRA_ENTITY_BONUS * (len(kinds) - 1)), 3)


def time_factor(hours: float) -> float:
    if hours <= FULL_TIME_HOURS:
        return 1.0
    span = WINDOW.total_seconds() / 3600 - FULL_TIME_HOURS
    return round(1.0 - (1.0 - TIME_FLOOR) * min(1.0, (hours - FULL_TIME_HOURS) / span), 3)


@lru_cache(maxsize=512)
def _single_term(term: str) -> KeywordSet:
    return KeywordSet((term,))


def _cause_has(cause: StoryFacts, evidence: str) -> bool:
    """هل يحمل عنوان السبب (أو حقوله) دليل الأثر نفسه؟"""
    kind, _, value = evidence.partition(":")
    if kind == "topic" and value:
        return cause.topic == value
    if kind == "event_type" and value:
        return cause.event_type == value
    return _single_term(evidence).matches(cause.norm_title)


def same_incident(cause: StoryFacts, effect: StoryFacts, effect_hits: Sequence[str] = ()) -> bool:
    """عنوانان متقاربان جدًا، والأثر لا يضيف عبارة عاقبة غائبة عن السبب —
    فهما وصفان للحادثة نفسها فاتا التجميع (صياغة أخرى، أو خارج نافذته).

    التقارب وحده لا يكفي: «إسرائيل تضرب إيران» و«إيران ترد بضربات انتقامية على
    إسرائيل» تشتركان في ثلاث كلمات من أربع، والثانية تضيف «انتقامية»."""
    shared = len(cause.tokens & effect.tokens)
    if not shared:
        return False
    close = (shared >= DUP_MIN_SHARED
             and shared / min(len(cause.tokens), len(effect.tokens)) >= DUP_MIN_OVERLAP)
    return close and all(_cause_has(cause, ev) for ev in effect_hits)


def _shared_label(kind: str, key: str) -> dict:
    ar, en = entity_label(kind, key)
    return {"kind": kind, "key": key, "ar": ar, "en": en}


_KIND_ORDER = list(ENTITY_FACTOR)


def evaluate_pair(tpl: Template, cause: StoryFacts, effect: StoryFacts) -> tuple[LinkCandidate | None, str]:
    """(المرشّح، "ok") أو (None، سبب الرفض) — السبب للاختبارات والتشخيص."""
    if cause.id == effect.id:
        return None, "same_story"
    cause_hits = tpl.cause(cause)
    if not cause_hits:
        return None, "cause"
    effect_hits = tpl.effect(effect)
    if not effect_hits:
        return None, "effect"
    if tpl.effect(cause):
        return None, "cause_is_effect"
    gap = effect.first_seen - cause.first_seen
    if gap < MIN_GAP:
        return None, "order"
    if gap > WINDOW:
        return None, "window"
    shared = (cause.entities & effect.entities) - tpl.uninformative
    if not shared:
        return None, "entity"
    countries = [k for kind, k in shared if kind == "country"]
    if tpl.strong_entity and len(countries) == len(shared) and len(countries) < 2:
        return None, "entity_strength"
    if same_incident(cause, effect, effect_hits):
        return None, "same_incident"

    hours = gap.total_seconds() / 3600
    ef = entity_factor(shared)
    tf = time_factor(hours)
    match = round(tpl.weight * ef * tf, 3)
    trust = min(cause.trust, effect.trust)
    confidence = round(match * trust, 2)
    ordered = sorted(shared, key=lambda s: (_KIND_ORDER.index(s[0]), s[1]))
    evidence = {
        "shared": [_shared_label(kind, key) for kind, key in ordered],
        "hours": round(hours, 1),
        "components": {
            "template": tpl.weight, "entity": ef, "time": tf, "match": match,
            "source_trust": trust, "cause_trust": cause.trust, "effect_trust": effect.trust,
        },
        "cause_terms": cause_hits[:6],
        "effect_terms": effect_hits[:6],
    }
    return LinkCandidate(
        cause_id=cause.id, effect_id=effect.id, rule_id=tpl.id,
        relation_ar=tpl.relation_ar, relation_en=tpl.relation_en,
        confidence=confidence, evidence=evidence,
    ), "ok"


# نقطة توسعة لخطوة اختيارية لاحقة (مثل نموذج لغوي يصنّف الأزواج المرشّحة
# ويصوغ العلاقة، بوسم method="llm"). لا تُنفَّذ في هذا الإصدار: المشغّل في
# `analysis.run_causal_linking` يمرّر قائمة فارغة دائمًا.
Refiner = Callable[[list[LinkCandidate]], list[LinkCandidate]]


def propose_links(
    stories: Sequence[StoryFacts],
    *,
    effect_ids: Iterable[int] | None = None,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    max_causes: int = MAX_CAUSES_PER_EFFECT,
    refiners: Sequence[Refiner] = (),
) -> list[LinkCandidate]:
    """كل الروابط المقبولة بين `stories`، لأثرٍ ضمن `effect_ids` (الكل إن غاب).

    زوج تطابقه عدة قوالب يُحفظ بأعلاها ثقة (رابط واحد لكل زوج)، ثم يُبقى لكل
    أثر أقوى `max_causes` أسباب."""
    scope = None if effect_ids is None else set(effect_ids)
    ordered = sorted(stories, key=lambda s: s.first_seen)
    best: dict[tuple[int, int], LinkCandidate] = {}
    for tpl in TEMPLATES:
        causes = [s for s in ordered if tpl.cause(s)]
        times = [s.first_seen for s in causes]
        for effect in ordered:
            if scope is not None and effect.id not in scope:
                continue
            if not tpl.effect(effect):
                continue
            lo = bisect_left(times, effect.first_seen - WINDOW)
            hi = bisect_right(times, effect.first_seen - MIN_GAP)
            for cause in causes[lo:hi]:
                cand, _ = evaluate_pair(tpl, cause, effect)
                if cand is None:
                    continue
                key = (cand.cause_id, cand.effect_id)
                if key not in best or cand.confidence > best[key].confidence:
                    best[key] = cand

    candidates = list(best.values())
    for refine in refiners:
        candidates = refine(candidates)

    per_effect: dict[int, list[LinkCandidate]] = {}
    for c in candidates:
        if c.confidence >= min_confidence:
            per_effect.setdefault(c.effect_id, []).append(c)
    out: list[LinkCandidate] = []
    for effect_id in sorted(per_effect):
        ranked = sorted(per_effect[effect_id], key=lambda c: (-c.confidence, c.cause_id))
        out.extend(ranked[:max_causes])
    return out


# ===== التشغيل على قاعدة البيانات =====

# حقائق القصص محسوبة سابقًا: لا يُعاد تحليل قصة لم يتغيّر ممثّلها ولا عدد
# أخبارها، فيكلّف التشغيل الدوري القصص الجديدة وحدها.
_FACTS_CACHE: dict[int, tuple[tuple, StoryFacts]] = {}

_COLUMNS = (
    "id", "cluster_id", "title", "event_date", "risk_score", "severity", "category", "topic",
    "event_type", "facility_id", "source", "confidence", "extra_data", "impact_sectors",
)


async def load_story_facts(session, since: datetime, until: datetime) -> list[StoryFacts]:
    """حقائق القصص المجمّعة التي فيها خبر بتاريخ بين `since` و`until`."""
    from ..models.database import Event

    cols = [getattr(Event, c) for c in _COLUMNS]
    rows = (await session.execute(
        select(*cols).where(
            Event.cluster_id.isnot(None), Event.event_date >= since, Event.event_date <= until,
        )
    )).all()
    groups: dict[int, list] = {}
    for r in rows:
        groups.setdefault(r.cluster_id, []).append(r)

    facts: list[StoryFacts] = []
    for sid, members in groups.items():
        sig = (max(members, key=story_rank).id, len(members), max(m.id for m in members))
        cached = _FACTS_CACHE.get(sid)
        if cached and cached[0] == sig:
            facts.append(cached[1])
            continue
        f = build_story_facts(sid, members)
        _FACTS_CACHE[sid] = (sig, f)
        facts.append(f)
    live = set(groups)
    for sid in [k for k in _FACTS_CACHE if k not in live]:
        del _FACTS_CACHE[sid]
    return facts


async def link_story_chains(
    session, now: datetime, *, hours: int = 72, min_confidence: float = DEFAULT_MIN_CONFIDENCE,
) -> dict:
    """يعيد حساب روابط الآثار التي رُصدت خلال آخر `hours` ساعة ويخزّنها.

    تزايدي: الآثار الأقدم لا تُمسّ (روابطها تبقى حتى يحذفها التنظيف). لكل أثر
    في النطاق يُستبدل طقم روابطه القاعدية كاملًا، فتشغيله مرتين متتاليتين لا
    يغيّر شيئًا. الروابط بطريقة غير `rule` لا تُمسّ.
    """
    from ..models.database import EventLink

    horizon = now - timedelta(hours=hours)
    # أسباب الآثار حتى 72 ساعة قبلها، وأخبار قصصها حتى نافذة التجميع قبلها
    stories = await load_story_facts(session, horizon - WINDOW - CLUSTER_WINDOW, now)
    scope = [s.id for s in stories if s.first_seen >= horizon]
    desired = {
        (c.cause_id, c.effect_id): c
        for c in propose_links(stories, effect_ids=scope, min_confidence=min_confidence)
    }

    existing: dict[tuple[int, int], EventLink] = {}
    for i in range(0, len(scope), 500):
        chunk = scope[i:i + 500]
        for link in (await session.execute(
            select(EventLink).where(EventLink.effect_id.in_(chunk))
        )).scalars():
            existing[(link.cause_id, link.effect_id)] = link

    created = updated = removed = 0
    for key, link in existing.items():
        if link.method != METHOD_RULE:
            continue
        cand = desired.get(key)
        if cand is None:
            await session.delete(link)
            removed += 1
            continue
        evidence = json.dumps(cand.evidence, ensure_ascii=False, sort_keys=True)
        if (link.confidence, link.rule_id, link.evidence) != (cand.confidence, cand.rule_id, evidence):
            link.confidence = cand.confidence
            link.rule_id = cand.rule_id
            link.relation_ar = cand.relation_ar
            link.relation_en = cand.relation_en
            link.evidence = evidence
            updated += 1
    for key, cand in desired.items():
        if key in existing:
            continue
        session.add(EventLink(
            cause_id=cand.cause_id, effect_id=cand.effect_id,
            relation_ar=cand.relation_ar, relation_en=cand.relation_en,
            confidence=cand.confidence, method=cand.method, rule_id=cand.rule_id,
            evidence=json.dumps(cand.evidence, ensure_ascii=False, sort_keys=True),
            created_at=now,
        ))
        created += 1
    if created or updated or removed:
        await session.commit()
        logger.info("🔗 سلاسل الترابط: %s جديد، %s محدَّث، %s محذوف", created, updated, removed)
    return {"stories": len(stories), "scope": len(scope), "created": created,
            "updated": updated, "removed": removed}
