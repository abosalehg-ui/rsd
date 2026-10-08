"""رصد - عدسة «الأثر على المملكة»: وسم القطاعات ودرجة الأثر لكل حدث.

كل حدث (لا النووي وحده) يمرّ بخطوتين:

1. **وسم القطاعات**: معجم عربي/إنجليزي لثمانية قطاعات (SECTORS) بمطابقة
   حدود الكلمة عبر `matching.KeywordSet`. الحدث قد يحمل أكثر من قطاع، أو لا
   يحمل شيئًا. عبارات ملتبسة («المياه الإقليمية»، "who said") تُخفى قبل
   المطابقة كي لا تُحسب لقطاع لا صلة له.

2. **درجة الأثر (0-100)**:

       الأثر = 100 × الشدة × القرب × الإشارة المباشرة × ثقة المصدر

   أربعة معاملات بين 0 و1، فلا تتجاوز الدرجة 100 ولا يرفعها عامل واحد وحده:
   حدث حرج بعيد بلا إشارة للمملكة يبقى منخفضًا، وخبر عادي عن أرامكو من مصدر
   رسمي لا يبلغ الحرج دون شدة.

   كل معامل يُعاد في `components` ويُخزَّن مع الحدث (extra_data.impact) كي
   تعرض الواجهة المعادلة بأرقامها — الدرجة لا تُعرض رقمًا مجردًا.

الأوزان اجتهاد تشغيلي أولي قابل للمعايرة، لا معيار رسمي. التوثيق الكامل
في docs/ksa-impact-methodology.md.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Mapping

from .gazetteer import ksa_point_en, ksa_proximity
from .matching import KeywordSet, strip_phrases
from .normalize import normalize_for_match
from .nuclear import SOURCE_TRUST


@dataclass(frozen=True)
class Sector:
    key: str
    terms: KeywordSet


# ===== القطاعات =====
# الترتيب يحسم التساوي في «القطاع الأساسي» للحدث.
SECTORS: tuple[Sector, ...] = (
    Sector("security", KeywordSet((
        "attack", "strike", "airstrike*", "missile*", "drone*", "rocket*", "intercept*",
        "air defense", "air defence", "militant*", "terror*", "explosion", "bombing",
        "clashes", "troops", "military", "war", "houthi*", "ballistic", "security forces",
        "border guard*", "infiltrat*",
        "هجوم", "هجمات", "قصف", "غارة", "غارات", "صاروخ", "صواريخ", "مسيرة", "مسيرات",
        "اعتراض", "الدفاع الجوي", "إرهاب", "إرهابي", "انفجار", "اشتباكات", "عسكري",
        "حرب", "الحوثي", "الحوثيين", "باليستي", "تسلل", "حرس الحدود", "القوات المسلحة",
    ))),
    Sector("energy", KeywordSet((
        "oil", "crude", "gas", "lng", "refiner*", "pipeline*", "opec", "barrel*",
        "aramco", "petrochemical*", "power grid", "electricity", "power station",
        "fuel", "oil field*", "gas field*", "energy",
        # منشآت طاقة سعودية بالاسم: ذكرها وحده يكفي للقطاع
        "ras tanura", "abqaiq", "khurais", "shaybah", "ras al khair", "petroline", "sabic",
        "نفط", "النفط", "النفط الخام", "خام برنت", "غاز", "الغاز", "مصفاة", "مصافي", "خط أنابيب", "أنابيب",
        "أوبك", "برميل", "براميل", "أرامكو", "بتروكيماويات", "الشبكة الكهربائية",
        "كهرباء", "محطة كهرباء", "وقود", "حقل نفط", "حقول النفط", "الطاقة",
        "رأس تنورة", "بقيق", "أبقيق", "خريص", "حقل شيبة", "سابك", "مصفاة ينبع",
    ))),
    Sector("aviation", KeywordSet((
        "airport*", "flight*", "airline*", "airspace", "aviation", "notam",
        "passenger plane", "commercial aircraft", "air traffic", "runway",
        "مطار", "مطارات", "رحلات جوية", "رحلة جوية", "الطيران المدني", "شركة طيران",
        "خطوط جوية", "المجال الجوي", "الملاحة الجوية", "طائرة ركاب", "مدرج",
    ))),
    Sector("shipping_ports", KeywordSet((
        "port", "ports", "shipping", "tanker*", "vessel*", "ship", "ships", "maritime",
        "strait", "red sea", "hormuz", "bab el mandeb", "bab al mandab", "suez",
        "container ship*", "freight", "navigation", "seafarer*", "naval blockade",
        "ميناء", "موانئ", "الملاحة", "ناقلة", "ناقلات", "سفينة", "سفن", "بحري",
        "مضيق", "البحر الأحمر", "هرمز", "باب المندب", "قناة السويس", "حاويات", "الشحن",
    ))),
    Sector("markets", KeywordSet((
        "stocks", "stock market*", "stock exchange*", "market*", "shares", "tadawul", "tasi", "currency", "riyal",
        "inflation", "bond*", "investor*", "oil price*", "economy", "economic",
        "gdp", "credit rating", "exchange rate",
        "أسهم", "سوق", "الأسواق", "تداول", "مؤشر السوق", "عملة", "الريال", "تضخم",
        "سندات", "مستثمرين", "أسعار النفط", "اقتصاد", "اقتصادي", "الناتج المحلي",
        "التصنيف الائتماني", "سعر الصرف",
    ))),
    Sector("food_water", KeywordSet((
        "food", "wheat", "grain*", "famine", "water supply", "drinking water",
        "desalination", "drought", "crop*", "agricultur*", "rice", "hunger",
        "food security", "water shortage",
        "غذاء", "الغذاء", "قمح", "القمح", "حبوب", "مجاعة", "مياه الشرب", "تحلية",
        "جفاف", "محاصيل", "زراعة", "زراعي", "أرز", "جوع", "الأمن الغذائي", "شح المياه",
        "إمدادات المياه",
    ))),
    Sector("health", KeywordSet((
        "health", "hospital*", "disease*", "outbreak*", "epidemic*", "pandemic*",
        "virus", "cholera", "vaccin*", "world health organization", "mers",
        "covid", "infection*", "medical",
        "صحة", "الصحة", "صحي", "مستشفى", "مستشفيات", "مرض", "أمراض", "تفشي", "وباء",
        "جائحة", "فيروس", "كوليرا", "لقاح", "منظمة الصحة العالمية", "كورونا", "عدوى",
    ))),
    Sector("diplomacy", KeywordSet((
        "talks", "summit", "negotiat*", "ceasefire", "foreign minister", "ambassador*",
        "embass*", "sanction*", "treaty", "agreement", "diplomat*", "envoy",
        "security council", "united nations", "mediation",
        "مفاوضات", "محادثات", "قمة", "هدنة", "وقف إطلاق النار", "وزير الخارجية",
        "سفير", "سفارة", "عقوبات", "معاهدة", "اتفاق", "اتفاقية", "دبلوماسي", "مبعوث",
        "مجلس الأمن", "الأمم المتحدة", "وساطة",
    ))),
)
SECTOR_KEYS: tuple[str, ...] = tuple(s.key for s in SECTORS)

# عبارات تحوي كلمة قطاع بمعنى آخر — تُخفى قبل وسم القطاعات
_SECTOR_EXCLUDE = KeywordSet((
    "territorial waters", "international waters", "المياه الإقليمية", "المياه الدولية",
    "gas chamber", "tear gas", "الغاز المسيل للدموع", "غاز مسيل للدموع",
    "black market", "السوق السوداء", "port of call",
    "food for thought", "war of words", "حرب كلامية",
    "price war", "حرب الأسعار", "star wars", "hunger strike", "الإضراب عن الطعام",
    # الوكالة الذرية شأن رقابي لا قطاع طاقة
    "atomic energy", "الطاقة الذرية",
    # «صحة» بمعنى الصدق لا القطاع الصحي
    "صحة الخبر", "صحة الأنباء", "صحة التقارير", "صحة المعلومات", "مدى صحة", "عدم صحة",
))


# ===== الإشارة المباشرة =====
# أصول سعودية حيوية: إشارة إليها أقوى من ذكر اسم الدولة. «ينبع» وحدها فعل
# («ينبع من…») فلا تُقبل إلا مقيّدة بسياق، و«المملكة» وحدها ملتبسة (البحرين،
# الأردن، المملكة المتحدة) فلا تُحتسب.
_KSA_ASSETS = KeywordSet((
    "aramco", "saudi aramco", "ras tanura", "abqaiq", "khurais", "yanbu", "jubail",
    "shaybah", "ras al khair", "sabic", "neom", "east west pipeline", "petroline",
    "king khalid international airport", "king abdulaziz international airport",
    "king fahd international airport", "abha airport", "jazan airport", "jizan airport",
    "jeddah islamic port", "king abdulaziz port", "dammam port", "jeddah port",
    "أرامكو", "رأس تنورة", "بقيق", "أبقيق", "خريص", "ميناء ينبع", "مصفاة ينبع",
    "ينبع الصناعية", "الجبيل", "حقل شيبة", "رأس الخير", "سابك", "نيوم",
    "خط أنابيب شرق غرب", "مطار الملك خالد", "مطار الملك عبدالعزيز", "مطار الملك فهد",
    "مطار أبها", "مطار جازان", "ميناء جدة الإسلامي", "ميناء الملك عبدالعزيز",
    "ميناء الدمام", "ميناء جدة",
))
_KSA_NAMES = KeywordSet((
    "saudi", "saudi arabia", "ksa", "riyadh", "jeddah", "dammam", "dhahran", "mecca",
    "makkah", "medina", "jazan", "jizan", "najran", "abha", "tabuk",
    "السعودية", "المملكة العربية السعودية", "سعودي", "الرياض", "جدة", "الدمام",
    "الظهران", "مكة المكرمة", "المدينة المنورة", "جازان", "جيزان", "نجران", "أبها",
    "تبوك",
))
_CHOKEPOINTS = KeywordSet((
    "hormuz", "strait of hormuz", "bab el mandeb", "bab al mandab", "red sea",
    "gulf of aden", "suez canal",
    "هرمز", "مضيق هرمز", "باب المندب", "البحر الأحمر", "خليج عدن", "قناة السويس",
))

# ===== المعاملات =====
SEVERITY_FACTOR = {"critical": 1.0, "high": 0.75, "medium": 0.5, "low": 0.25}
# نطاق القرب (gazetteer.PROXIMITY_BANDS) ← معامل. «بلا موقع» لا يُعامَل كبعيد:
# أغلبه أخبار عامة، لكن غياب الموقع ليس دليل بُعد.
PROXIMITY_FACTOR = {"adjacent": 1.0, "near": 0.8, "regional": 0.55, "far": 0.3, "unknown": 0.45}
MENTION_FACTOR = {"asset": 1.0, "ksa": 0.9, "chokepoint": 0.85, "none": 0.6}
# ثقة مصادر إيران OSINT من تصنيف الخلاصة نفسها (موثوق/متوسط/غير مؤكد)
_CONFIDENCE_TRUST = {"HIGH": 1.0, "MEDIUM": 0.9, "LOW": 0.8}
# مصادر بيانات منظّمة رسمية بلا `source_kind` في extra_data
_OFFICIAL_SOURCES = ("ucdp",)


@dataclass
class ImpactAssessment:
    score: float
    sectors: list[str] = field(default_factory=list)
    sector_hits: dict[str, int] = field(default_factory=dict)
    components: dict = field(default_factory=dict)
    severity: str = "low"
    proximity_band: str = "unknown"
    distance_to_ksa_km: float | None = None
    nearest_ksa_point: str = ""
    mention: str = "none"
    mentioned: list[str] = field(default_factory=list)

    def as_extra(self) -> dict:
        return {
            "score": self.score,
            "sectors": self.sectors,
            "sector_hits": self.sector_hits,
            "components": self.components,
            "severity": self.severity,
            "proximity_band": self.proximity_band,
            "distance_to_ksa_km": self.distance_to_ksa_km,
            "nearest_ksa_point": self.nearest_ksa_point,
            "nearest_ksa_point_en": ksa_point_en(self.nearest_ksa_point) if self.nearest_ksa_point else "",
            "mention": self.mention,
            "mentioned": self.mentioned,
        }


def tag_sectors(title: str, description: str = "") -> dict[str, int]:
    """{القطاع: عدد المقاطع المطابِقة} للقطاعات الحاضرة، الأكثر أولًا.

    كلمات العنوان تُحسب مرتين كما في الرصد النووي: العنوان أدلّ على موضوع
    الخبر من وصفه."""
    norm, _ = strip_phrases(normalize_for_match(f"{title} {description}"), _SECTOR_EXCLUDE)
    title_norm, _ = strip_phrases(normalize_for_match(title), _SECTOR_EXCLUDE)
    hits: dict[str, int] = {}
    for sector in SECTORS:
        if not sector.terms.matches(norm):     # مسح واحد يستبعد أغلب القطاعات
            continue
        n = sector.terms.count(norm) + sector.terms.count(title_norm)
        if n:
            hits[sector.key] = n
    order = {k: i for i, k in enumerate(SECTOR_KEYS)}
    return dict(sorted(hits.items(), key=lambda kv: (-kv[1], order[kv[0]])))


def _strict_terms(terms: KeywordSet, norm: str) -> list[str]:
    """العبارات المطابِقة، مع اشتراط «ال» لأسماء الأماكن المعرّفة.

    `KeywordSet` تجعل «ال» اختيارية، فتطابق «الرياض» الاسمَ «رياض» («رياض
    سلامة») و«الجبيل» مدينةَ «جبيل» اللبنانية. لاسم المكان المعرّف نشترط ظهور
    الأداة («الرياض»، «بالرياض»، «للرياض»)."""
    found: list[str] = []
    if not terms.matches(norm):
        return found
    for hit in terms.search(norm):
        if hit.term in found:
            continue
        term = normalize_for_match(hit.term)
        text = norm[hit.start:hit.end]
        if term.startswith("ال") and "ال" not in text and "لل" not in text:
            continue
        found.append(hit.term)
    return found


def direct_mention(title: str, description: str = "") -> tuple[str, list[str]]:
    """(المستوى، العبارات المطابِقة): asset > ksa > chokepoint > none."""
    norm = normalize_for_match(f"{title} {description}")
    for level, terms in (("asset", _KSA_ASSETS), ("ksa", _KSA_NAMES), ("chokepoint", _CHOKEPOINTS)):
        matched = _strict_terms(terms, norm)
        if matched:
            return level, matched[:6]
    return "none", []


def source_trust(source: str = "", source_kind: str = "", confidence: str = "") -> float:
    """معامل ثقة المصدر — جدول الرصد النووي نفسه (`SOURCE_TRUST`) حين يُعرف نوع
    المصدر، وتصنيف الخلاصة لإيران OSINT، و«إخباري» (0.9) افتراضًا."""
    if source_kind in SOURCE_TRUST:
        return SOURCE_TRUST[source_kind]
    if source in _OFFICIAL_SOURCES:
        return SOURCE_TRUST["official"]
    if source == "iran_osint" and confidence in _CONFIDENCE_TRUST:
        return _CONFIDENCE_TRUST[confidence]
    return SOURCE_TRUST["news"]


def assess_impact(
    title: str,
    description: str = "",
    *,
    severity: str = "low",
    latitude: float | None = None,
    longitude: float | None = None,
    source: str = "",
    source_kind: str = "",
    confidence: str = "",
) -> ImpactAssessment:
    sector_hits = tag_sectors(title, description)
    mention, mentioned = direct_mention(title, description)
    prox = ksa_proximity(latitude, longitude)
    sev = severity if severity in SEVERITY_FACTOR else "low"

    components = {
        "severity": SEVERITY_FACTOR[sev],
        "proximity": PROXIMITY_FACTOR[prox.band],
        "mention": MENTION_FACTOR[mention],
        "source_trust": source_trust(source, source_kind, confidence),
    }
    product = 1.0
    for value in components.values():
        product *= value
    score = max(0.0, min(100.0, round(100 * product, 1)))

    return ImpactAssessment(
        score=score,
        sectors=list(sector_hits),
        sector_hits=sector_hits,
        components=components,
        severity=sev,
        proximity_band=prox.band,
        distance_to_ksa_km=prox.distance_km,
        nearest_ksa_point=prox.nearest_point,
        mention=mention,
        mentioned=mentioned,
    )


def _load_extra(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def impact_fields(fields: Mapping) -> dict:
    """حقول `Event` المشتقّة من الأثر لحدث في صيغة قاموس الإدراج (أو صفّ مخزّن).

    يعيد `ksa_impact` و`impact_sectors` (JSON) و`extra_data` بعد دمج مكوّنات
    الأثر فيها تحت المفتاح `impact`. يُستدعى من `insert_event_if_new` فيغطّي
    كل الجامعين — حتى من يحدّد تصنيفه وموقعه بنفسه (UCDP، إيران OSINT)."""
    extra = _load_extra(fields.get("extra_data"))
    a = assess_impact(
        fields.get("title") or "",
        fields.get("description") or "",
        severity=fields.get("severity") or "low",
        latitude=fields.get("latitude"),
        longitude=fields.get("longitude"),
        source=fields.get("source") or "",
        source_kind=extra.get("source_kind") or "",
        confidence=fields.get("confidence") or "",
    )
    extra["impact"] = a.as_extra()
    return {
        "ksa_impact": a.score,
        "impact_sectors": json.dumps(a.sectors),
        "extra_data": json.dumps(extra, ensure_ascii=False),
    }


def parse_sectors(raw) -> list[str]:
    """قائمة القطاعات من عمود `impact_sectors` (JSON) — [] عند الغياب أو التلف."""
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    return [s for s in parsed if s in SECTOR_KEYS] if isinstance(parsed, list) else []
