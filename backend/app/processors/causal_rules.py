"""رصد - حقائق القصة وشروط قوالب «سبب ← أثر» والقوالب نفسها (انظر processors/causal).

`StoryFacts` ما يحتاجه المحرّك من قصة. كل شرط دالة صغيرة تعيد الأدلة (عبارات
أو حقولًا مطابِقة) أو `None`، والقالب بيانات معلنة: وزن + شرط سبب + شرط أثر.
التقييم والتخزين في `processors/causal`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Sequence

from .causal_entities import extract_entities
from .causal_lexicon import (
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
from .clustering import story_rank, title_tokens
from .dates import as_utc
from .gazetteer import locate
from .impact import direct_mention, parse_sectors, source_trust
from .matching import KeywordSet, strip_phrases
from .normalize import normalize_for_match, parse_extra

# دول الخليج واليمن (ومعها إيران): نطاق قالب «هجوم في الخليج أو اليمن»
GULF_YEMEN = frozenset({"SA", "AE", "QA", "KW", "BH", "OM", "YE", "IR"})


# ===== حقائق القصة =====

@dataclass
class StoryFacts:
    """ما يحتاجه المحرّك من قصة: ممثّلها، وأول رصد لها، وكياناتها، وأقوى ثقة
    مصدر بين أخبارها (مصدر رسمي واحد في القصة يكفي)."""

    id: int
    rep_id: int
    first_seen: datetime
    title: str
    norm_title: str
    tokens: frozenset[str]
    category: str
    topic: str | None
    event_type: str | None
    sectors: tuple[str, ...]
    trust: float
    entities: frozenset[tuple[str, str]]
    _memo: dict = field(default_factory=dict, repr=False, compare=False)

    @property
    def countries(self) -> frozenset[str]:
        return frozenset(k for kind, k in self.entities if kind == "country")

    @property
    def waterways(self) -> frozenset[str]:
        return frozenset(k for kind, k in self.entities if kind == "waterway")

    def terms(self, ks: KeywordSet) -> list[str]:
        """العبارات المطابِقة في العنوان (بعد إخفاء المعاني غير الحركية)."""
        key = id(ks)
        if key not in self._memo:
            self._memo[key] = ks.matched_terms(self.norm_title)
        return self._memo[key]


def build_story_facts(story_id: int, members: Sequence) -> StoryFacts:
    """حقائق قصة من أخبارها (صفوف `Event` أو ما يشبهها بالحقول نفسها)."""
    rep = max(members, key=story_rank)
    dates = [as_utc(m.event_date) for m in members if m.event_date is not None]
    trust = max(
        source_trust(m.source or "", parse_extra(m.extra_data).get("source_kind") or "", m.confidence or "")
        for m in members
    )
    title = rep.title or ""
    norm, _ = strip_phrases(normalize_for_match(title), _NON_KINETIC)
    return StoryFacts(
        id=story_id,
        rep_id=rep.id,
        first_seen=min(dates) if dates else datetime.now(timezone.utc),
        title=title,
        norm_title=norm,
        tokens=title_tokens(title),
        category=rep.category or "general",
        topic=rep.topic,
        event_type=rep.event_type,
        sectors=tuple(parse_sectors(rep.impact_sectors)),
        trust=trust,
        entities=extract_entities(title, rep.facility_id),
    )


# ===== شروط القوالب =====
# كل شرط يعيد قائمة الأدلة (عبارات أو حقول مطابِقة)، أو None إن لم يتحقّق.

Evidence = list[str]
Predicate = Callable[[StoryFacts], "Evidence | None"]


def _both(f: StoryFacts, a: KeywordSet, b: KeywordSet) -> Evidence | None:
    ta, tb = f.terms(a), f.terms(b)
    return ta + tb if ta and tb else None


def is_attack(f: StoryFacts) -> Evidence | None:
    return f.terms(ATTACK) or None


def is_strike(f: StoryFacts) -> Evidence | None:
    hits = f.terms(STRIKE)
    if hits:
        return hits
    return ["event_type:strike"] if f.event_type == "strike" else None


def _price_move(f: StoryFacts, subject: KeywordSet, *directions: KeywordSet) -> Evidence | None:
    """موضوع سعري + حركة في الاتجاه المتوقع (أو تقلّب)، بلا محرّك آخر مُعلن."""
    if f.terms(_OTHER_DRIVERS):
        return None
    for direction in directions + (PRICE_VOLATILE,):
        hits = _both(f, subject, direction)
        if hits:
            return hits
    return None


def gulf_attack(f: StoryFacts) -> Evidence | None:
    hits = is_attack(f)
    if not hits:
        return None
    region = sorted(f.countries & GULF_YEMEN) + sorted(f.waterways)
    return hits + [f"region:{r}" for r in region] if region else None


def energy_shipping_effect(f: StoryFacts) -> Evidence | None:
    if f.terms(_OPEC_POLICY):
        return None
    oil = _price_move(f, OIL_SUBJECT, PRICE_UP)
    if oil:
        return oil
    # عنوان فيه هجوم + اضطراب مادي («هجوم يوقف الملاحة») غالبًا وصفٌ للحادثة
    # نفسها لا أثرٌ لها؛ الحركة السعرية وحدها أثرٌ لا يلتبس بالحادثة
    if is_attack(f):
        return None
    return _both(f, SHIP_SUBJECT, SHIP_DISRUPT) or _both(f, ENERGY_SUBJECT, ENERGY_DISRUPT)


def nuclear_cause(f: StoryFacts) -> Evidence | None:
    return [f"topic:{f.topic}"] if f.topic in NUCLEAR_CAUSE_TOPICS else None


def diplomatic_effect(f: StoryFacts) -> Evidence | None:
    if not f.topic:      # الأثر نفسه يجب أن يكون شأنًا نوويًا (عبَر بوابة الرصد النووي)
        return None
    hits = f.terms(DIPLOMATIC_MOVE)
    if hits:
        return hits
    return ["topic:diplomacy_sanctions"] if f.topic == "diplomacy_sanctions" else None


def retaliation_effect(f: StoryFacts) -> Evidence | None:
    if f.terms(_NON_MILITARY_RESPONSE):
        return None
    self_hits = f.terms(RETALIATION_SELF)
    if self_hits:
        return self_hits
    return _both(f, RETALIATION_MARK, KINETIC)


def launch_effect(f: StoryFacts) -> Evidence | None:
    if f.terms(_NON_MILITARY_LAUNCH):
        return None
    hits = f.terms(LAUNCH)
    if hits:
        return hits
    if f.event_type == "launch" and f.terms(_MISSILE):
        return ["event_type:launch"] + f.terms(_MISSILE)
    return None


def ksa_asset_attack(f: StoryFacts) -> Evidence | None:
    hits = is_attack(f)
    if not hits:
        return None
    if "ksa_target" not in f._memo:
        level, matched = direct_mention(f.title)
        if level == "asset":
            target = [f"asset:{m}" for m in matched]
        elif locate(f.title).country_code == "SA":
            # الهدف في المملكة (يفضّل المعجم الاسم المسبوق بـ«على»، «في»…):
            # «تحالف بقيادة سعودية يقصف صنعاء» ليس هجومًا على أصل سعودي
            target = ["target:SA"]
        else:
            target = [f"near:{t}" for t in f.terms(KSA_NEAR)]
        f._memo["ksa_target"] = target
    target = f._memo["ksa_target"]
    return hits + target if target else None


def aviation_markets_effect(f: StoryFacts) -> Evidence | None:
    ksa = "SA" in f.countries or any(kind == "asset" for kind, _ in f.entities)
    if not ksa:
        return None
    market = _price_move(f, MARKET_SUBJECT, PRICE_DOWN) or _price_move(f, OIL_SUBJECT, PRICE_UP)
    if market:
        return market
    if is_attack(f):     # انظر energy_shipping_effect
        return None
    return _both(f, AVIATION_SUBJECT, AVIATION_DISRUPT)


# ===== القوالب =====

@dataclass(frozen=True)
class Template:
    id: str
    weight: float
    relation_ar: str
    relation_en: str
    cause: Predicate
    effect: Predicate
    # كيان أخصّ من الدولة، أو دولتان مشتركتان على الأقل
    strong_entity: bool = False
    # كيانات مشتركة بحكم شرطي القالب نفسيهما فلا تدلّ على شيء: في قالب «أصل
    # سعودي ← طيران أو أسواق» الطرفان سعوديان دائمًا، فاشتراكهما في «السعودية»
    # لا يربط هجومًا في بقيق بتعليق رحلات في أبها
    uninformative: frozenset[tuple[str, str]] = frozenset()


TEMPLATES: tuple[Template, ...] = (
    Template(
        "gulf_attack_energy_shipping", 0.8,
        "هجوم أو تهديد في الخليج أو اليمن ← اضطراب في الطاقة أو الملاحة",
        "Attack or threat in the Gulf or Yemen → energy or shipping disruption",
        gulf_attack, energy_shipping_effect,
    ),
    Template(
        "nuclear_diplomacy", 0.75,
        "حدث نووي ← تحرّك دبلوماسي أو عقوبات",
        "Nuclear development → diplomatic move or sanctions",
        nuclear_cause, diplomatic_effect,
    ),
    Template(
        "strike_retaliation", 0.85,
        "ضربة ← رد انتقامي",
        "Strike → retaliation",
        is_strike, retaliation_effect,
    ),
    Template(
        "strike_launch", 0.6,
        "ضربة ← إطلاق صواريخ",
        "Strike → missile launch",
        is_strike, launch_effect,
        strong_entity=True,
    ),
    Template(
        "ksa_asset_aviation_markets", 0.85,
        "هجوم على أصل سعودي أو قربه ← أثر على الطيران أو الأسواق",
        "Attack on or near a Saudi asset → aviation or market impact",
        ksa_asset_attack, aviation_markets_effect,
        uninformative=frozenset({("country", "SA")}),
    ),
)
TEMPLATE_BY_ID = {t.id: t for t in TEMPLATES}


def describe_templates() -> list[dict]:
    """القوالب للعرض (الواجهة والتوثيق)."""
    return [
        {"id": t.id, "weight": t.weight, "relation_ar": t.relation_ar, "relation_en": t.relation_en,
         "strong_entity": t.strong_entity}
        for t in TEMPLATES
    ]
