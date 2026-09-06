"""
رصد - حماية العمليات المكلفة: حارس CSRF + مفتاح API اختياري.

طبقتان مستقلّتان على النقاط المكلفة (`POST /api/refresh`):

1. **حارس CSRF (دائم).** الترويسة `X-Rasad-Client` مطلوبة دائمًا. الترويسة
   المخصّصة ليست "بسيطة" بمعنى CORS، فالمتصفح يُلزَم بطلب preflight قبلها
   ويرفضه الخادم لأي أصل خارج `CORS_ORIGINS`. بدونها كانت أي صفحة يزورها
   المستخدم تستطيع إرسال `POST` عبر الأصول إلى `127.0.0.1:8000` فتُطلق خمسة
   جامعين خارجيين على جهازه — CORS يمنع *قراءة* الرد لا *إرساله*.

2. **مفتاح API (اختياري).** `API_KEY` فارغ = معطّل (تشغيل محلي/سطح مكتب)،
   وعند ضبطه تُفرض الترويسة `X-API-Key` ويُقارَن بـ `secrets.compare_digest`
   لتفادي تسريب المعلومات عبر توقيت المقارنة.
"""
from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, status

from .config import get_settings

#: قيمة الترويسة لا تحمل أي سرّ — وجودها وحده هو ما يُلزم المتصفح بـ preflight.
CLIENT_HEADER = "X-Rasad-Client"


async def require_api_key(
    x_api_key: str | None = Header(default=None),
    x_rasad_client: str | None = Header(default=None),
) -> None:
    """تبعية FastAPI للنقاط المكلفة: حارس CSRF ثم مفتاح API إن كان مضبوطًا."""
    if not x_rasad_client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"طلب مرفوض — الترويسة {CLIENT_HEADER} مطلوبة",
        )

    expected = get_settings().api_key
    if not expected:
        return

    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="مفتاح API غير صالح أو مفقود (الترويسة X-API-Key)",
            headers={"WWW-Authenticate": "ApiKey"},
        )
