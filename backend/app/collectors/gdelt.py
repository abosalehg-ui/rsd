"""رصد - جامع بيانات GDELT
يجمع الأحداث من مشروع GDELT كل 15 دقيقة
GDELT يراقب الأخبار العالمية ويحولها لأحداث مصنفة جغرافياً
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from ..models.database import get_session_factory, insert_event_if_new
from ..processors.text_analysis import ME_COUNTRY_NAMES as ME_COUNTRIES
from ..processors.text_analysis import classify

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
                "query": "middleeast OR gaza OR israel OR yemen OR syria OR lebanon OR iran",
                "mode": "artlist",
                "maxrecords": 50,
                "format": "json",
                "sort": "datedesc",
                "timespan": "4hours",
            }

            response = await client.get(GDELT_DOC_API, params=params)

            if response.status_code != 200:
                logger.warning(f"GDELT API returned {response.status_code}")
                return 0

            data = response.json()
            articles = data.get("articles", [])

            async with session_factory() as session:
                for article in articles:
                    try:
                        source_id = f"gdelt_{article.get('url', '')[:200]}"

                        # تحديد التصنيف من العنوان
                        title = article.get("title", "")
                        category, severity = classify(title)

                        # تحديد الدولة
                        country_code = _extract_country(title, article.get("sourcecountry", ""))

                        # ملاحظة: GDELT artlist لا يعيد وصفاً — نترك الوصف فارغاً بدل
                        # حشو حقل الوصف بطابع seendate الزمني (BUG-1).
                        inserted = await insert_event_if_new(
                            session,
                            source="gdelt",
                            source_id=source_id,
                            title=title,
                            description="",
                            url=article.get("url", ""),
                            image_url=article.get("socialimage", ""),
                            category=category,
                            severity=severity,
                            latitude=article.get("lat"),
                            longitude=article.get("lon"),
                            country=ME_COUNTRIES.get(country_code, ""),
                            country_code=country_code,
                            location_name=article.get("sourcelocation", ""),
                            event_date=_parse_date(article.get("seendate")),
                            extra_data=json.dumps({
                                "domain": article.get("domain", ""),
                                "language": article.get("language", ""),
                                "tone": article.get("tone", ""),
                            }),
                        )
                        if inserted:
                            count += 1

                    except Exception as e:
                        logger.error(f"خطأ في معالجة مقال GDELT: {e}")
                        continue

                await session.commit()

    except Exception as e:
        logger.error(f"خطأ في جمع بيانات GDELT: {e}")

    logger.info(f"GDELT: تم جمع {count} حدث جديد")
    return count


def _extract_country(title: str, source_country: str) -> str:
    """استخراج رمز الدولة"""
    country_keywords = {
        "gaza": "PS", "palestine": "PS", "فلسطين": "PS", "غزة": "PS",
        "israel": "IL", "إسرائيل": "IL",
        "yemen": "YE", "اليمن": "YE", "houthi": "YE", "حوثي": "YE",
        "syria": "SY", "سوريا": "SY",
        "lebanon": "LB", "لبنان": "LB", "hezbollah": "LB", "حزب الله": "LB",
        "iran": "IR", "إيران": "IR",
        "iraq": "IQ", "العراق": "IQ",
        "saudi": "SA", "السعودية": "SA",
        "egypt": "EG", "مصر": "EG",
        "jordan": "JO", "الأردن": "JO",
        "turkey": "TR", "تركيا": "TR",
        "libya": "LY", "ليبيا": "LY",
        "sudan": "SD", "السودان": "SD",
    }

    title_lower = title.lower()
    for keyword, code in country_keywords.items():
        if keyword in title_lower:
            return code

    return source_country[:2].upper() if source_country else ""


def _parse_date(date_str: Optional[str]) -> datetime:
    """تحويل تاريخ GDELT"""
    if date_str:
        try:
            return datetime.strptime(date_str[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            pass
    return datetime.now(timezone.utc)
