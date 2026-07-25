"""
رصد - حماية العمليات المكلفة بمفتاح API اختياري.

الوضع الافتراضي (تشغيل محلي / تطبيق سطح المكتب): `API_KEY` فارغ فلا مصادقة —
لا نُعقّد تجربة المستخدم الشخصي. عند النشر على شبكة، ضبط `API_KEY` في `.env`
يجعل النقاط المحمية تتطلّب الترويسة `X-API-Key`.

يُقارَن المفتاح بـ `secrets.compare_digest` لتفادي تسريب المعلومات عبر توقيت
المقارنة.
"""
from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, status

from .config import get_settings


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """تبعية FastAPI: تسمح بالمرور إن لم يُضبط مفتاح، وإلا تفرض تطابقه."""
    expected = get_settings().api_key
    if not expected:
        return

    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="مفتاح API غير صالح أو مفقود (الترويسة X-API-Key)",
            headers={"WWW-Authenticate": "ApiKey"},
        )
