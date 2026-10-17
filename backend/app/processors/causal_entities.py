"""رصد - كيانات سلاسل السبب والأثر خارج المعجم الجغرافي (انظر processors/causal).

الدول والمدن والمنشآت والممرات المعروفة تأتي من `gazetteer.mentions`. هنا ما
لا يعرفه المعجم: القادة (الإيرانيون من `data/iranian_leaders.json` + إقليميون)،
والأصول السعودية بالاسم، وممرات إضافية — ومعها `extract_entities` التي تجمع
الكل من **العنوان وحده**.
"""
from __future__ import annotations

from functools import lru_cache

from ..static_data import iranian_leaders
from .gazetteer import COUNTRY_BY_CODE, PLACE_BY_KEY, facility_names, mentions
from .matching import KeywordSet
from .normalize import normalize_for_match


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
