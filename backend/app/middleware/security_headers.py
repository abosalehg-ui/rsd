"""
رصد - ترويسات أمنية للصفحات التي يقدّمها الخادم نفسه.

في وضع سطح المكتب (PyInstaller) يُقدَّم `frontend/dist` من FastAPI مباشرة على
`http://127.0.0.1:8000`، ولا يمرّ بـ nginx، فكانت الصفحة تصل المتصفح بلا أي
ترويسة أمنية: لا `X-Frame-Options` (فيمكن وضع الأداة المحلية داخل iframe في
موقع خارجي) ولا `nosniff`. هذه الطبقة تضيفها للمسارات غير-`/api`.

**مصادر السياسة الثلاثة** — لكل هدف نشر نسخته، وأي تعديل يلزم في الثلاثة:
  1. هنا (وضع سطح المكتب / الخادم المُجمّع).
  2. `frontend/security-headers.conf` (نشر Docker عبر nginx).
  3. `<meta http-equiv>` في `frontend/index.html` (نشر GitHub Pages بلا خادم).

ملاحظة على `script-src`: بلا `'unsafe-inline'` ولا `'unsafe-eval'` — بناء Vite
الإنتاجي لا يُنتج سكربتات مضمّنة، ولا تستدعي three/globe.gl/leaflet `eval` ولا
`new Function` (مُتحقَّق منه على الحزم المبنية). أما `style-src 'unsafe-inline'`
فمطلوب فعلًا: Leaflet وReact يكتبان سمات `style` مباشرة على العناصر.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "img-src 'self' data: blob: https://*.basemaps.cartocdn.com https://unpkg.com; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' data: https://fonts.gstatic.com; "
    "connect-src 'self' https://*.basemaps.cartocdn.com https://unpkg.com; "
    "frame-src https://www.youtube-nocookie.com; "
    "worker-src 'self' blob:; "
    "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)

SECURITY_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=(), usb=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """يضيف ترويسات الأمان لاستجابات الصفحات (لا لمسارات `/api`).

    مسارات الـ API مستثناة: هي JSON يستهلكه العميل، وسياسة الصفحات لا تعنيها،
    كما أن `ETagCacheMiddleware` يعيد بناء استجاباتها.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            return response
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response
