"""رصد - رفض الطلبات التي لا تحمل اسم مضيف معروفًا في ترويسة Host.

الخادم بلا مصادقة على `127.0.0.1`، وCORS لا يحميه من **DNS rebinding**: صفحة على
`attacker.example` تعيد توجيه نطاقها إلى 127.0.0.1 بعد التحميل، فتصير طلباتها إلى
`attacker.example:8000` من الأصل نفسه في نظر المتصفح — تقرأ الردود وترسل
`X-Rasad-Client`. الشيء الوحيد الذي لا تستطيع تزويره هو `Host: attacker.example`.

ليست `starlette.middleware.trustedhost`: تلك تقسم الترويسة عند أول «:» فيصير
`[::1]:8000` المضيفَ `[` ويُرفض الوصول عبر IPv6 المحلي.
"""
from __future__ import annotations

from collections.abc import Iterable

from starlette.datastructures import Headers
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send


def host_of(header: str) -> str:
    """اسم المضيف من ترويسة Host بلا المنفذ: `[::1]:8000` ← `::1`."""
    value = header.strip().lower()
    if value.startswith("["):
        end = value.find("]")
        return value[1:end] if end != -1 else ""
    if value.count(":") == 1:
        return value.split(":", 1)[0]
    return value


class TrustedHostMiddleware:
    """يقبل المضيفات المطابقة حرفيًا أو بنمط `*.example.com`؛ "*" يعطّل الفحص."""

    def __init__(self, app: ASGIApp, allowed_hosts: Iterable[str]) -> None:
        hosts = [h.strip().lower() for h in allowed_hosts if h.strip()]
        self.app = app
        self.allow_any = "*" in hosts
        self.exact = frozenset(h for h in hosts if not h.startswith("*."))
        self.suffixes = tuple(h[1:] for h in hosts if h.startswith("*."))

    def allowed(self, host: str) -> bool:
        return host in self.exact or bool(self.suffixes and host.endswith(self.suffixes))

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self.allow_any or scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        if self.allowed(host_of(Headers(scope=scope).get("host", ""))):
            await self.app(scope, receive, send)
            return
        await PlainTextResponse("Invalid host header", status_code=400)(scope, receive, send)
