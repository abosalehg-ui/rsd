"""رصد - تنظيف النصوص وتطبيعها قبل التحليل والعرض.

وظيفتان منفصلتان عمدًا:

- `clean_text` للعرض والتخزين: تفكّ كيانات HTML (`&quot;`) وتزيل الوسوم
  (`<b>`) وتوحّد المسافات. العناوين كانت تُخزَّن خامًا فتظهر الوسوم في الواجهة.
- `normalize_for_match` للمطابقة فقط: توحّد أشكال الألف والياء والتاء
  المربوطة وتزيل التشكيل والتطويل، فتتطابق «الإشعاعية» و«الاشعاعيه».
  لا تُعرض نتيجتها أبدًا.
"""
from __future__ import annotations

import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")

# التشكيل + ألف خنجرية + تطويل
_DIACRITICS_RE = re.compile(r"[ً-ْٰـ]")
_ARABIC_FOLD = str.maketrans({
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
    "ى": "ي",
    "ة": "ه",
    # أرقام عربية-هندية → لاتينية كي تتطابق "٦٠٪" مع "60%"
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
    "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
    "٪": "%",
    # فواصل الكلمات المركّبة: "nuclear-capable" ≡ "nuclear capable"
    "-": " ", "_": " ", "/": " ", "–": " ", "—": " ",
})


def clean_text(raw: str | None, cap: int | None = None) -> str:
    """نص صالح للعرض: كيانات مفكوكة، بلا وسوم، مسافات موحّدة.

    نفكّ الكيانات مرتين: خلاصات كثيرة تُرمِّز مرتين (`&amp;quot;`).
    """
    if not raw:
        return ""
    text = html.unescape(html.unescape(str(raw)))
    text = _TAG_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()
    if cap is not None and len(text) > cap:
        text = text[:cap].rstrip()
    return text


def normalize_for_match(text: str | None) -> str:
    """صيغة مطابقة: أحرف صغيرة، عربية موحّدة، مسافات مفردة."""
    if not text:
        return ""
    text = _DIACRITICS_RE.sub("", text.lower())
    text = text.translate(_ARABIC_FOLD)
    return _WS_RE.sub(" ", text).strip()


# ===== عناوين Google News وأمثالها: "العنوان - اسم المصدر" =====
_SOURCE_SUFFIX_RE = re.compile(r"\s+[-–—|]\s+([^-–—|]{2,60})$")


def split_source_suffix(title: str, known_source: str = "") -> tuple[str, str]:
    """يفصل لاحقة اسم المصدر من العنوان إن وُجدت.

    يُفصل فقط حين تطابق اللاحقة اسم المصدر المعروف، أو حين لا يُعرف المصدر
    واللاحقة قصيرة — كي لا نقتطع جزءًا حقيقيًا من عنوان يحوي شرطة.
    """
    m = _SOURCE_SUFFIX_RE.search(title or "")
    if not m:
        return title, ""
    suffix = m.group(1).strip()
    if known_source:
        if normalize_for_match(suffix) != normalize_for_match(known_source):
            return title, ""
    elif len(suffix.split()) > 5:
        return title, ""
    return title[: m.start()].rstrip(), suffix
