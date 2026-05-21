"""
رصد - ETag + Cache-Control middleware (v1.4)

- يحسب SHA-1 ضعيف للجواب ويضعه في ETag.
- يستجيب 304 Not Modified عند تطابق If-None-Match.
- يضيف Cache-Control حسب المسار:
  * /api/infrastructure/* و /api/nuclear/facilities/* و /api/sources → public, max-age=3600
  * /api/events/stats و /api/events/country-index → public, max-age=60
  * بقية /api/events/* و /api/iran/* و /api/flights/* → no-cache (يجب revalidate)
"""
from __future__ import annotations

import hashlib

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# مدد التخزين المؤقت (ثواني) — مرتّبة بالأطول أولاً للحصول على المطابقة الأكثر تحديداً
_CACHE_RULES: list[tuple[str, str]] = [
    ("/api/infrastructure/", "public, max-age=3600, stale-while-revalidate=300"),
    ("/api/nuclear/facilities", "public, max-age=3600, stale-while-revalidate=300"),
    ("/api/sources", "public, max-age=3600"),
    ("/api/events/country-index", "public, max-age=60, stale-while-revalidate=30"),
    ("/api/events/stats", "public, max-age=60, stale-while-revalidate=30"),
    ("/api/events/", "public, max-age=15, must-revalidate"),
    ("/api/iran/", "public, max-age=30, must-revalidate"),
    ("/api/flights/", "public, max-age=15, must-revalidate"),
]


def _cache_control_for(path: str) -> str | None:
    for prefix, value in _CACHE_RULES:
        if path.startswith(prefix):
            return value
    return None


class ETagCacheMiddleware(BaseHTTPMiddleware):
    """يضيف ETag + Cache-Control للاستجابات GET على مسارات /api."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # فقط GET على مسارات API بحالة 200
        if request.method != "GET" or response.status_code != 200:
            return response
        if not request.url.path.startswith("/api/"):
            return response

        # نقرأ الجسم لحساب ETag (لاحظ: StreamingResponse يحتاج تجميع)
        body_chunks: list[bytes] = []
        async for chunk in response.body_iterator:
            body_chunks.append(chunk)
        body = b"".join(body_chunks)

        etag = 'W/"' + hashlib.sha1(body).hexdigest()[:16] + '"'
        if_none_match = request.headers.get("if-none-match")

        headers = dict(response.headers)
        headers["ETag"] = etag
        cc = _cache_control_for(request.url.path)
        if cc:
            headers["Cache-Control"] = cc
        # احذف Content-Length لأن Starlette سيعيد حسابها
        headers.pop("content-length", None)

        if if_none_match and if_none_match == etag:
            return Response(status_code=304, headers=headers)

        return Response(
            content=body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
        )
