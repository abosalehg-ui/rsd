"""رصد - معاجم محرّك سلاسل السبب والأثر (`processors/causal`).

تُطابَق كلها على **العنوان وحده** بعد التطبيع (انظر توثيق `causal`). مفصولة عن
منطق القوالب كي تُراجَع الكلمات وتُعدَّل دون تمرير المحرّك نفسه. معاجم الأثر
عبارات عاقبة («تعليق الرحلات»، «ارتفاع أسعار النفط») لا أسماء قطاعات.
"""
from __future__ import annotations

from .matching import KeywordSet

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
