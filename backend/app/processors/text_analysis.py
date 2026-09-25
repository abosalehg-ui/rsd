"""رصد - تحليل النصوص المشترك بين الجامعين.

نقطة دخول واحدة `analyze()` تعيد كل ما يحتاجه الجامع لتخزين حدث: التصنيف،
والخطورة، والموقع بدقته، وتقييم المخاطر النووية/الإشعاعية إن انطبق. الدوال
القديمة (`classify`, `geolocate`, `country_code_from_text`) باقية كواجهات
رقيقة فوقها كي لا يتغيّر توقيع أي جامع.

المطابقة كلها عبر `matching.KeywordSet` (حدود كلمة + سوابق/لواحق عربية)، لا
`kw in text` — راجع توثيق `matching.py` لأمثلة الأخطاء التي كان يُنتجها ذلك.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .gazetteer import (  # noqa: F401 - إعادة تصدير للتوافق الخلفي
    COUNTRY_COORDS,
    ME_COUNTRY_NAMES,
    Location,
    locate,
)
from .gazetteer import country_code_from_text as _country_code
from .matching import KeywordSet
from .normalize import normalize_for_match
from .nuclear import NuclearAssessment, assess

# ===== قوائم كلمات التصنيف العام =====
MILITARY_KW = KeywordSet((
    "attack", "strike", "airstrike", "bomb*", "missile*", "war", "troops", "drone*", "soldier*",
    "combat", "killed", "kill", "casualt*", "shelling", "clashes", "rocket*", "intercept*",
    "هجوم", "قصف", "صاروخ", "صواريخ", "غارة", "غارات", "حرب", "قتل", "قتلى", "طائرة مسيرة",
    "مسيرة", "مسيرات", "عسكري", "اشتباك", "اشتباكات", "اعتراض",
))
DEATH_KW = KeywordSet((
    "killed", "kill", "dead", "deaths", "casualt*", "قتل", "قتلى", "مقتل", "شهداء", "ضحايا",
))
DIPLOMATIC_KW = KeywordSet((
    "ceasefire", "peace", "diplomat*", "negotiat*", "summit", "treaty", "united nations",
    "foreign minister", "talks",
    "هدنة", "سلام", "دبلوماسي", "مفاوضات", "قمة", "وقف إطلاق النار", "اتفاق", "محادثات",
    "وزير الخارجية", "الأمم المتحدة",
))
HUMANITARIAN_KW = KeywordSet((
    "humanitarian", "refugee*", "aid", "civilian*", "displaced", "famine", "relief",
    "إنساني", "لاجئ", "لاجئين", "مساعدات", "نازح", "نازحين", "إغاثة", "مجاعة", "مدنيين",
))
ECONOMIC_KW = KeywordSet((
    "sanctions", "oil price*", "crude", "economic", "economy", "trade", "tariff*", "inflation",
    "عقوبات", "نفط", "أسعار النفط", "اقتصاد", "اقتصادي", "تجارة", "تضخم",
))

CATEGORIES = ("military", "nuclear", "radiological", "diplomatic", "humanitarian", "economic", "general")


@dataclass
class Analysis:
    category: str
    severity: str
    location: Location
    nuclear: NuclearAssessment
    extra: dict = field(default_factory=dict)

    @property
    def is_nuclear(self) -> bool:
        return self.nuclear.relevant


def _classify_general(norm: str, base_category: str, escalate_on_death: bool) -> tuple[str, str]:
    if MILITARY_KW.matches(norm):
        sev = "critical" if (escalate_on_death and DEATH_KW.matches(norm)) else "high"
        return "military", sev
    if DIPLOMATIC_KW.matches(norm):
        return "diplomatic", "medium"
    if HUMANITARIAN_KW.matches(norm):
        return "humanitarian", "medium"
    if ECONOMIC_KW.matches(norm):
        return "economic", "low"
    return base_category, ("medium" if base_category != "general" else "low")


def analyze(
    title: str,
    description: str = "",
    *,
    base_category: str = "general",
    source_kind: str = "news",
    escalate_on_death: bool = True,
) -> Analysis:
    """تحليل كامل لخبر. `base_category="nuclear"` يعني مصدرًا نوويًا متخصصًا
    (كل منشوراته نووية) فيُقيَّم نوويًا حتى لو لم تظهر كلمة «نووي»."""
    location = locate(title, description)
    nuclear = assess(
        title, description, location,
        source_kind=source_kind,
        force=base_category in ("nuclear", "radiological"),
    )

    if nuclear.relevant:
        category, severity = nuclear.category, nuclear.severity
    else:
        norm = normalize_for_match(f"{title} {description}")
        category, severity = _classify_general(norm, base_category, escalate_on_death)

    extra = {"geo_precision": location.precision}
    if location.place_name:
        extra["place_name"] = location.place_name
    if nuclear.relevant:
        extra["nuclear"] = {
            "topic": nuclear.topic,
            "risk_score": nuclear.risk_score,
            "components": nuclear.components,
            "facility_ids": nuclear.facility_ids,
            "distance_to_ksa_km": nuclear.distance_to_ksa_km,
            "nearest_ksa_point": nuclear.nearest_ksa_point,
            "reassuring": nuclear.reassuring,
            "matched": nuclear.matched,
        }
    return Analysis(category=category, severity=severity, location=location, nuclear=nuclear, extra=extra)


def event_fields(analysis: Analysis) -> dict:
    """حقول نموذج `Event` المشتقّة من التحليل — تُفكّ مباشرة في `insert_event_if_new`."""
    loc = analysis.location
    nuc = analysis.nuclear
    return {
        "category": analysis.category,
        "severity": analysis.severity,
        "latitude": loc.lat,
        "longitude": loc.lon,
        "country": loc.country_name,
        "country_code": loc.country_code,
        "topic": nuc.topic if nuc.relevant else None,
        "risk_score": nuc.risk_score if nuc.relevant else None,
        "facility_id": (nuc.facility_ids[0] if nuc.facility_ids else loc.facility_id) or None,
        "geo_precision": loc.precision,
    }


# ===== واجهات التوافق الخلفي =====

def classify(
    title: str,
    description: str = "",
    base_category: str = "general",
    escalate_on_death: bool = True,
) -> tuple[str, str]:
    """(category, severity) — كما كانت، مع دعم التصنيف النووي/الإشعاعي."""
    a = analyze(title, description, base_category=base_category, escalate_on_death=escalate_on_death)
    return a.category, a.severity


def country_code_from_text(text: str) -> str:
    return _country_code(text)


def geolocate(title: str, description: str = "") -> tuple[str, str, float | None, float | None]:
    """(code, name_ar, lat, lon) — أدق موقع متاح، أو ("", "", None, None)."""
    loc = locate(title, description)
    return loc.country_code, loc.country_name, loc.lat, loc.lon
