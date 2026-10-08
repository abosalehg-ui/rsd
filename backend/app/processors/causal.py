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
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Callable, Iterable, Sequence

from sqlalchemy import select

from ..static_data import iranian_leaders
from .clustering import WINDOW as CLUSTER_WINDOW
from .clustering import story_rank, title_tokens
from .gazetteer import COUNTRY_BY_CODE, PLACE_BY_KEY, facility_names, locate, mentions
from .impact import direct_mention, parse_sectors, source_trust
from .matching import KeywordSet, strip_phrases
from .normalize import normalize_for_match

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

GULF_YEMEN = frozenset({"SA", "AE", "QA", "KW", "BH", "OM", "YE", "IR"})


# ===== الكيانات خارج المعجم الجغرافي =====

def _leader_table() -> tuple[tuple[str, str, str, tuple[str, ...]], ...]:
    """(المفتاح، الاسم العربي، الإنجليزي، الأسماء) — القادة الإيرانيون من
    `data/iranian_leaders.json` (مصدر واحد مع لوحة إيران) + قادة إقليميون."""
    rows = [
        (f"ir{leader['id']}", leader["name"], leader["name_en"], tuple(leader["keywords"]))
        for leader in iranian_leaders()
    ]
    rows += [
        ("netanyahu", "نتنياهو", "Netanyahu", ("netanyahu", "نتنياهو")),
        ("trump", "ترامب", "Trump", ("trump", "ترامب", "ترمب")),
        ("mbs", "محمد بن سلمان", "Mohammed bin Salman",
         ("mohammed bin salman", "mohammad bin salman", "محمد بن سلمان", "ولي العهد السعودي")),
        ("grossi", "غروسي", "Grossi", ("grossi", "غروسي")),
        ("abdulmalik_houthi", "عبدالملك الحوثي", "Abdul-Malik al-Houthi",
         ("abdul malik al houthi", "abdulmalik al houthi", "عبدالملك الحوثي", "عبد الملك الحوثي")),
        ("naim_qassem", "نعيم قاسم", "Naim Qassem", ("naim qassem", "نعيم قاسم")),
        ("erdogan", "أردوغان", "Erdogan", ("erdogan", "أردوغان")),
    ]
    return tuple(rows)


# أصول سعودية بالاسم بمفتاح واحد للغتين («أرامكو» و"Aramco" كيان واحد).
# المدن والموانئ المعروفة في المعجم الجغرافي (بقيق، رأس تنورة، الجبيل، ينبع)
# تأتي من هناك نوعَ «مدينة».
_KSA_ASSETS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("aramco", "أرامكو", "Aramco", ("aramco", "saudi aramco", "أرامكو")),
    ("sabic", "سابك", "SABIC", ("sabic", "سابك")),
    ("east_west_pipeline", "خط أنابيب شرق-غرب", "East-West Pipeline",
     ("east west pipeline", "petroline", "خط أنابيب شرق غرب")),
    ("khurais", "خريص", "Khurais", ("khurais", "خريص")),
    ("shaybah", "حقل شيبة", "Shaybah", ("shaybah", "حقل شيبة")),
    ("ras_al_khair", "رأس الخير", "Ras Al-Khair", ("ras al khair", "رأس الخير")),
    ("king_khalid_airport", "مطار الملك خالد", "King Khalid Airport",
     ("king khalid international airport", "king khalid airport", "riyadh airport", "مطار الملك خالد",
      "مطار الرياض")),
    ("king_abdulaziz_airport", "مطار الملك عبدالعزيز", "King Abdulaziz Airport",
     ("king abdulaziz international airport", "king abdulaziz airport", "jeddah airport",
      "مطار الملك عبدالعزيز", "مطار الملك عبد العزيز", "مطار جدة")),
    ("king_fahd_airport", "مطار الملك فهد", "King Fahd Airport",
     ("king fahd international airport", "king fahd airport", "dammam airport", "مطار الملك فهد",
      "مطار الدمام")),
    ("abha_airport", "مطار أبها", "Abha Airport", ("abha airport", "abha international airport", "مطار أبها")),
    ("jazan_airport", "مطار جازان", "Jazan Airport",
     ("jazan airport", "jizan airport", "مطار جازان", "مطار جيزان")),
    ("jeddah_port", "ميناء جدة الإسلامي", "Jeddah Islamic Port",
     ("jeddah islamic port", "jeddah port", "ميناء جدة الإسلامي", "ميناء جدة")),
    ("dammam_port", "ميناء الملك عبدالعزيز", "King Abdulaziz Port",
     ("king abdulaziz port", "dammam port", "ميناء الملك عبدالعزيز", "ميناء الملك عبد العزيز", "ميناء الدمام")),
)

# ممرات خارج المعجم الجغرافي (المعجم يعرف هرمز والخليج وبحر عُمان والبحر
# الأحمر وباب المندب)
_EXTRA_WATERWAYS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("gulf_of_aden", "خليج عدن", "Gulf of Aden", ("gulf of aden", "خليج عدن")),
)


@lru_cache(maxsize=1)
def _entity_matchers() -> dict[str, list[tuple[str, KeywordSet]]]:
    return {
        "leader": [(key, KeywordSet(names)) for key, _, _, names in _leader_table()],
        "asset": [(key, KeywordSet(names)) for key, _, _, names in _KSA_ASSETS],
        "waterway": [(key, KeywordSet(names)) for key, _, _, names in _EXTRA_WATERWAYS],
    }


@lru_cache(maxsize=1)
def _entity_labels() -> dict[tuple[str, str], tuple[str, str]]:
    labels: dict[tuple[str, str], tuple[str, str]] = {}
    for kind, table in (("leader", _leader_table()), ("asset", _KSA_ASSETS), ("waterway", _EXTRA_WATERWAYS)):
        for key, ar, en, _ in table:
            labels[(kind, key)] = (ar, en)
    return labels


def entity_label(kind: str, key: str) -> tuple[str, str]:
    """(الاسم العربي، الإنجليزي) لكيان — للعرض في الواجهة والتوثيق."""
    if kind == "country" and key in COUNTRY_BY_CODE:
        c = COUNTRY_BY_CODE[key]
        return c.name_ar, c.name_en
    if kind in ("place", "waterway") and key in PLACE_BY_KEY:
        p = PLACE_BY_KEY[key]
        return p.name_ar, p.name_en
    if kind == "facility":
        return facility_names(key)
    return _entity_labels().get((kind, key), (key, key))


def extract_entities(title: str, facility_id: str | None = None) -> frozenset[tuple[str, str]]:
    """الكيانات المذكورة في العنوان: {(النوع، المفتاح)}. الوصف لا يُقرأ عمدًا
    (انظر توثيق الوحدة)؛ `facility_id` من التحليل يُضاف لأنه اسم منشأة صريح."""
    m = mentions(title)
    out: set[tuple[str, str]] = {("country", c) for c in m.countries}
    out |= {("place", p) for p in m.places}
    out |= {("waterway", w) for w in m.waterways}
    out |= {("facility", f) for f in m.facilities}
    if facility_id:
        out.add(("facility", facility_id))
    norm = normalize_for_match(title)
    for kind, matchers in _entity_matchers().items():
        for key, ks in matchers:
            if ks.matches(norm):
                out.add((kind, key))
    return frozenset(out)


# ===== المعاجم (تُطابَق على العنوان) =====

# عبارات تحوي كلمة حدث بمعنى آخر — تُخفى قبل المطابقة
_NON_KINETIC = KeywordSet((
    "hunger strike", "general strike", "labor strike", "labour strike", "workers strike", "on strike",
    "strike action", "strikes deal", "strike deal", "strike a deal", "strikes a deal", "strikes agreement",
    "strike an agreement", "heart attack", "panic attack", "attack ad", "attack ads", "lucky strike",
    "الإضراب عن الطعام", "إضراب عام", "نوبة قلبية",
))

STRIKE = KeywordSet((
    "strike", "strikes", "struck", "airstrike*", "air raid*", "bombing", "bombed", "bombard*",
    "attack", "attacks", "attacked", "assassinat*",
    "ضربة", "ضربات", "غارة", "غارات", "قصف", "هجوم", "هجمات", "اغتيال", "استهداف", "استهدف", "استهدفت",
    # المطابِق لا يقبل سوابق المضارعة (ي، ت) عمدًا، فتُكتب صيغ الفعل صراحة
    "تقصف", "يقصف", "قصفت", "تضرب", "يضرب", "ضربت", "تستهدف", "يستهدف", "تهاجم", "يهاجم", "هاجم", "هاجمت",
))
ATTACK = KeywordSet(STRIKE.terms + (
    "drone attack*", "drone strike*", "missile*", "rocket*", "explosion*", "blast", "threat", "threats",
    "threaten*", "seize", "seizes", "seized", "seizure", "hijack*", "naval mine*", "sea mine*",
    "limpet mine*", "sabotage*",
    "صاروخ", "صواريخ", "طائرة مسيرة", "طائرات مسيرة", "مسيرة مفخخة", "مسيرات مفخخة", "زورق مفخخ",
    "انفجار", "تفجير", "تهديد", "تهديدات", "يهدد", "تهدد", "هدد", "هددت", "احتجاز", "احتجزت",
    "احتجز", "استيلاء", "اختطاف", "لغم بحري", "ألغام بحرية", "تخريب",
))
KINETIC = KeywordSet(STRIKE.terms + (
    "missile*", "rocket*", "drone*", "صاروخ", "صواريخ", "طائرة مسيرة", "طائرات مسيرة", "مسيرات",
))
# رد يحمل فعله في العبارة نفسها
RETALIATION_SELF = KeywordSet((
    "retaliatory strike*", "retaliatory attack*", "retaliatory fire", "retaliatory raid*",
    "ضربة انتقامية", "ضربات انتقامية", "هجوم انتقامي", "هجمات انتقامية", "رد عسكري",
))
# علامة رد تحتاج فعلًا حركيًا معها في العنوان
RETALIATION_MARK = KeywordSet((
    "in retaliation", "retaliat*", "in response to", "revenge", "avenge*",
    "ردا على", "انتقاما", "انتقام", "ثأرا", "الثأر",
))
# «رد» تجاري أو دبلوماسي ليس ردًا عسكريًا
_NON_MILITARY_RESPONSE = KeywordSet((
    "tariff*", "sanction*", "trade", "جمركية", "جمركي", "عقوبات",
))
LAUNCH = KeywordSet((
    "missile launch*", "rocket launch*", "launches missiles", "launched missiles", "launch missiles",
    "launches rockets", "launched rockets", "launch rockets", "fires missiles", "fired missiles",
    "fires ballistic missiles", "fired ballistic missiles",
    "fires rockets", "fired rockets", "rocket fire", "missile barrage", "rocket barrage", "salvo", "salvos",
    "ballistic missile*",
    "إطلاق صواريخ", "أطلق صواريخ", "أطلقت صواريخ", "إطلاق صاروخ", "أطلق صاروخا", "أطلقت صاروخا",
    "رشقة صاروخية", "رشقات صاروخية", "وابل من الصواريخ", "صواريخ باليستية", "صاروخ باليستي",
    "تطلق صواريخ", "يطلق صواريخ", "تطلق صاروخا", "يطلق صاروخا",
))
_MISSILE = KeywordSet(("missile*", "rocket*", "صاروخ", "صواريخ"))
_NON_MILITARY_LAUNCH = KeywordSet((
    "satellite launch*", "space launch*", "إطلاق قمر", "إطلاق سراح",
))

# الحركة السعرية: يلزم موضوع سعري + فعل حركة في العنوان نفسه
OIL_SUBJECT = KeywordSet((
    "oil price*", "oil", "crude", "brent", "wti", "oil futures", "gas price*", "lng price*",
    "أسعار النفط", "النفط", "نفط", "برنت", "الخام", "أسعار الغاز",
))
MARKET_SUBJECT = KeywordSet((
    "stock*", "shares", "equit*", "tadawul", "tasi", "bourse", "riyal", "stock market*",
    "الأسهم", "أسهم", "سوق الأسهم", "البورصة", "مؤشر تداول", "سوق تداول", "تاسي", "السوق السعودية",
    "السوق المالية", "مؤشر السوق", "الريال",
))
# اتجاه الحركة مهم: هجوم يرفع النفط ويخفض الأسهم، فـ«الأسهم ترتفع» بعد هجوم
# ليست أثرًا له
PRICE_UP = KeywordSet((
    "jump*", "surge*", "soar*", "spike*", "rise", "rises", "rose", "rising", "climb*", "rall*",
    "ترتفع", "يرتفع", "ارتفاع", "ارتفعت", "ارتفع", "قفزة", "تقفز", "يقفز", "قفزت", "قفز", "صعود",
))
PRICE_DOWN = KeywordSet((
    "fall", "falls", "fell", "falling", "drop*", "slump*", "plunge*", "tumble*", "slide", "slides", "slid",
    "sink*", "sank", "losses",
    "تراجع", "تتراجع", "يتراجع", "تراجعت", "هبوط", "تهبط", "يهبط", "هبطت", "انخفاض", "تنخفض", "ينخفض",
    "انخفضت", "خسائر",
))
PRICE_VOLATILE = KeywordSet(("volatil*", "jitters", "تقلبات", "اضطراب"))
# العنوان ينسب الحركة إلى محرّك آخر صراحةً
_OTHER_DRIVERS = KeywordSet((
    "earnings", "profit*", "results", "dividend*", "interest rate*", "rate cut*", "rate hike*", "fed",
    "inflation data", "jobs report",
    "أرباح", "الأرباح", "نتائج", "توزيعات", "أسعار الفائدة", "الفيدرالي",
))

SHIP_SUBJECT = KeywordSet((
    "ship", "ships", "shipping", "shipper*", "vessel*", "tanker*", "container*", "freight", "maritime",
    "transit*", "port", "ports", "maersk", "hapag",
    "سفن", "سفينة", "ناقلة", "ناقلات", "الشحن", "الملاحة", "حاويات", "ميناء", "موانئ", "العبور",
))
SHIP_DISRUPT = KeywordSet((
    "reroute*", "re route*", "divert*", "suspend*", "halt*", "pause*", "avoid*", "close", "closes", "closed",
    "closing", "closure*", "insurance", "premium*", "war risk", "freight rate*", "delay*",
    "تعليق", "تعلق", "يعلق", "علقت", "تحويل", "تغيير مسار", "وقف", "توقف", "تتجنب", "تجنب", "إغلاق",
    "التأمين", "أقساط", "تكاليف الشحن", "أسعار الشحن", "تأخير",
))
ENERGY_SUBJECT = KeywordSet((
    "oil", "crude", "gas", "lng", "refiner*", "pipeline*", "output", "production", "exports", "aramco",
    "oil field*", "gas field*",
    "نفط", "النفط", "الغاز", "غاز", "مصفاة", "مصافي", "خط أنابيب", "الإنتاج", "إنتاج", "الصادرات",
    "صادرات", "أرامكو", "حقل", "حقول", "إمدادات",
))
ENERGY_DISRUPT = KeywordSet((
    "halt*", "suspend*", "shut*", "disrupt*", "outage*", "force majeure", "offline",
    "توقف", "وقف", "تعليق", "تعطل", "تعطيل", "انقطاع", "القوة القاهرة", "إغلاق",
))
# قرار إنتاج من أوبك+ ليس أثرًا لهجوم
_OPEC_POLICY = KeywordSet(("opec", "أوبك", "voluntary cut*", "خفض طوعي"))

AVIATION_SUBJECT = KeywordSet((
    "flight*", "airport*", "airspace", "air traffic", "airline*", "aviation",
    "رحلات", "الرحلات", "رحلة", "مطار", "مطارات", "المجال الجوي", "الملاحة الجوية", "حركة الطيران",
    "الطيران",
))
AVIATION_DISRUPT = KeywordSet((
    "suspend*", "cancel*", "divert*", "reroute*", "close", "closes", "closed", "closing", "closure*",
    "halt*", "delay*", "grounded", "shut*", "disrupt*",
    "تعليق", "تعلق", "علقت", "إلغاء", "تلغي", "ألغت", "تحويل", "إغلاق", "أغلقت", "تغلق", "توقف",
    "تأخير", "تأخر", "اضطراب", "تعطل",
))

DIPLOMATIC_MOVE = KeywordSet((
    "sanction*", "condemn*", "summon*", "security council", "board of governors", "resolution",
    "censure*", "talks", "negotiat*", "envoy", "snapback", "expel* ambassador", "recall* ambassador",
    "عقوبات", "يدين", "تدين", "إدانة", "استدعاء", "استدعت", "استدعى", "مجلس الأمن", "مجلس المحافظين",
    "مشروع قرار", "مفاوضات", "محادثات", "مبعوث", "آلية الزناد", "سناب باك", "طرد السفير", "سحب السفير",
))
# موضوعات نووية تصلح «سببًا»: حدث على الأرض أو في الرقابة، لا خبر سياسي أو
# تنظيمي أو طبي
NUCLEAR_CAUSE_TOPICS = frozenset({
    "military_threat", "weapons_program", "safeguards_iaea", "safety_incident",
    "radiation_release", "trafficking_security", "radioactive_source",
})

KSA_NEAR = KeywordSet((
    "saudi border", "border with saudi", "الحدود السعودية", "الحدود مع السعودية", "الحد الجنوبي",
))


# ===== حقائق القصة =====

def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _extra(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw) if raw else {}
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


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
    dates = [_aware(m.event_date) for m in members if m.event_date is not None]
    trust = max(
        source_trust(m.source or "", _extra(m.extra_data).get("source_kind") or "", m.confidence or "")
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
# `models/database.run_causal_linking` يمرّر قائمة فارغة دائمًا.
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
