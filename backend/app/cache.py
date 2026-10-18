"""رصد - ذاكرة مؤقتة داخل العملية لنتائج النقاط الثقيلة.

`ETagCacheMiddleware` يوفّر النطاق الترددي فقط: يشغّل المعالج كاملًا ثم يقارن
البصمة. أما نقاط مثل التزامن والسلاسل والعدسة فتعيد الحساب ببايثون على حلقة
الأحداث في كل طلب (0.6 ثانية للتزامن على 60 ألف حدث)، والواجهة تستطلعها
دوريًا من كل تبويب مفتوح.

النتيجة تُحفظ بمفتاح (النقطة، المعاملات) مدة `RESPONSE_CACHE_SECONDS`، وتُبطَل
كلها عند تغيّر البيانات: نهاية دورة التحليل، وجمع الأسواق، والتنظيف. فالتأخير
الأقصى عن البيانات بعد كل كتابة صفر، وبين الكتابات مدة الصلاحية.

متغيّر عملية: يكفي لتطبيق سطح المكتب وuvicorn بعامل واحد.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable, Hashable

_store: dict[Hashable, tuple[float, Any]] = {}
# قفل لكل مفتاح: ثلاثة تبويبات تستطلع `/nuclear/risk` في اللحظة نفسها بعد
# انتهاء الصلاحية كانت تحسبه ثلاث مرات؛ الأول يحسب والبقية ينتظرون نتيجته.
_locks: dict[Hashable, asyncio.Lock] = {}
_MAX_ENTRIES = 256


def _fresh(key: Hashable, now: float):
    hit = _store.get(key)
    return hit if hit is not None and hit[0] > now else None


async def cached(key: Hashable, ttl: float, compute: Callable[[], Awaitable[Any]]) -> Any:
    """قيمة `key` من الذاكرة إن لم تنتهِ صلاحيتها، وإلا تُحسب مرة واحدة وتُحفظ."""
    if ttl <= 0:
        return await compute()
    hit = _fresh(key, time.monotonic())
    if hit is not None:
        return hit[1]
    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        now = time.monotonic()
        hit = _fresh(key, now)      # فحص ثانٍ: ربما حسبها من سبقنا إلى القفل
        if hit is not None:
            return hit[1]
        value = await compute()
        if len(_store) >= _MAX_ENTRIES:
            # المعاملات محدودة (ساعات/أيام/عتبة) فالسقف لا يُبلغ إلا بطلبات عابثة
            _store.clear()
            _locks.clear()
        _store[key] = (now + ttl, value)
        return value


def invalidate() -> None:
    """يُسقط كل النتائج المحفوظة — يُستدعى بعد كل كتابة تغيّر المؤشرات."""
    _store.clear()
