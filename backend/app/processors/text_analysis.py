"""رصد - تحليل النصوص المشترك بين الجامعين.

مصدر واحد لتصنيف الأحداث وتحديد مواقعها وتحويل تواريخها، بدل تكرار المنطق
(والإحداثيات وقوائم الكلمات) في كل جامع. أي تعديل تصنيف يتم هنا فقط.
"""
from __future__ import annotations

# ===== إحداثيات مراكز دول الشرق الأوسط (lat, lon, الاسم العربي) — مصدر واحد =====
COUNTRY_COORDS: dict[str, tuple[float, float, str]] = {
    "PS": (31.5, 34.47, "فلسطين"),
    "IL": (31.77, 35.23, "إسرائيل"),
    "YE": (15.55, 48.52, "اليمن"),
    "SY": (34.8, 38.99, "سوريا"),
    "LB": (33.87, 35.51, "لبنان"),
    "IR": (35.69, 51.39, "إيران"),
    "IQ": (33.31, 44.37, "العراق"),
    "SA": (24.71, 46.68, "السعودية"),
    "EG": (30.04, 31.24, "مصر"),
    "JO": (31.95, 35.93, "الأردن"),
    "TR": (39.93, 32.86, "تركيا"),
    "LY": (32.9, 13.18, "ليبيا"),
    "SD": (15.59, 32.53, "السودان"),
}

# أسماء عربية إضافية لدول الخليج (تُستخدم من GDELT)
ME_COUNTRY_NAMES: dict[str, str] = {
    **{code: name for code, (_, _, name) in COUNTRY_COORDS.items()},
    "AE": "الإمارات",
    "QA": "قطر",
    "KW": "الكويت",
    "BH": "البحرين",
    "OM": "عمان",
}

# ===== كلمات تحديد الموقع (رمز الدولة → كلمات مفتاحية عربية/إنجليزية) =====
COUNTRY_KEYWORDS: dict[str, list[str]] = {
    "PS": ["gaza", "palestine", "west bank", "غزة", "فلسطين", "الضفة"],
    "IL": ["israel", "tel aviv", "jerusalem", "إسرائيل", "تل أبيب", "القدس"],
    "YE": ["yemen", "houthi", "sanaa", "red sea", "اليمن", "حوثي", "صنعاء", "البحر الأحمر"],
    "SY": ["syria", "damascus", "aleppo", "سوريا", "دمشق", "حلب"],
    "LB": ["lebanon", "beirut", "hezbollah", "لبنان", "بيروت", "حزب الله"],
    "IR": ["iran", "tehran", "إيران", "طهران"],
    "IQ": ["iraq", "baghdad", "العراق", "بغداد"],
    "SA": ["saudi", "riyadh", "السعودية", "الرياض"],
    "EG": ["egypt", "cairo", "sinai", "مصر", "القاهرة", "سيناء"],
    "JO": ["jordan", "amman", "الأردن", "عمان"],
    "TR": ["turkey", "ankara", "تركيا", "أنقرة"],
    "LY": ["libya", "tripoli", "ليبيا", "طرابلس"],
    "SD": ["sudan", "khartoum", "السودان", "الخرطوم"],
}

# ===== قوائم كلمات التصنيف =====
NUCLEAR_KW = [
    "nuclear", "uranium", "enrichment", "iaea", "atomic", "reactor", "radiation",
    "centrifuge", "نووي", "يورانيوم", "تخصيب", "مفاعل", "ذري", "إشعاع",
]
MILITARY_KW = [
    "attack", "strike", "bomb", "missile", "war", "troops", "drone", "airstrike",
    "soldier", "combat", "killed", "kill", "dead", "casualt",
    "هجوم", "قصف", "صاروخ", "غارة", "حرب", "قتل", "طائرة مسيرة", "عسكري",
]
DEATH_KW = ["kill", "dead", "killed", "قتل", "قتلى"]
DIPLOMATIC_KW = [
    "ceasefire", "peace", "diplomat", "negotiate", "summit", "treaty",
    "united nations", "un ",
    "هدنة", "سلام", "دبلوماسي", "مفاوضات", "قمة", "وقف إطلاق", "اتفاق",
]
HUMANITARIAN_KW = [
    "humanitarian", "refugee", "aid", "civilian", "displaced", "famine",
    "إنساني", "لاجئ", "مساعدات", "نازح", "إغاثة", "مجاعة",
]
ECONOMIC_KW = [
    "sanctions", "oil", "economic", "trade", "عقوبات", "نفط", "اقتصاد",
]


def _has(text: str, keywords: list[str]) -> bool:
    return any(kw in text for kw in keywords)


def classify(
    title: str,
    description: str = "",
    base_category: str = "general",
    escalate_on_death: bool = True,
) -> tuple[str, str]:
    """تصنيف حدث إلى (category, severity) من عنوانه ووصفه.

    - base_category="nuclear" يفرض التصنيف النووي مباشرة (مصادر نووية مخصّصة).
    - escalate_on_death يرفع العسكري إلى "critical" عند ذكر قتلى.
    """
    if base_category == "nuclear":
        return "nuclear", "high"

    text = f"{title} {description}".lower()

    if _has(text, NUCLEAR_KW):
        return "nuclear", "high"
    if _has(text, MILITARY_KW):
        sev = "critical" if (escalate_on_death and _has(text, DEATH_KW)) else "high"
        return "military", sev
    if _has(text, DIPLOMATIC_KW):
        return "diplomatic", "medium"
    if _has(text, HUMANITARIAN_KW):
        return "humanitarian", "medium"
    if _has(text, ECONOMIC_KW):
        return "economic", "low"

    return base_category, "medium" if base_category != "general" else "low"


def country_code_from_text(text: str) -> str:
    """رمز ISO للدولة المذكورة في النص، أو "" عند التعذّر.

    مصدر واحد لمطابقة الدول يستعمله كل الجامعين.
    """
    lowered = text.lower()
    for code, keywords in COUNTRY_KEYWORDS.items():
        if _has(lowered, keywords):
            return code
    return ""


def geolocate(title: str, description: str = "") -> tuple[str, str, float | None, float | None]:
    """تحديد (code, name_ar, lat, lon) من النص. يعيد ("", "", None, None) عند التعذّر."""
    code = country_code_from_text(f"{title} {description}")
    if not code:
        return "", "", None, None
    lat, lon, name = COUNTRY_COORDS[code]
    return code, name, lat, lon
