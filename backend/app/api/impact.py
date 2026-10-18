"""رصد - نقاط API لعدسة «الأثر على المملكة».

- `/ksa`      المؤشر العام مع اتجاهه وسلسلته الزمنية، والتوزيع حسب القطاع،
              والأحداث الأعلى أثرًا بمكوّناتها، وبنود «راقِب».
- `/sectors`  القطاعات ومعاملات المعادلة (لشرح المؤشر في الواجهة).

المؤشر بصيغة المؤشر النووي نفسها (60% أعلى أثر منفرد + 40% متوسط أعلى عشر
قصص)، محسوبًا على ممثّلي القصص: الخبر المكرّر من عشرة مصادر يُعدّ مرة.
بنود «راقِب» قاعدية لا مولَّدة: كل قطاع ارتفع مؤشره عن الفترة السابقة بـ
`WATCH_MIN_DELTA` نقطة فأكثر وبلغ `WATCH_MIN_INDEX`.

المنهجية الكاملة: docs/ksa-impact-methodology.md.
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from .. import cache
from ..config import get_settings
from ..processors.impact import SECTOR_KEYS
from ..processors.impact_index import (  # noqa: F401 - تُعاد تصديرها للتوافق
    INDEX_MAX_WEIGHT,
    INDEX_TOP_N,
    INDEX_TOP_WEIGHT,
    TREND_FLAT,
    trend_of,
)
from ..services.impact import (  # noqa: F401 - الخدمة مصدر المنطق؛ تُعاد هنا للتوافق
    TOP_EVENTS,
    WATCH_MIN_DELTA,
    WATCH_MIN_INDEX,
    build_ksa_impact,
    formula,
    watch_items,
)

router = APIRouter(prefix="/api/impact", tags=["impact"])

@router.get("/ksa")
async def ksa_impact(hours: int = Query(default=48, ge=1, le=720)):
    """مؤشر الأثر على المملكة (0-100) مع اتجاهه وقطاعاته وأعلى الأحداث أثرًا."""
    ttl = get_settings().response_cache_seconds
    return await cache.cached(("impact.ksa", hours), ttl, lambda: build_ksa_impact(hours))


@router.get("/sectors")
async def list_sectors():
    """القطاعات ومعاملات المعادلة — مرجع شرح المؤشر."""
    return {"sectors": list(SECTOR_KEYS), "formula": formula()}
