"""رصد - تحويل التواريخ المشترك بين الجامعين.

مصدر واحد لكل صيغ التاريخ التي نستقبلها من المصادر. كلها تعيد datetime
**واعياً بالمنطقة الزمنية** (UTC): خلط الواعي بغير الواعي يرفع TypeError عند
المقارنة في طبقة API.
"""
from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """الوقت الحالي بـ UTC (واعٍ بالمنطقة الزمنية)."""
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    """يضمن أن التاريخ واعٍ بالمنطقة الزمنية — يفترض UTC للتواريخ العارية."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def parse_entry_date(entry) -> datetime:
    """تاريخ مدخل feedparser (`published_parsed` / `updated_parsed`)."""
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if parsed:
        try:
            from time import mktime

            return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
        except (TypeError, ValueError, OverflowError):
            pass
    return utcnow()


def parse_iso(value: str | None) -> datetime:
    """تاريخ ISO-8601 (NewsAPI) — يقبل اللاحقة Z."""
    if value:
        try:
            return _as_utc(datetime.fromisoformat(str(value).replace("Z", "+00:00")))
        except (ValueError, TypeError):
            pass
    return utcnow()


def parse_compact(value: str | None) -> datetime:
    """تاريخ GDELT المضغوط `YYYYMMDDHHMMSS`."""
    if value:
        try:
            return datetime.strptime(str(value)[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            pass
    return utcnow()


def parse_ymd(value) -> datetime:
    """تاريخ `YYYY-MM-DD` (UCDP)."""
    if value:
        try:
            return datetime.strptime(str(value)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            pass
    return utcnow()
