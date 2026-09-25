"""رصد - جامع بيانات GDELT
يجمع الأحداث من مشروع GDELT كل 15 دقيقة
GDELT يراقب الأخبار العالمية ويحولها لأحداث مصنفة جغرافياً
"""
import logging

import httpx

from ..models.database import get_session_factory, insert_event_if_new
from ..processors.dates import parse_compact
from ..processors.gazetteer import COUNTRY_BY_CODE, COUNTRY_COORDS
from ._feed_base import analyzed_fields, clean_title

logger = logging.getLogger("rasad.gdelt")

GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"


async def collect_gdelt_events() -> int:
    """جمع الأحداث من GDELT API"""
    count = 0
    session_factory = get_session_factory()
    if not session_factory:
        logger.error("قاعدة البيانات غير مهيأة")
        return 0

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # جلب أحداث الشرق الأوسط
            params = {
                # المفردات النووية/الإشعاعية ضمن الاستعلام نفسه: GDELT يحدّ
                # الطلبات (نحو طلب كل 5 ثوانٍ)، فاستعلام ثانٍ يعني انتظارًا.
                "query": (
                    "(middleeast OR gaza OR israel OR yemen OR syria OR lebanon OR iran "
                    "OR iaea OR uranium OR radioactive OR barakah OR bushehr)"
                ),
                "mode": "artlist",
                "maxrecords": 75,
                "format": "json",
                "sort": "datedesc",
                "timespan": "4hours",
            }

            response = await client.get(GDELT_DOC_API, params=params)

            if response.status_code != 200:
                # نرفع ولا نعيد 0: GDELT يردّ 429 عند تجاوز الحصة، وابتلاعه
                # كان يجعل جامعًا مخنوقًا يبدو "بلا أخبار جديدة" في
                # /api/collectors/status و/api/refresh معًا.
                raise RuntimeError(f"GDELT: HTTP {response.status_code}")

            data = response.json()
            articles = data.get("articles", [])

            async with session_factory() as session:
                for article in articles:
                    try:
                        source_id = f"gdelt_{(article.get('url') or '')[:200]}"
                        title, _ = clean_title(article.get("title") or "")
                        if not title:
                            continue

                        # ملاحظة: GDELT artlist لا يعيد وصفاً — نترك الوصف فارغاً بدل
                        # حشو حقل الوصف بطابع seendate الزمني (BUG-1).
                        fields, analysis = analyzed_fields(
                            title,
                            extra={
                                "domain": article.get("domain", ""),
                                "source_name": article.get("domain", ""),
                                "language": article.get("language", ""),
                                "tone": article.get("tone", ""),
                            },
                        )
                        _fallback_to_source_country(fields, article.get("sourcecountry", ""))

                        inserted = await insert_event_if_new(
                            session,
                            source="gdelt",
                            source_id=source_id,
                            title=title,
                            description="",
                            url=article.get("url", ""),
                            image_url=article.get("socialimage", ""),
                            location_name=analysis.location.place_name or article.get("sourcecountry", ""),
                            event_date=parse_compact(article.get("seendate")),
                            **fields,
                        )
                        if inserted:
                            count += 1

                    except Exception as e:
                        logger.error(f"خطأ في معالجة مقال GDELT: {e}")
                        continue

                await session.commit()

    except Exception as e:
        # نرفع بعد التسجيل كي يُميّز /api/collectors/status و/api/refresh فشلاً
        # حقيقياً من "لا جديد" (كان يُعيد 0 صامتاً فيبدو الجامع المعطّل هادئاً).
        logger.error(f"خطأ في جمع بيانات GDELT: {e}")
        raise

    logger.info(f"GDELT: تم جمع {count} حدث جديد")
    return count


# اسم الدولة كما يكتبه GDELT في sourcecountry → رمز ISO. كان الرمز يُشتقّ
# بأول حرفين من الاسم ("Israel" → "IS" = آيسلندا، "Iran" → "IR" صدفةً).
_GDELT_COUNTRY_CODES = {c.name_en.lower(): c.code for c in COUNTRY_BY_CODE.values()}
_GDELT_COUNTRY_CODES.update({"turkey": "TR", "west bank": "PS", "gaza strip": "PS"})


def gdelt_country_code(source_country: str) -> str:
    return _GDELT_COUNTRY_CODES.get((source_country or "").strip().lower(), "")


def _fallback_to_source_country(fields: dict, source_country: str) -> None:
    """حين لا يذكر العنوان أي مكان، نستعمل بلد الناشر رمزًا فقط — بلا إحداثيات:
    بلد الصحيفة ليس مكان الحدث، ووضعه على الخريطة كان يضلّل."""
    if fields.get("country_code"):
        return
    code = gdelt_country_code(source_country)
    if code:
        fields["country_code"] = code
        fields["country"] = COUNTRY_COORDS[code][2]
