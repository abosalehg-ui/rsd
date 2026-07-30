"""
رصد - حدّ معدل بسيط لكل عنوان IP على مسارات /api

الـ API بلا حسابات مستخدمين، وبعض نقاطه مكلفة (استعلامات على نوافذ 720 ساعة،
أو بحث LIKE). هذا الحدّ يمنع استنزاف قاعدة البيانات من عميل واحد.

نافذة منزلقة في الذاكرة (deque من الطوابع الزمنية لكل IP) — بلا تبعية خارجية
ومناسبة لعملية واحدة. عند التشغيل بعدة عمّال أو خلف موازن حِمل استخدم
حدّاً على مستوى الوكيل العكسي بدلاً من هذا (أو إضافةً إليه).
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# لا نطبّق الحدّ على فحص الصحة كي لا تفشل healthchecks المتكرّرة
_EXEMPT_PATHS = frozenset({"/api/health"})

# سقف عدد العناوين المتتبَّعة — يمنع نمو الذاكرة بلا حدود تحت هجوم بعناوين منتحلة
_MAX_TRACKED_CLIENTS = 4096


class RateLimitMiddleware(BaseHTTPMiddleware):
    """يرفض ما يتجاوز `max_requests` طلباً خلال `window_seconds` بـ 429."""

    def __init__(
        self,
        app,
        max_requests: int = 120,
        window_seconds: int = 60,
        trust_proxy_headers: bool = False,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.trust_proxy_headers = trust_proxy_headers
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _client_key(self, request: Request) -> str:
        # X-Forwarded-For مُتحكَّم به من العميل ما لم نكن خلف وكيل موثوق يضبطه.
        # لا نقرأه إلا عند تفعيل trust_proxy_headers صراحةً، وإلا يستطيع عميل
        # مباشر انتحال IP مختلف لكل طلب فيتجاوز الحدّ ويُضخّم جدول التتبّع.
        if self.trust_proxy_headers:
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                # آخر إدخال يضيفه وكيلنا الموثوق هو IP النظير الفعلي
                return forwarded.split(",")[-1].strip()
        return request.client.host if request.client else "unknown"

    def _prune_tracked(self, now: float) -> None:
        """أسقط العناوين الخاملة، ثم أقدمها إن بقينا فوق السقف (حماية الذاكرة)."""
        stale = [ip for ip, hits in self._hits.items() if not hits or now - hits[-1] > self.window_seconds]
        for ip in stale:
            del self._hits[ip]
        # إن بقينا فوق السقف رغم إسقاط الخاملة (عناوين نشطة كثيرة)، أسقط الأقدم
        # نشاطاً حتى نعود للسقف — يضمن حدّاً فعلياً للذاكرة تحت هجوم موزّع.
        if len(self._hits) > _MAX_TRACKED_CLIENTS:
            oldest = sorted(self._hits.items(), key=lambda kv: kv[1][-1] if kv[1] else 0.0)
            for ip, _ in oldest[: len(self._hits) - _MAX_TRACKED_CLIENTS]:
                del self._hits[ip]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api/") or path in _EXEMPT_PATHS:
            return await call_next(request)

        now = time.monotonic()
        key = self._client_key(request)
        hits = self._hits[key]

        # أزل الطوابع الخارجة عن النافذة
        cutoff = now - self.window_seconds
        while hits and hits[0] < cutoff:
            hits.popleft()

        if len(hits) >= self.max_requests:
            retry_after = max(1, int(self.window_seconds - (now - hits[0])))
            return JSONResponse(
                status_code=429,
                content={"detail": f"تجاوزت حدّ الطلبات — أعد المحاولة بعد {retry_after} ثانية"},
                headers={"Retry-After": str(retry_after)},
            )

        hits.append(now)
        if len(self._hits) > _MAX_TRACKED_CLIENTS:
            self._prune_tracked(now)

        return await call_next(request)
