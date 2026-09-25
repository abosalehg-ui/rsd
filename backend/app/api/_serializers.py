"""رصد - تحويل نماذج قاعدة البيانات إلى JSON.

أساس مشترك لكل الأحداث + امتداد إيراني فوقه يضيف الثقة والفيديو، كي لا
تتباعد نسختا التسلسل في `events.py` و`iran.py`.

العنوان والوصف يمرّان عبر `clean_text` عند الإخراج أيضًا: الصفوف المخزّنة قبل
إصلاح الجامعين تحمل `&quot;` و`<b>` خامًا، وتنظيفها هنا يصلح عرضها دون ترحيل.
"""
from __future__ import annotations

import json

from ..models.database import Event
from ..processors.normalize import clean_text


def _extra(event: Event) -> dict:
    """فكّ حقل extra_data المخزّن كنص JSON — يعيد {} عند التلف."""
    if not event.extra_data:
        return {}
    try:
        parsed = json.loads(event.extra_data)
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def serialize_event(event: Event) -> dict:
    """التمثيل القياسي لحدث."""
    extra = _extra(event)
    nuclear = extra.get("nuclear") if isinstance(extra.get("nuclear"), dict) else None
    return {
        "id": event.id,
        "source": event.source,
        "title": clean_text(event.title),
        "description": clean_text(event.description),
        "url": event.url,
        "image_url": event.image_url,
        "category": event.category,
        "severity": event.severity,
        "latitude": event.latitude,
        "longitude": event.longitude,
        "country": event.country,
        "country_code": event.country_code,
        "location_name": event.location_name,
        "event_date": event.event_date.isoformat() if event.event_date else None,
        "geo_precision": event.geo_precision or extra.get("geo_precision") or (
            "country" if event.latitude is not None else "none"
        ),
        "topic": event.topic,
        "risk_score": event.risk_score,
        "facility_id": event.facility_id,
        "cluster_id": event.cluster_id or event.id,
        "source_name": extra.get("source_name") or extra.get("feed_name") or event.source,
        "nuclear": nuclear,
        "extra": extra,
    }


def serialize_iran_event(event: Event) -> dict:
    """تمثيل حدث إيران OSINT — الأساس + حقول الثقة والفيديو والنوع."""
    extra = _extra(event)
    return {
        **serialize_event(event),
        "video_url": event.video_url,
        "confidence": event.confidence,
        "confidence_icon": extra.get("confidence_icon", "🔵"),
        "event_type": event.event_type,
        "feed_name": extra.get("feed_name", ""),
    }
