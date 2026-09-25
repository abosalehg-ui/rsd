"""رصد - مطابقة الكلمات المفتاحية بحدود الكلمة.

المطابقة السابقة كانت `kw in text` (بحث عن جزء نص)، فكانت:
  "war" تطابق "warning" · "aid" تطابق "said" · "dead" تطابق "deadline"
  "قتل" تطابق "يقتلع" · "un " تطابق "run "
فتتضخّم التصنيفات العسكرية والحرجة بأخبار لا صلة لها.

هنا تُترجَم كل كلمة مفتاحية مرة واحدة إلى تعبير نمطي بحدود كلمة:

- إنجليزي: الكلمة نفسها + لواحق تصريف شائعة (s/es/ed/ing).
- عربي: سوابق الإلصاق (و، ف، ب، ل، ك، ال) + لواحق شائعة (ات، ون، ين، ية…)،
  لكن لا سوابق فعلية (ي، ت، ن) — فتطابق «قتلى» و«بالقتل» ولا تطابق «يقتلع».
- `*` في آخر الكلمة = مطابقة بادئة صريحة (`enrich*` ← enriched/enrichment).

كل الكلمات تُطبَّع بـ`normalize_for_match` قبل الترجمة، والنص كذلك قبل الفحص.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from .normalize import normalize_for_match

_ARABIC_CHAR_RE = re.compile(r"[؀-ۿ]")

# سوابق الإلصاق العربية: حرف عطف اختياري، ثم حرف جر اختياري، ثم "ال" أو "ل".
# (لل = ل + ال بعد حذف الألف، فتغطيها "ل" ثم "ل".)
_AR_PREFIX = r"(?:[وف])?(?:[بلك])?(?:ال|ل)?"
# لواحق شائعة بعد التطبيع (ة→ه، ى→ي). الأطول أولًا.
_AR_SUFFIX = r"(?:يات|يون|يين|ات|ون|ين|ان|يه|يا|ها|هم|هن|نا|ه|ي|ا)?"
_EN_SUFFIX = r"(?:s|es|ed|d|ing|'s)?"
_BOUNDARY_START = r"(?<![\w])"
_BOUNDARY_END = r"(?![\w])"


def _term_pattern(term: str) -> str:
    raw = normalize_for_match(term)
    prefix_match = raw.endswith("*")
    raw = raw.rstrip("*").strip()
    is_arabic = bool(_ARABIC_CHAR_RE.search(raw))
    if is_arabic and raw.startswith("ال") and len(raw) > 4:
        # «ال» تُغطّيها السوابق؛ إبقاؤها في الجسم يُفشل «للطاقة» (ل + ال بلا ألف)
        raw = raw[2:]
    body = r"\s+".join(re.escape(part) for part in raw.split(" "))

    if prefix_match:
        tail = r"\w*"
    elif is_arabic:
        tail = _AR_SUFFIX
    elif raw[-1:].isalpha():
        tail = _EN_SUFFIX
    else:  # ينتهي برقم أو رمز ("60%"، "cobalt 60")
        tail = ""

    head = _AR_PREFIX if is_arabic else ""
    end = _BOUNDARY_END if raw[-1:].isalnum() or prefix_match else ""
    return f"{_BOUNDARY_START}{head}{body}{tail}{end}"


@dataclass(frozen=True)
class Hit:
    term: str
    start: int
    end: int


class KeywordSet:
    """مجموعة كلمات مفتاحية مُترجمة مسبقًا إلى تعبيرات نمطية.

    `search` تعيد كل المطابقات بمواضعها (للترتيب والاستبعاد)، و`matches`
    فحص وجود سريع. النص المُمرَّر يجب أن يكون مُطبَّعًا (`normalize_for_match`).
    """

    def __init__(self, terms: Iterable[str]):
        self.terms: tuple[str, ...] = tuple(dict.fromkeys(t for t in terms if t and t.strip()))
        self._compiled = [(t, re.compile(_term_pattern(t))) for t in self.terms]

    def __len__(self) -> int:
        return len(self.terms)

    def search(self, norm_text: str) -> list[Hit]:
        hits: list[Hit] = []
        for term, rx in self._compiled:
            for m in rx.finditer(norm_text):
                hits.append(Hit(term, m.start(), m.end()))
        hits.sort(key=lambda h: h.start)
        return hits

    def matches(self, norm_text: str) -> bool:
        return any(rx.search(norm_text) for _, rx in self._compiled)

    def count(self, norm_text: str) -> int:
        """عدد المقاطع المطابِقة غير المتداخلة، مع تفضيل الأطول.

        «هيئة الرقابة النووية والإشعاعية» تحوي «الرقابة النووية» و«هيئة
        الرقابة»؛ عدّها ثلاث مطابقات كان يضخّم موضوعًا لمجرد ذكر اسم جهة.
        """
        hits = sorted(self.search(norm_text), key=lambda h: (-(h.end - h.start), h.start))
        taken: list[tuple[int, int]] = []
        for h in hits:
            if all(h.end <= s or h.start >= e for s, e in taken):
                taken.append((h.start, h.end))
        return len(taken)

    def matched_terms(self, norm_text: str) -> list[str]:
        return [t for t, rx in self._compiled if rx.search(norm_text)]


def mask_spans(norm_text: str, spans: Iterable[tuple[int, int]]) -> str:
    """يستبدل مقاطع النص بمسافات (يحفظ المواضع) — لإخراج عبارات مستبعدة من
    المطابقة، مثل «الحمض النووي» قبل البحث عن «نووي»."""
    chars = list(norm_text)
    for start, end in spans:
        for i in range(max(start, 0), min(end, len(chars))):
            chars[i] = " "
    return "".join(chars)


def strip_phrases(norm_text: str, phrases: KeywordSet) -> tuple[str, list[str]]:
    """يُخفي العبارات المطابِقة ويعيد (النص المُنقّى، العبارات التي أُخفيت)."""
    hits = phrases.search(norm_text)
    if not hits:
        return norm_text, []
    return mask_spans(norm_text, [(h.start, h.end) for h in hits]), [h.term for h in hits]
