"""رصد - بيانات سلاسل الطاقة والأسواق وحساب التزامن (نقي، بلا قاعدة بيانات).

يشترك فيه الجامع (`collectors/markets`) ونقاط الـ API (`api/markets`)، فلا
تستورد طبقة الـ API من طبقة الجامعين.
"""
from __future__ import annotations

import math

#: السلاسل المجموعة بترتيب العرض. الأسماء المعروضة في ملفات الترجمة
#: (`markets.series.<code>`)؛ هنا الوحدة وحدها لأنها جزء من البيانات.
SERIES: dict[str, dict] = {
    "DCOILBRENTEU": {"unit": "USD/bbl"},
    "DCOILWTICO": {"unit": "USD/bbl"},
    "DHHNGSP": {"unit": "USD/MMBtu"},
    "VIXCLS": {"unit": "index"},
}
BRENT = "DCOILBRENTEU"

#: أقل عدد أيام مشتركة يُحسب عليه معامل الارتباط — دونه رقم بلا معنى
MIN_CORRELATION_DAYS = 10

# تباين أصغر من هذا (نسبةً لمربّع المقدار) = سلسلة ثابتة. المقارنة بالصفر
# الحرفي لا تكفي: خطأ التقريب في المتوسط يترك لسلسلة ثابتة مثل [23.4]*12
# تباينًا ضئيلًا غير صفري، فيخرج «0.0» (لا ارتباط) بدل «غير معرّف».
_REL_VARIANCE_EPS = 1e-12


def _is_constant(ss: float, n: int, mean: float) -> bool:
    return ss <= _REL_VARIANCE_EPS * n * max(1.0, mean * mean)


def pearson(xs: list[float], ys: list[float]) -> float | None:
    """معامل ارتباط بيرسون، أو None حين تقلّ الأيام أو تثبت إحدى السلسلتين."""
    n = len(xs)
    if n < MIN_CORRELATION_DAYS or n != len(ys):
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if _is_constant(sxx, n, mx) or _is_constant(syy, n, my):
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    r = round(sxy / math.sqrt(sxx * syy), 2)
    return r + 0.0          # يحوّل -0.0 إلى 0.0
