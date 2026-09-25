"""رصد - تصنيف المخاطر النووية والإشعاعية وتقدير درجتها.

كل خبر يمرّ بثلاث خطوات:

1. **البوابة**: هل الخبر نووي/إشعاعي أصلًا؟ تُخفى أولًا العبارات التي تحوي
   «نووي» بمعنى آخر («الحمض النووي»، "nuclear family"، «الإشعاع الشمسي»)،
   ثم يُبحث عن مفردات جوهرية (نووي، إشعاعي، يورانيوم، الوكالة الذرية، أسماء
   منشآت غير ملتبسة…).

2. **الموضوع**: أحد عشر موضوعًا (TOPICS). لكل موضوع كلمات ووزن أساس. يُختار
   الموضوع صاحب أعلى (عدد المطابقات × وزن الأساس)، وتُحسم المساواة بالترتيب.
   عبارات النفي المطمئنة («لم تُرصد زيادة في مستويات الإشعاع») تُخفى قبل
   المطابقة كي لا ترفع موضوع «انبعاث إشعاعي»، وتُسجَّل علامة `reassuring`.

3. **الدرجة (0-100)**: أساس الموضوع + شدة − تخفيف ± قرب من المملكة ± ثقة
   المصدر. كل مكوّن يُعاد في `components` كي تعرض الواجهة لماذا بلغ الخبر
   درجته — الدرجة لا تُعرض رقمًا مجردًا.

الأوزان اجتهاد تشغيلي أولي قابل للمعايرة، لا معيار رسمي. التوثيق الكامل
في docs/nuclear-risk-methodology.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .gazetteer import Location, find_facilities, nearest_ksa_point
from .matching import KeywordSet, strip_phrases
from .normalize import normalize_for_match


@dataclass(frozen=True)
class Topic:
    key: str
    category: str          # nuclear | radiological
    base: int              # درجة الأساس 0-100
    terms: KeywordSet


# ===== البوابة =====
_EXCLUDE = KeywordSet((
    # "نووي" بمعنى غير ذري
    "الحمض النووي", "حمض نووي", "الأحماض النووية", "dna", "rna", "nucleic acid",
    "nuclear family", "nuclear option", "الخيار النووي",
    "nuclear magnetic resonance", "الرنين المغناطيسي النووي",
    # "إشعاع" غير مؤيِّن
    "الإشعاع الشمسي", "الأشعة فوق البنفسجية", "solar radiation", "uv radiation",
    "ultraviolet", "infrared", "الأشعة تحت الحمراء", "heat radiation", "الإشعاع الحراري",
    "microwave radiation", "radiation of warmth",
    # مصطلحات صناعية تحوي كلمة «حادث» دون أن تكون حادثًا
    "accident tolerant", "accident tolerant fuel", "atf", "الوقود المقاوم للحوادث",
))

_CORE = KeywordSet((
    "nuclear", "atomic energy", "atomic bomb", "uranium", "plutonium", "reactor", "enrich*",
    "iaea", "centrifuge*", "npt", "jcpoa", "fissile", "radiation", "radioactive*", "radiological",
    "radioisotope*", "caesium", "cesium", "cobalt 60", "iridium 192", "dirty bomb", "nuclear weapon",
    "نووي", "نووية", "الطاقة الذرية", "القنبلة الذرية", "قنبلة ذرية", "يورانيوم", "اليورانيوم",
    "بلوتونيوم", "مفاعل", "تخصيب", "مخصب", "طرد مركزي", "أجهزة الطرد", "إشعاع", "إشعاعي",
    "مشع", "مشعة", "سيزيوم", "قنبلة قذرة", "معاهدة عدم الانتشار",
))


# ===== الموضوعات =====
# الترتيب مهم: عند التساوي يُقدَّم الأخطر.
TOPICS: tuple[Topic, ...] = (
    Topic("radiation_release", "radiological", 80, KeywordSet((
        "radiation leak", "radioactive leak", "radioactive release", "radiation release",
        "radioactive contamination", "radiological contamination", "radiation levels",
        "elevated radiation", "radiation spike", "increase in radiation", "fallout",
        "radioactive cloud", "radioactive plume", "meltdown", "core damage", "ines",
        "iodine tablets", "potassium iodide", "exclusion zone", "radioactive water",
        "تسرب إشعاعي", "تسرب نووي", "تسرب مواد مشعة", "تلوث إشعاعي", "مستويات الإشعاع",
        "ارتفاع الإشعاع", "ارتفاع مستوى الإشعاع", "غبار نووي", "سحابة مشعة", "انصهار",
        "أقراص اليود", "يوديد البوتاسيوم", "انبعاثات مشعة", "مياه مشعة", "إشعاعات خطيرة",
    ))),
    # الكلمات الحركية (قصف، صاروخ…) لا تُحتسب هنا إلا بوجود «موقع» في النص —
    # انظر `_KINETIC` و`_SITE_CONTEXT` أدناه. هذه القائمة لاستخدام السلاح
    # النووي نفسه، وتُحتسب دائمًا.
    Topic("military_threat", "nuclear", 75, KeywordSet((
        "nuclear war", "nuclear strike", "tactical nuclear", "nuclear test", "nuclear attack",
        "use of nuclear weapons", "nuclear detonation",
        "حرب نووية", "تجربة نووية", "ضربة نووية", "هجوم نووي", "استخدام السلاح النووي",
        "تفجير نووي",
    ))),
    # «مواد مشعة» وحدها لا تكفي (ترد في شرح تقني عادي) — انظر `_SOURCE_GENERIC`
    Topic("radioactive_source", "radiological", 62, KeywordSet((
        "orphan source", "cobalt 60", "caesium 137", "cesium 137", "iridium 192", "americium",
        "dirty bomb", "radiological dispersal", "rdd", "radiography source",
        "missing radioactive", "stolen radioactive", "lost radioactive",
        "قنبلة قذرة", "كوبالت 60", "سيزيوم 137", "إيريديوم 192", "مصدر مشع مفقود",
    ))),
    Topic("trafficking_security", "nuclear", 60, KeywordSet((
        "nuclear smuggling", "smuggl*", "nuclear theft", "nuclear security", "nuclear terrorism",
        "sabotage*", "cyberattack*", "cyber attack*", "stuxnet", "illicit trafficking", "itdb",
        "physical protection", "unauthorized access",
        "تهريب", "سرقة", "الأمن النووي", "إرهاب نووي", "تخريب", "هجوم سيبراني", "هجمات سيبرانية",
        "اختراق", "الاتجار غير المشروع", "الحماية المادية",
    ))),
    Topic("safety_incident", "nuclear", 55, KeywordSet((
        "incident", "accident", "emergency shutdown", "scram", "reactor trip", "fire at",
        "loss of coolant", "coolant leak", "loss of power", "off site power", "power outage",
        "blackout", "emergency diesel", "safety concern*", "unplanned shutdown", "malfunction",
        "حادث", "حادثة", "عطل", "إغلاق طارئ", "توقف طارئ", "حريق", "فقدان الطاقة",
        "انقطاع الكهرباء", "انقطاع التيار", "فقدان التبريد", "عطل في التبريد",
        "مخاوف السلامة", "خلل",
    ))),
    Topic("weapons_program", "nuclear", 50, KeywordSet((
        "60%", "90%", "weapons grade", "breakout", "weaponization", "weaponisation", "warhead*",
        "nuclear weapon*", "nuclear bomb", "atomic bomb", "highly enriched", "heu", "plutonium",
        "reprocessing", "npt withdrawal", "withdraw from the npt", "enrich*", "centrifuge*",
        "stockpile", "nuclear threat", "nuclear program*", "nuclear programme*",
        "nuclear ambition*", "arms race", "nuclear arms", "nuclear armed", "nuclear capable",
        "درجة نقاء", "لأغراض عسكرية", "سلاح نووي", "أسلحة نووية", "قنبلة نووية", "قنبلة ذرية",
        "رؤوس نووية", "رأس نووي", "عالي التخصيب", "أجهزة الطرد المركزي", "طرد مركزي",
        "بلوتونيوم", "إعادة المعالجة", "الانسحاب من معاهدة", "تخصيب", "مخصب", "مخزون",
        "تهديد نووي", "البرنامج النووي", "طموحات نووية", "سباق التسلح", "امتلاك قنبلة",
        "التسلح النووي", "قدرات نووية",
    ))),
    Topic("safeguards_iaea", "nuclear", 35, KeywordSet((
        "iaea", "inspector*", "inspection*", "safeguards", "board of governors", "grossi",
        "additional protocol", "non proliferation", "nonproliferation", "npt", "verification",
        "monitoring cameras", "undeclared",
        "الوكالة الدولية للطاقة الذرية", "الطاقة الذرية", "مفتش", "مفتشين", "تفتيش",
        "ضمانات", "مجلس المحافظين", "غروسي", "البروتوكول الإضافي", "معاهدة عدم الانتشار",
        "عدم الانتشار", "كاميرات المراقبة", "غير معلن",
    ))),
    Topic("diplomacy_sanctions", "nuclear", 30, KeywordSet((
        "nuclear talks", "nuclear deal", "nuclear agreement", "jcpoa", "snapback", "sanction*",
        "negotiat*", "123 agreement", "security council", "talks", "diplomatic",
        "مفاوضات", "محادثات", "اتفاق نووي", "الاتفاق النووي", "عقوبات", "آلية الزناد",
        "سناب باك", "مجلس الأمن", "اتفاقية", "اتفاق", "دبلوماسي",
    ))),
    Topic("emergency_preparedness", "radiological", 20, KeywordSet((
        "emergency exercise", "drill*", "emergency preparedness", "emergency response",
        "convex", "radiation emergency", "nuclear emergency", "emergency plan*",
        "تمرين", "تمرين طوارئ", "التأهب", "الاستعداد للطوارئ", "الاستجابة للطوارئ",
        "خطة الطوارئ", "الطوارئ الإشعاعية", "الطوارئ النووية",
    ))),
    Topic("regulatory", "nuclear", 15, KeywordSet((
        "regulator*", "licens*", "permit*", "nrrc", "fanr", "enrra", "nuclear regulatory",
        "regulation*", "safety review", "peer review", "irrs", "oversight",
        "هيئة الرقابة النووية والإشعاعية", "الرقابة النووية", "ترخيص", "رخصة", "تصريح",
        "لائحة", "الهيئة الاتحادية للرقابة النووية", "هيئة الرقابة", "رقابي", "رقابية",
    ))),
    Topic("medical_industrial", "radiological", 12, KeywordSet((
        "nuclear medicine", "radiotherapy", "radiation therapy", "radiopharmaceutical*",
        "radioisotope*", "medical isotope*", "x ray", "radiography", "radiation protection",
        "dosimetry", "occupational exposure", "irradiation",
        "الطب النووي", "العلاج الإشعاعي", "نظائر مشعة", "النظائر المشعة", "الأشعة السينية",
        "الوقاية من الإشعاع", "قياس الجرعات", "التعرض المهني", "التشعيع",
    ))),
    Topic("energy_program", "nuclear", 10, KeywordSet((
        "nuclear power", "nuclear plant", "power plant", "nuclear energy", "smr",
        "small modular", "uranium mining", "uranium exploration", "fuel load*",
        "grid connection", "reactor", "construction", "haleu", "low enriched uranium", "leu",
        "laser enrichment", "enrichment services", "enrichment capacity", "fuel supply",
        "fuel cycle", "uranium production", "uranium supply", "uranium price*",
        "محطة نووية", "الطاقة النووية", "محطة طاقة", "مفاعل", "مفاعلات", "مفاعلات صغيرة",
        "تعدين اليورانيوم", "خام اليورانيوم", "تحميل الوقود", "الربط بالشبكة", "إنشاء",
    ))),
)

# كلمات حركية: تُنسب لموضوع «تهديد عسكري» فقط حين يذكر النص منشأة أو موقعًا
# نوويًا. «إيران لا تريد قنبلة نووية» أو «ترامب يستضيف شي… وسط تهديد نووي
# إيراني» كانت تُصنَّف تهديدًا عسكريًا (75) لمجرد كلمة bomb أو threat.
_KINETIC = KeywordSet((
    "strike", "strikes", "attack", "attacked", "attacks", "hits", "hit by", "airstrike*",
    "bombing", "bombed", "bombard*", "missile*", "drone*", "struck", "targeted", "destroy*",
    "shelling", "shelled", "military action", "sabotage*",
    "قصف", "ضربة", "ضربات", "غارة", "غارات", "هجوم", "هجمات", "استهداف", "استهدف", "استهدفت",
    "صاروخ", "صواريخ", "مسيرة", "مسيرات", "تدمير", "عمل عسكري",
))
# سياق «موقع نووي» تحديدًا: "air defense sites" أو «محطة كهرباء» لا تكفي
_SITE_CONTEXT = KeywordSet((
    "nuclear plant", "nuclear power plant", "power plant", "nuclear station", "reactor*",
    "nuclear facilit*", "nuclear site*", "enrichment site*", "enrichment facilit*",
    "enrichment plant", "centrifuge hall", "nuclear installation*",
    "منشأة نووية", "منشآت نووية", "المنشآت النووية", "مفاعل", "محطة نووية",
    "المحطة النووية", "موقع نووي", "مواقع نووية", "منشأة التخصيب", "منشآت التخصيب",
))

# مفردات المصادر المشعة العامة: تُحتسب لموضوع «مصدر مشع» فقط مع سياق فقدان
# أو سرقة أو ضبط. «…لمنع إطلاق المواد المشعة» في شرح تقني عن الوقود ليس حادثة.
_SOURCE_GENERIC = KeywordSet((
    "radioactive source*", "radioactive material*", "radioactive substance*", "sealed source*",
    "مصدر مشع", "مصادر مشعة", "مواد مشعة", "مادة مشعة", "مصادر إشعاعية", "مصدر إشعاعي",
))
_LOSS_CONTEXT = KeywordSet((
    "missing", "stolen", "theft", "lost", "found", "seized", "abandoned", "smuggl*",
    "discovered", "unattended", "recovered", "scrap", "exposure", "exposed",
    "مفقود", "مفقودة", "فقدان", "سرقة", "مسروق", "مسروقة", "ضبط", "العثور", "عثر",
    "مهجور", "مهملة", "تهريب", "خردة", "تعرض",
))

TOPIC_BY_KEY = {t.key: t for t in TOPICS}
TOPIC_KEYS = tuple(t.key for t in TOPICS)
DEFAULT_TOPIC = "energy_program"

# ===== المعدِّلات =====
_INTENSIFIERS = KeywordSet((
    "explosion", "casualt*", "killed", "dead", "evacuat*", "state of emergency", "emergency",
    "meltdown", "leak*", "released", "elevated", "damage*", "injured", "fire",
    "urgent", "breaking", "exposed", "exposure",
    "انفجار", "قتلى", "ضحايا", "إخلاء", "حالة الطوارئ", "طوارئ", "تسرب", "إصابات",
    "أضرار", "دمار", "عاجل", "تعرض", "حريق",
))
# صيغ التصريح: «X: …»، "says"، «قال»… خبر عن موقف لا عن واقعة — يُخفَّض قليلًا
# (يبقى حدثًا سياسيًا مهمًا، لكن لا يساوي ضربة فعلية).
_STATEMENT = KeywordSet((
    "says", "said", "warns", "warned", "claims", "vows", "threatens", "statement",
    "interview", "told", "insists", "denies", "rejects", "ready to", "willing to",
    "قال", "يقول", "صرح", "تصريح", "تصريحات", "أكد", "يؤكد", "حذر", "يحذر", "توعد",
    "يتوعد", "هدد", "يهدد", "بيان", "مقابلة", "ينفي", "نفى", "يرفض", "رفض", "مستعدون",
    "استعداد", "يبدي",
))
_DAMPENERS = KeywordSet((
    "exercise", "drill*", "simulation", "simulated", "training", "workshop", "conference",
    "webinar", "anniversary", "history", "opinion", "analysis", "podcast", "course",
    "scholarship", "award", "celebrat*", "museum", "documentary", "film",
    "تمرين", "محاكاة", "ورشة عمل", "مؤتمر", "ندوة", "ذكرى", "تاريخ", "رأي", "تحليل",
    "دورة تدريبية", "تدريب", "جائزة", "احتفال", "متحف", "فيلم", "منحة",
))
# عبارات مطمئنة: تُخفى من النص قبل المطابقة ثم تخفّض الدرجة
_REASSURING = KeywordSet((
    "no increase in radiation", "no increase in off site radiation", "no radiation leak",
    "no radioactive release", "no release of radioactive", "no leak", "no radiological",
    "radiation levels remain normal", "radiation levels are normal", "normal radiation levels",
    "no abnormal radiation", "no impact on radiation", "no radiological consequences",
    "no radioactive material", "no radioactive*", "no radiation", "not radioactive",
    "no elevated radiation", "no danger to the public", "no risk to the public",
    "لا توجد مواد مشعة", "خالية من المواد المشعة", "خال من الإشعاع", "لا يشكل خطرا",
    "لا تسرب", "لا يوجد تسرب", "عدم وجود تسرب", "لم يتم رصد", "لم ترصد", "لم يرصد",
    "مستويات الإشعاع طبيعية", "المستويات طبيعية", "لا توجد زيادة", "لا زيادة في مستويات",
    "عدم تسجيل", "لم تسجل", "لا خطر إشعاعي", "لا يوجد خطر",
))

# ===== ثقة المصدر =====
# معامل ضرب على الدرجة بعد جمع المكوّنات. الرسمي/المتخصص 1.0، الإخباري العام
# 0.9، المجمِّعات غير المعروفة 0.85، ومدوّنات التحليل والرأي 0.8 (تناقش
# سيناريوهات لا وقائع).
SOURCE_TRUST = {"official": 1.0, "specialist": 1.0, "news": 0.9, "aggregator": 0.85, "analysis": 0.8}


@dataclass
class NuclearAssessment:
    relevant: bool
    category: str = ""
    topic: str = ""
    risk_score: float = 0.0
    severity: str = "low"
    facility_ids: list[str] = field(default_factory=list)
    distance_to_ksa_km: float | None = None
    nearest_ksa_point: str = ""
    reassuring: bool = False
    components: dict = field(default_factory=dict)
    matched: list[str] = field(default_factory=list)


def _topic_counts(norm: str, site_context: bool) -> dict[str, int]:
    """عدد المقاطع لكل موضوع، بعد إسناد كل مقطع لأطول عبارة تطابقه عبر كل
    الموضوعات: «nuclear bomb» لبرنامج التسلح لا تُحتسب «bomb» فيها مرة ثانية
    لموضوع التهديد العسكري.
    """
    spans: list[tuple[int, int, str]] = []
    for topic in TOPICS:
        spans.extend((h.start, h.end, topic.key) for h in topic.terms.search(norm))
    if _LOSS_CONTEXT.matches(norm):
        spans.extend((h.start, h.end, "radioactive_source") for h in _SOURCE_GENERIC.search(norm))

    kinetic = _KINETIC.search(norm)
    if site_context:
        spans.extend((h.start, h.end, "military_threat") for h in kinetic)
    elif kinetic and not spans:
        # لغة عسكرية عن البرنامج النووي بلا موقع محدد («تدمير نووي إيران»):
        # شأن سياسي-تسليحي لا تهديد لمنشأة بعينها
        spans.extend((h.start, h.end, "weapons_program") for h in kinetic[:1])

    spans.sort(key=lambda s: (-(s[1] - s[0]), s[0]))
    taken: list[tuple[int, int]] = []
    counts: dict[str, int] = {}
    for start, end, key in spans:
        if all(end <= a or start >= b for a, b in taken):
            taken.append((start, end))
            counts[key] = counts.get(key, 0) + 1
    return counts


def severity_from_score(score: float) -> str:
    if score >= 75:
        return "critical"
    if score >= 55:
        return "high"
    if score >= 30:
        return "medium"
    return "low"


def proximity_adjustment(distance_km: float | None) -> int:
    """الأثر العابر للحدود: الأقرب للمملكة أعلى أولوية للرصد الوطني.

    خبر بلا أي موقع قابل للاستخلاص يُخفَّض قليلًا (-5): أغلبه أخبار صناعة أو
    أبحاث عامة من الخلاصات الدولية، والخبر الإقليمي يذكر مكانه عادةً."""
    if distance_km is None:
        return -5
    if distance_km < 300:
        return 15
    if distance_km < 800:
        return 8
    if distance_km < 1500:
        return 3
    return -10


def is_nuclear_relevant(title: str, description: str = "") -> bool:
    norm = normalize_for_match(f"{title} {description}")
    norm, _ = strip_phrases(norm, _EXCLUDE)
    return _CORE.matches(norm) or bool(find_facilities(norm))


def assess(
    title: str,
    description: str = "",
    location: Location | None = None,
    *,
    source_kind: str = "news",
    force: bool = False,
) -> NuclearAssessment:
    """تقييم خبر. `force=True` للمصادر النووية المتخصصة: يتخطّى البوابة
    (كل ما تنشره World Nuclear News نووي حتى لو لم يذكر الكلمة)."""
    norm = normalize_for_match(f"{title} {description}")
    norm, _ = strip_phrases(norm, _EXCLUDE)
    facilities = find_facilities(norm)

    if not force and not (_CORE.matches(norm) or facilities):
        return NuclearAssessment(relevant=False)

    norm, reassuring_hits = strip_phrases(norm, _REASSURING)
    reassuring = bool(reassuring_hits)

    # العنوان يُحسب مرتين: كلماته أدلّ على الموضوع من الوصف
    title_norm, _ = strip_phrases(strip_phrases(normalize_for_match(title), _EXCLUDE)[0], _REASSURING)

    site_context = bool(facilities) or _SITE_CONTEXT.matches(norm)
    counts = _topic_counts(norm, site_context)
    for key, n in _topic_counts(title_norm, site_context).items():
        counts[key] = counts.get(key, 0) + n
    matched = sorted({t for topic in TOPICS for t in topic.terms.matched_terms(norm)})

    best: tuple[float, Topic] | None = None
    for topic in TOPICS:   # الترتيب يحسم التساوي لصالح الأخطر
        n = counts.get(topic.key, 0)
        if n and (best is None or n * topic.base > best[0]):
            best = (n * topic.base, topic)
    topic = best[1] if best else TOPIC_BY_KEY[DEFAULT_TOPIC]

    base = topic.base
    intensity = min(_INTENSIFIERS.count(norm) * 8, 20)
    dampening = -min(_DAMPENERS.count(norm) * 15, 30)
    reassurance = -15 if reassuring else 0
    is_statement = _STATEMENT.matches(norm) or ":" in (title or "")[:40]
    # لا يتراكم مع التطمين: التطمين نفسه تصريح رسمي عن واقعة حقيقية
    statement = -15 if is_statement and not intensity and not reassuring else 0
    specificity = 5 if facilities else 0

    distance = nearest = None
    if location is not None and location.lat is not None:
        near = nearest_ksa_point(location.lat, location.lon)
        if near:
            distance, nearest = near
    proximity = proximity_adjustment(distance)

    trust = SOURCE_TRUST.get(source_kind, 0.9)
    raw = base + intensity + dampening + reassurance + statement + specificity + proximity
    score = max(0.0, min(100.0, round(raw * trust, 1)))

    return NuclearAssessment(
        relevant=True,
        category=topic.category,
        topic=topic.key,
        risk_score=score,
        severity=severity_from_score(score),
        facility_ids=facilities,
        distance_to_ksa_km=distance,
        nearest_ksa_point=nearest or "",
        reassuring=reassuring,
        components={
            "base": base,
            "intensity": intensity,
            "dampening": dampening,
            "reassurance": reassurance,
            "statement": statement,
            "specificity": specificity,
            "proximity": proximity,
            "source_trust": trust,
        },
        matched=matched[:12],
    )
