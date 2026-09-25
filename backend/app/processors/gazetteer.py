"""رصد - معجم جغرافي: دول ومدن ومسطّحات مائية ومنشآت نووية.

كان تحديد الموقع يعرف 13 دولة فقط (بلا الإمارات وقطر والكويت والبحرين
وعُمان)، ويضع كل حدث في عاصمة دولته، ويختار أول دولة في ترتيب القاموس لا في
النص — فخبر «إيران تطلق صواريخ على إسرائيل» كان يُحدَّد في إسرائيل لأن IL
تسبق IR في القاموس، لا لأنها الهدف.

الترتيب الآن:
1. منشأة نووية مذكورة باسمها → إحداثياتها الدقيقة (precision = "facility").
2. مدينة أو مسطّح مائي → إحداثياته (precision = "city" / "region").
3. دولة → مركزها (precision = "country") — تُعرض في الواجهة كموقع تقريبي.

وداخل كل مستوى: الاسم المسبوق بحرف مكان/هدف («في»، «على»، "at"، "in"…)
يُفضَّل، وإلا فالأسبق ذكرًا. الدول الإقليمية (tier 1) قبل البعيدة (tier 2).

الأسماء العربية الملتبسة بكلمات شائعة مستبعدة عمدًا أو مقيّدة بسياق:
«الخبر» (الخبر/المدينة)، «صور»، «تدمر»، «العديد»، «مشهد»، «أراك»، «خرج»،
«المدينة»، «العقبة»، «الزرقاء». وعبارات مثل «مسقط رأسه» و«القوة القاهرة»
تُخفى قبل البحث.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .matching import KeywordSet, strip_phrases
from .normalize import normalize_for_match


@dataclass(frozen=True)
class Country:
    code: str
    name_ar: str
    name_en: str
    lat: float
    lon: float
    aliases: tuple[str, ...]
    tier: int = 1
    # أسماء قادة: تُستعمل فقط إن لم تُذكر أي دولة باسمها. «نتنياهو: تدمير نووي
    # إيران…» يخصّ إيران لا إسرائيل، لكن «نتنياهو يلتقي ترامب» يخصّ إسرائيل.
    people: tuple[str, ...] = ()


@dataclass(frozen=True)
class Place:
    key: str
    name_ar: str
    name_en: str
    country_code: str      # "" للمسطّحات المائية الدولية
    lat: float
    lon: float
    aliases: tuple[str, ...]
    kind: str = "city"     # city | region


@dataclass(frozen=True)
class Location:
    country_code: str
    country_name: str      # بالعربية (يُخزَّن في events.country كما كان)
    lat: float | None
    lon: float | None
    precision: str         # facility | city | region | country | none
    place_name: str = ""
    facility_id: str = ""


NO_LOCATION = Location("", "", None, None, "none")

# ===== الدول =====
# المركز = العاصمة أو مركز ثقل الأحداث (كما كان في COUNTRY_COORDS).
COUNTRIES: tuple[Country, ...] = (
    Country("PS", "فلسطين", "Palestine", 31.5, 34.47,
            ("palestine", "palestinian", "فلسطين", "فلسطيني")),
    Country("IL", "إسرائيل", "Israel", 31.77, 35.23,
            ("israel", "israeli", "idf", "إسرائيل", "إسرائيلي"),
            people=("netanyahu", "نتنياهو")),
    Country("YE", "اليمن", "Yemen", 15.55, 48.52,
            ("yemen", "yemeni", "houthi", "houthis", "اليمن", "يمني", "الحوثي", "الحوثيين", "حوثي")),
    Country("SY", "سوريا", "Syria", 34.8, 38.99,
            ("syria", "syrian", "سوريا", "سوري", "سورية")),
    Country("LB", "لبنان", "Lebanon", 33.87, 35.51,
            ("lebanon", "lebanese", "hezbollah", "لبنان", "لبناني", "حزب الله")),
    Country("IR", "إيران", "Iran", 35.69, 51.39,
            ("iran", "iranian", "irgc", "إيران", "إيراني", "الحرس الثوري"),
            people=("pezeshkian", "khamenei", "araghchi", "بزشكيان", "خامنئي", "عراقجي", "عراقچي")),
    Country("IQ", "العراق", "Iraq", 33.31, 44.37,
            ("iraq", "iraqi", "العراق", "عراقي")),
    Country("SA", "السعودية", "Saudi Arabia", 24.71, 46.68,
            ("saudi", "saudi arabia", "ksa", "السعودية", "سعودي", "المملكة العربية السعودية")),
    Country("AE", "الإمارات", "United Arab Emirates", 24.45, 54.38,
            ("uae", "united arab emirates", "emirati", "الإمارات", "إماراتي", "دولة الإمارات")),
    Country("QA", "قطر", "Qatar", 25.29, 51.53,
            ("qatar", "qatari", "قطر", "قطري")),
    Country("KW", "الكويت", "Kuwait", 29.37, 47.98,
            ("kuwait", "kuwaiti", "الكويت", "كويتي")),
    Country("BH", "البحرين", "Bahrain", 26.23, 50.59,
            ("bahrain", "bahraini", "البحرين", "بحريني")),
    Country("OM", "عُمان", "Oman", 23.59, 58.41,
            ("oman", "omani", "سلطنة عمان", "عمان", "عماني")),
    Country("EG", "مصر", "Egypt", 30.04, 31.24,
            ("egypt", "egyptian", "مصر", "مصري")),
    Country("JO", "الأردن", "Jordan", 31.95, 35.93,
            ("jordan", "jordanian", "amman", "الأردن", "أردني")),
    Country("TR", "تركيا", "Turkey", 39.93, 32.86,
            ("turkey", "turkish", "turkiye", "türkiye", "تركيا", "تركي")),
    Country("LY", "ليبيا", "Libya", 32.9, 13.18,
            ("libya", "libyan", "ليبيا", "ليبي")),
    Country("SD", "السودان", "Sudan", 15.59, 32.53,
            ("sudan", "sudanese", "السودان", "سوداني")),
    # tier 2: خارج الإقليم لكنها تتكرّر في الأخبار النووية والإشعاعية
    Country("UA", "أوكرانيا", "Ukraine", 50.45, 30.52,
            ("ukraine", "ukrainian", "أوكرانيا", "أوكراني"), tier=2),
    Country("RU", "روسيا", "Russia", 55.75, 37.62,
            ("russia", "russian", "روسيا", "روسي"), tier=2),
    Country("KP", "كوريا الشمالية", "North Korea", 39.03, 125.75,
            ("north korea", "dprk", "كوريا الشمالية", "كوريا الديمقراطية"), tier=2),
    Country("PK", "باكستان", "Pakistan", 33.69, 73.06,
            ("pakistan", "pakistani", "باكستان", "باكستاني"), tier=2),
    Country("IN", "الهند", "India", 28.61, 77.21,
            ("india", "indian", "الهند", "هندي"), tier=2),
    Country("JP", "اليابان", "Japan", 35.68, 139.69,
            ("japan", "japanese", "اليابان", "ياباني"), tier=2),
)

COUNTRY_BY_CODE: dict[str, Country] = {c.code: c for c in COUNTRIES}

# ===== المدن والمسطّحات المائية =====
PLACES: tuple[Place, ...] = (
    # إيران
    Place("tehran", "طهران", "Tehran", "IR", 35.689, 51.389, ("tehran", "طهران")),
    Place("isfahan", "أصفهان", "Isfahan", "IR", 32.654, 51.668, ("isfahan", "esfahan", "أصفهان")),
    Place("qom", "قم", "Qom", "IR", 34.640, 50.876, ("qom", "قم")),
    Place("tabriz", "تبريز", "Tabriz", "IR", 38.080, 46.292, ("tabriz", "تبريز")),
    Place("shiraz", "شيراز", "Shiraz", "IR", 29.591, 52.584, ("shiraz", "شيراز")),
    Place("mashhad", "مشهد", "Mashhad", "IR", 36.297, 59.606, ("mashhad", "مدينة مشهد")),
    Place("ahvaz", "الأهواز", "Ahvaz", "IR", 31.318, 48.671, ("ahvaz", "الأهواز", "الاحواز")),
    Place("bandar_abbas", "بندر عباس", "Bandar Abbas", "IR", 27.183, 56.267, ("bandar abbas", "بندر عباس")),
    Place("bushehr", "بوشهر", "Bushehr", "IR", 28.969, 50.839, ("bushehr", "بوشهر")),
    Place("karaj", "كرج", "Karaj", "IR", 35.840, 50.939, ("karaj", "كرج")),
    Place("kermanshah", "كرمانشاه", "Kermanshah", "IR", 34.314, 47.065, ("kermanshah", "كرمانشاه")),
    Place("chabahar", "تشابهار", "Chabahar", "IR", 25.292, 60.643, ("chabahar", "تشابهار", "جابهار")),
    Place("kharg", "جزيرة خرج", "Kharg Island", "IR", 29.245, 50.325, ("kharg", "جزيرة خرج")),
    Place("parchin", "بارشين", "Parchin", "IR", 35.520, 51.770, ("parchin", "بارشين")),
    # إسرائيل وفلسطين
    Place("tel_aviv", "تل أبيب", "Tel Aviv", "IL", 32.085, 34.781, ("tel aviv", "تل أبيب")),
    Place("jerusalem", "القدس", "Jerusalem", "IL", 31.778, 35.235, ("jerusalem", "القدس")),
    Place("haifa", "حيفا", "Haifa", "IL", 32.794, 34.990, ("haifa", "حيفا")),
    Place("beersheba", "بئر السبع", "Beersheba", "IL", 31.252, 34.791, ("beersheba", "beer sheva", "بئر السبع")),
    Place("dimona", "ديمونا", "Dimona", "IL", 31.068, 35.033, ("dimona", "ديمونا")),
    Place("eilat", "إيلات", "Eilat", "IL", 29.558, 34.952, ("eilat", "إيلات")),
    Place("nevatim", "نيفاتيم", "Nevatim", "IL", 31.208, 35.012, ("nevatim", "نيفاتيم")),
    Place("golan", "الجولان", "Golan Heights", "SY", 33.0, 35.75, ("golan", "الجولان")),
    Place("gaza", "غزة", "Gaza", "PS", 31.502, 34.467, ("gaza", "غزة", "قطاع غزة")),
    Place("rafah", "رفح", "Rafah", "PS", 31.297, 34.245, ("rafah", "رفح")),
    Place("khan_yunis", "خان يونس", "Khan Yunis", "PS", 31.346, 34.306, ("khan yunis", "khan younis", "خان يونس")),
    Place("west_bank", "الضفة الغربية", "West Bank", "PS", 31.95, 35.3, ("west bank", "الضفة الغربية", "الضفة")),
    Place("jenin", "جنين", "Jenin", "PS", 32.461, 35.300, ("jenin", "مخيم جنين", "مدينة جنين")),
    Place("ramallah", "رام الله", "Ramallah", "PS", 31.899, 35.204, ("ramallah", "رام الله")),
    Place("nablus", "نابلس", "Nablus", "PS", 32.222, 35.262, ("nablus", "نابلس")),
    Place("hebron", "الخليل", "Hebron", "PS", 31.532, 35.095, ("hebron", "الخليل")),
    # لبنان وسوريا
    Place("beirut", "بيروت", "Beirut", "LB", 33.894, 35.502, ("beirut", "بيروت")),
    Place("dahieh", "الضاحية الجنوبية", "Dahieh", "LB", 33.853, 35.510, ("dahieh", "dahiyeh", "الضاحية الجنوبية")),
    Place("sidon", "صيدا", "Sidon", "LB", 33.563, 35.369, ("sidon", "saida", "صيدا")),
    Place("tyre", "صور", "Tyre", "LB", 33.270, 35.203, ("tyre",)),
    Place("baalbek", "بعلبك", "Baalbek", "LB", 34.006, 36.204, ("baalbek", "بعلبك")),
    Place("nabatieh", "النبطية", "Nabatieh", "LB", 33.378, 35.484, ("nabatieh", "النبطية")),
    Place("damascus", "دمشق", "Damascus", "SY", 33.513, 36.292, ("damascus", "دمشق")),
    Place("aleppo", "حلب", "Aleppo", "SY", 36.202, 37.134, ("aleppo", "حلب")),
    Place("homs", "حمص", "Homs", "SY", 34.733, 36.723, ("homs", "حمص")),
    Place("latakia", "اللاذقية", "Latakia", "SY", 35.532, 35.791, ("latakia", "اللاذقية")),
    Place("tartus", "طرطوس", "Tartus", "SY", 34.889, 35.887, ("tartus", "طرطوس")),
    Place("deir_ezzor", "دير الزور", "Deir ez-Zor", "SY", 35.336, 40.141, ("deir ez zor", "deir ezzor", "دير الزور")),
    Place("idlib", "إدلب", "Idlib", "SY", 35.931, 36.634, ("idlib", "إدلب")),
    Place("raqqa", "الرقة", "Raqqa", "SY", 35.952, 39.009, ("raqqa", "الرقة")),
    Place("daraa", "درعا", "Daraa", "SY", 32.625, 36.106, ("daraa", "درعا")),
    # العراق
    Place("baghdad", "بغداد", "Baghdad", "IQ", 33.315, 44.366, ("baghdad", "بغداد")),
    Place("basra", "البصرة", "Basra", "IQ", 30.508, 47.783, ("basra", "البصرة")),
    Place("erbil", "أربيل", "Erbil", "IQ", 36.191, 44.009, ("erbil", "أربيل")),
    Place("mosul", "الموصل", "Mosul", "IQ", 36.340, 43.130, ("mosul", "الموصل")),
    Place("kirkuk", "كركوك", "Kirkuk", "IQ", 35.468, 44.392, ("kirkuk", "كركوك")),
    Place("najaf", "النجف", "Najaf", "IQ", 32.000, 44.336, ("najaf", "النجف")),
    Place("karbala", "كربلاء", "Karbala", "IQ", 32.616, 44.025, ("karbala", "كربلاء")),
    Place("anbar", "الأنبار", "Anbar", "IQ", 33.4, 42.0, ("anbar", "الأنبار")),
    Place("ain_al_asad", "عين الأسد", "Ain al-Asad", "IQ", 33.786, 42.441, ("ain al asad", "عين الأسد")),
    # اليمن
    Place("sanaa", "صنعاء", "Sanaa", "YE", 15.369, 44.191, ("sanaa", "sana'a", "صنعاء")),
    Place("aden", "عدن", "Aden", "YE", 12.785, 45.019, ("aden", "عدن")),
    Place("hodeidah", "الحديدة", "Hodeidah", "YE", 14.798, 42.954, ("hodeidah", "hudaydah", "الحديدة")),
    Place("marib", "مأرب", "Marib", "YE", 15.462, 45.325, ("marib", "مأرب")),
    Place("taiz", "تعز", "Taiz", "YE", 13.579, 44.021, ("taiz", "تعز")),
    # السعودية
    Place("riyadh", "الرياض", "Riyadh", "SA", 24.713, 46.675, ("riyadh", "الرياض")),
    Place("jeddah", "جدة", "Jeddah", "SA", 21.485, 39.193, ("jeddah", "jiddah", "جدة")),
    Place("dammam", "الدمام", "Dammam", "SA", 26.434, 50.103, ("dammam", "الدمام")),
    Place("mecca", "مكة المكرمة", "Mecca", "SA", 21.389, 39.858, ("mecca", "makkah", "مكة")),
    Place("medina", "المدينة المنورة", "Medina", "SA", 24.468, 39.614, ("medina", "madinah", "المدينة المنورة")),
    Place("jubail", "الجبيل", "Jubail", "SA", 27.011, 49.658, ("jubail", "الجبيل")),
    Place("dhahran", "الظهران", "Dhahran", "SA", 26.288, 50.114, ("dhahran", "الظهران")),
    Place("khobar", "الخبر", "Khobar", "SA", 26.217, 50.197, ("khobar", "مدينة الخبر", "محافظة الخبر")),
    Place("abqaiq", "بقيق", "Abqaiq", "SA", 25.938, 49.668, ("abqaiq", "بقيق")),
    Place("ras_tanura", "رأس تنورة", "Ras Tanura", "SA", 26.644, 50.159, ("ras tanura", "رأس تنورة")),
    Place("tabuk", "تبوك", "Tabuk", "SA", 28.383, 36.566, ("tabuk", "تبوك")),
    Place("jazan", "جازان", "Jazan", "SA", 16.889, 42.570, ("jazan", "jizan", "جازان", "جيزان")),
    Place("najran", "نجران", "Najran", "SA", 17.493, 44.128, ("najran", "نجران")),
    Place("abha", "أبها", "Abha", "SA", 18.216, 42.505, ("abha", "أبها")),
    Place("yanbu", "ينبع", "Yanbu", "SA", 24.089, 38.064, ("yanbu", "ينبع")),
    Place("neom", "نيوم", "NEOM", "SA", 28.0, 35.2, ("neom", "نيوم")),
    Place("hafr_albatin", "حفر الباطن", "Hafr Al-Batin", "SA", 28.432, 45.971, ("hafr al batin", "حفر الباطن")),
    Place("ahsa", "الأحساء", "Al-Ahsa", "SA", 25.383, 49.587, ("al ahsa", "hofuf", "الأحساء", "الهفوف")),
    Place("qassim", "القصيم", "Qassim", "SA", 26.326, 43.975, ("qassim", "القصيم")),
    Place("taif", "الطائف", "Taif", "SA", 21.270, 40.416, ("taif", "الطائف")),
    Place("arar", "عرعر", "Arar", "SA", 30.975, 41.038, ("arar", "عرعر")),
    # الإمارات
    Place("abu_dhabi", "أبوظبي", "Abu Dhabi", "AE", 24.453, 54.377, ("abu dhabi", "أبوظبي", "أبو ظبي")),
    Place("dubai", "دبي", "Dubai", "AE", 25.205, 55.271, ("dubai", "دبي")),
    Place("sharjah", "الشارقة", "Sharjah", "AE", 25.346, 55.421, ("sharjah", "الشارقة")),
    Place("fujairah", "الفجيرة", "Fujairah", "AE", 25.128, 56.326, ("fujairah", "الفجيرة")),
    Place("ras_al_khaimah", "رأس الخيمة", "Ras Al Khaimah", "AE", 25.800, 55.976, ("ras al khaimah", "رأس الخيمة")),
    Place("ruwais", "الرويس", "Ruwais", "AE", 24.110, 52.730, ("ruwais", "الرويس")),
    # قطر والكويت والبحرين وعُمان
    Place("doha", "الدوحة", "Doha", "QA", 25.286, 51.533, ("doha", "الدوحة")),
    Place("ras_laffan", "رأس لفان", "Ras Laffan", "QA", 25.909, 51.559, ("ras laffan", "رأس لفان")),
    Place("al_udeid", "قاعدة العديد", "Al Udeid", "QA", 25.117, 51.315, ("al udeid", "قاعدة العديد")),
    Place("ahmadi", "الأحمدي", "Ahmadi", "KW", 29.077, 48.084, ("ahmadi", "الأحمدي")),
    Place("manama", "المنامة", "Manama", "BH", 26.228, 50.586, ("manama", "المنامة")),
    Place("muscat", "مسقط", "Muscat", "OM", 23.588, 58.383, ("muscat", "مسقط")),
    Place("salalah", "صلالة", "Salalah", "OM", 17.019, 54.089, ("salalah", "صلالة")),
    Place("duqm", "الدقم", "Duqm", "OM", 19.662, 57.705, ("duqm", "الدقم")),
    Place("sohar", "صحار", "Sohar", "OM", 24.347, 56.709, ("sohar", "صحار")),
    Place("musandam", "مسندم", "Musandam", "OM", 26.2, 56.25, ("musandam", "مسندم")),
    # الأردن ومصر
    Place("aqaba", "العقبة", "Aqaba", "JO", 29.532, 35.006, ("aqaba", "ميناء العقبة", "مدينة العقبة")),
    Place("irbid", "إربد", "Irbid", "JO", 32.556, 35.850, ("irbid", "إربد")),
    Place("cairo", "القاهرة", "Cairo", "EG", 30.044, 31.236, ("cairo", "القاهرة")),
    Place("alexandria", "الإسكندرية", "Alexandria", "EG", 31.200, 29.919, ("alexandria", "الإسكندرية")),
    Place("sinai", "سيناء", "Sinai", "EG", 29.5, 33.8, ("sinai", "سيناء")),
    Place("suez", "السويس", "Suez", "EG", 29.967, 32.550, ("suez", "السويس", "قناة السويس")),
    Place("port_said", "بورسعيد", "Port Said", "EG", 31.265, 32.302, ("port said", "بورسعيد", "بور سعيد")),
    Place("el_dabaa", "الضبعة", "El Dabaa", "EG", 31.045, 28.495, ("el dabaa", "dabaa", "الضبعة")),
    # تركيا
    Place("ankara", "أنقرة", "Ankara", "TR", 39.934, 32.860, ("ankara", "أنقرة")),
    Place("istanbul", "إسطنبول", "Istanbul", "TR", 41.008, 28.978, ("istanbul", "إسطنبول", "اسطنبول")),
    Place("incirlik", "إنجرليك", "Incirlik", "TR", 37.002, 35.426, ("incirlik", "إنجرليك")),
    Place("mersin", "مرسين", "Mersin", "TR", 36.812, 34.641, ("mersin", "مرسين")),
    # ليبيا والسودان
    Place("tripoli_ly", "طرابلس", "Tripoli", "LY", 32.887, 13.191, ("tripoli", "طرابلس")),
    Place("benghazi", "بنغازي", "Benghazi", "LY", 32.117, 20.068, ("benghazi", "بنغازي")),
    Place("khartoum", "الخرطوم", "Khartoum", "SD", 15.501, 32.559, ("khartoum", "الخرطوم")),
    Place("port_sudan", "بورتسودان", "Port Sudan", "SD", 19.616, 37.216, ("port sudan", "بورتسودان", "بور سودان")),
    # tier 2
    Place("kyiv", "كييف", "Kyiv", "UA", 50.450, 30.523, ("kyiv", "kiev", "كييف")),
    Place("chernobyl", "تشيرنوبل", "Chernobyl", "UA", 51.389, 30.099, ("chernobyl", "chornobyl", "تشيرنوبل", "تشرنوبل")),
    Place("kursk", "كورسك", "Kursk", "RU", 51.730, 36.193, ("kursk", "كورسك")),
    Place("yongbyon", "يونغبيون", "Yongbyon", "KP", 39.797, 125.755, ("yongbyon", "يونغبيون")),
    Place("fukushima", "فوكوشيما", "Fukushima", "JP", 37.421, 141.033, ("fukushima", "فوكوشيما")),
    Place("vienna", "فيينا", "Vienna", "", 48.208, 16.373, ("vienna", "فيينا")),
    # مسطّحات مائية وممرات
    Place("hormuz", "مضيق هرمز", "Strait of Hormuz", "", 26.567, 56.250,
          ("strait of hormuz", "hormuz", "مضيق هرمز", "هرمز"), kind="region"),
    Place("gulf", "الخليج العربي", "Arabian Gulf", "", 26.8, 51.8,
          ("persian gulf", "arabian gulf", "the gulf", "الخليج العربي", "الخليج الفارسي"), kind="region"),
    Place("gulf_of_oman", "بحر عُمان", "Gulf of Oman", "", 24.5, 58.5,
          ("gulf of oman", "خليج عمان", "بحر عمان"), kind="region"),
    Place("red_sea", "البحر الأحمر", "Red Sea", "", 20.0, 38.8,
          ("red sea", "البحر الأحمر"), kind="region"),
    Place("bab_el_mandeb", "باب المندب", "Bab el-Mandeb", "", 12.6, 43.4,
          ("bab el mandeb", "bab al mandab", "باب المندب"), kind="region"),
)

# ===== أسماء المنشآت النووية =====
# المعرّف يطابق `data/nuclear_facilities.json` — الإحداثيات تُقرأ من هناك
# (مصدر واحد). الأسماء هنا غير ملتبسة: «بوشهر» وحدها مدينة، أما «محطة بوشهر»
# و"bushehr nuclear" فمنشأة.
FACILITY_ALIASES: dict[str, tuple[str, ...]] = {
    "ir-bushehr-1": ("bushehr nuclear", "bushehr power plant", "bushehr npp", "bushehr reactor",
                     "محطة بوشهر", "مفاعل بوشهر", "بوشهر النووية"),
    "ir-natanz": ("natanz", "نطنز"),
    "ir-fordow": ("fordow", "fordo", "فوردو", "فردو"),
    "ir-arak": ("khondab", "arak heavy water", "arak reactor", "ir 40", "مفاعل أراك", "خنداب", "آراك للماء الثقيل"),
    "ir-isfahan-ucf": ("isfahan nuclear", "isfahan uranium", "isfahan conversion", "ucf isfahan",
                       "منشأة أصفهان", "أصفهان النووية", "مركز أصفهان"),
    "ir-tehran-trr": ("tehran research reactor", "مفاعل طهران البحثي", "مفاعل طهران للأبحاث"),
    "il-dimona": ("dimona reactor", "negev nuclear", "shimon peres negev", "مفاعل ديمونا", "ديمونا النووي"),
    "il-soreq": ("soreq", "سوريك"),
    "ae-barakah-1": ("barakah", "barakah nuclear", "براكة", "محطة براكة"),
    "tr-akkuyu-1": ("akkuyu", "أكويو", "أكيويو", "آق قويو"),
    "eg-eldabaa-1": ("el dabaa nuclear", "dabaa nuclear", "محطة الضبعة", "الضبعة النووية"),
    "eg-inshas": ("inshas", "etrr 2", "أنشاص"),
    "sa-kacare-research": ("k.a.care", "k a care", "kacare", "king abdullah city for atomic",
                           "مدينة الملك عبدالله للطاقة الذرية", "مدينة الملك عبد الله للطاقة الذرية"),
    "jo-jrtr": ("jrtr", "jordan research and training reactor", "المفاعل الأردني", "مفاعل البحوث الأردني"),
    "iq-tuwaitha": ("tuwaitha", "التويثة"),
    "ua-zaporizhzhia": ("zaporizhzhia", "zaporizhia", "zaporozhye", "znpp", "زابوريجيا", "زابوروجيا"),
    "pk-kanupp-2": ("kanupp", "karachi nuclear"),
    "pk-chashma-1": ("chashma",),
    "in-tarapur-1": ("tarapur",),
    "in-kakrapar": ("kakrapar",),
    "ru-rostov": ("rostov nuclear", "rostov npp"),
}

# سوابق مكان/هدف: الاسم المسبوق بها يُفضَّل على الأسبق ذكرًا
_TARGET_PREPS = (
    "in", "at", "on", "near", "against", "targeting", "hits", "hit", "struck", "into", "over", "off",
    "في", "على", "قرب", "ضد", "باتجاه", "نحو", "داخل", "استهداف", "استهدف", "استهدفت",
)

# عبارات تُخفى قبل البحث لأنها تحوي اسم مكان بمعنى آخر
_GEO_EXCLUDE = KeywordSet((
    "مسقط رأس", "مسقط رأسه", "مسقط رأسها", "القوة القاهرة", "force majeure",
    "jordan river", "michael jordan", "turkey sandwich",
))


@lru_cache(maxsize=1)
def _facility_coords() -> dict[str, dict]:
    path = Path(__file__).resolve().parent.parent / "data" / "nuclear_facilities.json"
    with path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    return {f["id"]: f for f in data.get("facilities", [])}


@lru_cache(maxsize=1)
def _matchers():
    countries = [(c, KeywordSet(c.aliases)) for c in COUNTRIES]
    people = [(c, KeywordSet(c.people)) for c in COUNTRIES if c.people]
    places = [(p, KeywordSet(p.aliases)) for p in PLACES]
    facilities = [(fid, KeywordSet(aliases)) for fid, aliases in FACILITY_ALIASES.items()]
    return countries, places, facilities, people


def _preceded_by_target(norm_text: str, start: int) -> bool:
    before = norm_text[max(0, start - 24):start].split()
    tail = before[-2:] if before else []
    preps = {normalize_for_match(p) for p in _TARGET_PREPS}
    return any(w in preps for w in tail)


def _pick(hits: list[tuple[object, int]], norm_text: str):
    """من قائمة (عنصر، موضع): المسبوق بحرف هدف أولًا، وإلا الأسبق."""
    if not hits:
        return None
    targeted = [h for h in hits if _preceded_by_target(norm_text, h[1])]
    pool = targeted or hits
    return min(pool, key=lambda h: h[1])[0]


def find_facilities(norm_text: str) -> list[str]:
    """معرّفات المنشآت المذكورة بالاسم (بترتيب الذكر)."""
    _, _, facilities, _ = _matchers()
    found = []
    for fid, ks in facilities:
        hits = ks.search(norm_text)
        if hits:
            found.append((fid, hits[0].start))
    return [fid for fid, _ in sorted(found, key=lambda x: x[1])]


def locate(title: str, description: str = "") -> Location:
    """أدق موقع يمكن استخلاصه من النص. العنوان يُفحص أولًا ثم الوصف."""
    for part in (title, description):
        loc = _locate_one(part)
        if loc.precision != "none":
            return loc
    return NO_LOCATION


def _locate_one(text: str) -> Location:
    norm = normalize_for_match(text)
    if not norm:
        return NO_LOCATION
    norm, _ = strip_phrases(norm, _GEO_EXCLUDE)
    countries, places, _, people = _matchers()

    # 1) منشأة نووية
    facility_ids = find_facilities(norm)
    coords = _facility_coords()
    for fid in facility_ids:
        fac = coords.get(fid)
        if fac:
            code = fac.get("country_code", "")
            country = COUNTRY_BY_CODE.get(code)
            return Location(
                country_code=code,
                country_name=country.name_ar if country else fac.get("country", ""),
                lat=fac["latitude"], lon=fac["longitude"],
                precision="facility",
                place_name=fac.get("name_ar") or fac.get("name_en", ""),
                facility_id=fid,
            )

    # 2) مدينة / مسطّح مائي
    place_hits = []
    for place, ks in places:
        hits = ks.search(norm)
        if hits:
            place_hits.append((place, hits[0].start))
    place = _pick(place_hits, norm)
    if place is not None:
        country = COUNTRY_BY_CODE.get(place.country_code)
        return Location(
            country_code=place.country_code,
            country_name=country.name_ar if country else place.name_ar,
            lat=place.lat, lon=place.lon,
            precision=place.kind,
            place_name=place.name_ar,
        )

    # 3) دولة — الإقليمية قبل البعيدة
    by_tier: dict[int, list] = {}
    for country, ks in countries:
        hits = ks.search(norm)
        if hits:
            by_tier.setdefault(country.tier, []).append((country, hits[0].start))
    for tier in sorted(by_tier):
        chosen = _pick(by_tier[tier], norm)
        if chosen is None:
            continue
        # «عمان» بلا سياق = سلطنة عُمان؛ مع ذكر الأردن = العاصمة عمّان
        if chosen.code == "OM" and "JO" in {c.code for c, _ in by_tier[tier]}:
            chosen = COUNTRY_BY_CODE["JO"]
        return Location(
            country_code=chosen.code, country_name=chosen.name_ar,
            lat=chosen.lat, lon=chosen.lon, precision="country",
        )

    # 4) أسماء قادة — آخر ملاذ
    person_hits = []
    for country, ks in people:
        hits = ks.search(norm)
        if hits:
            person_hits.append((country, hits[0].start))
    if person_hits:
        chosen = min(person_hits, key=lambda h: h[1])[0]
        return Location(
            country_code=chosen.code, country_name=chosen.name_ar,
            lat=chosen.lat, lon=chosen.lon, precision="country",
        )
    return NO_LOCATION


def country_code_from_text(text: str) -> str:
    """رمز الدولة من النص (أدق مستوى متاح)، أو "" عند التعذّر."""
    return _locate_one(text).country_code


# ===== المسافة إلى المملكة =====
# نقاط مرجعية على امتداد المملكة (مدن حدودية وساحلية ومراكز سكانية). المسافة
# إلى أقربها تقريب معقول لـ«المسافة إلى أراضي المملكة» دون مضلّع حدود كامل.
KSA_REFERENCE_POINTS: tuple[tuple[str, str, float, float], ...] = (
    ("الرياض", "Riyadh", 24.713, 46.675), ("الدمام", "Dammam", 26.434, 50.103),
    ("الجبيل", "Jubail", 27.011, 49.658), ("رأس تنورة", "Ras Tanura", 26.644, 50.159),
    ("الخفجي", "Khafji", 28.439, 48.491), ("حفر الباطن", "Hafr Al-Batin", 28.432, 45.971),
    ("عرعر", "Arar", 30.975, 41.038), ("القريات", "Qurayyat", 31.332, 37.343),
    ("تبوك", "Tabuk", 28.383, 36.566), ("حقل", "Haql", 29.289, 34.938),
    ("ينبع", "Yanbu", 24.089, 38.064), ("جدة", "Jeddah", 21.485, 39.193),
    ("جازان", "Jazan", 16.889, 42.570), ("نجران", "Najran", 17.493, 44.128),
    ("شرورة", "Sharurah", 17.469, 47.107), ("الأحساء", "Al-Ahsa", 25.383, 49.587),
    ("سلوى", "Salwa", 24.735, 50.829), ("البطحاء", "Al-Batha", 24.100, 51.550),
    ("الوديعة", "Al-Wadiah", 17.050, 47.100), ("طريف", "Turaif", 31.672, 38.663),
    ("الجوف", "Al-Jouf", 29.970, 40.200), ("تيماء", "Tayma", 27.630, 38.550),
    ("المدينة المنورة", "Medina", 24.468, 39.614), ("أبها", "Abha", 18.216, 42.505),
    ("وادي الدواسر", "Wadi Al-Dawasir", 20.460, 44.800), ("الخرخير", "Al-Kharkhir", 18.870, 51.130),
    ("شيبة", "Shaybah", 22.520, 54.000),
)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest_ksa_point(lat: float | None, lon: float | None) -> tuple[float, str] | None:
    """(المسافة بالكيلومتر، اسم أقرب نقطة سعودية) أو None بلا إحداثيات."""
    if lat is None or lon is None:
        return None
    best = min(
        ((haversine_km(lat, lon, plat, plon), name) for name, _, plat, plon in KSA_REFERENCE_POINTS),
        key=lambda x: x[0],
    )
    return round(best[0], 1), best[1]


_KSA_EN = {ar: en for ar, en, _, _ in KSA_REFERENCE_POINTS}


def ksa_point_en(name_ar: str) -> str:
    """الاسم الإنجليزي لنقطة مرجعية سعودية (للواجهة الإنجليزية)."""
    return _KSA_EN.get(name_ar, name_ar)


# ===== توافق خلفي مع الواجهات السابقة =====
COUNTRY_COORDS: dict[str, tuple[float, float, str]] = {
    c.code: (c.lat, c.lon, c.name_ar) for c in COUNTRIES
}
ME_COUNTRY_NAMES: dict[str, str] = {c.code: c.name_ar for c in COUNTRIES}
