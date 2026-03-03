"""رصد - جامع بيانات GDELT
يجمع الأحداث من مشروع GDELT كل 15 دقيقة
GDELT يراقب الأخبار العالمية ويحولها لأحداث مصنفة جغرافياً
"""
import httpx
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
from ..models.database import Event, get_session_factory

logger = logging.getLogger("rasad.gdelt")

# دول الشرق الأوسط
ME_COUNTRIES = {
    "SA": "السعودية", "AE": "الإمارات", "QA": "قطر", "KW": "الكويت",
    "BH": "البحرين", "OM": "عمان", "YE": "اليمن", "IQ": "العراق",
    "SY": "سوريا", "LB": "لبنان", "JO": "الأردن", "PS": "فلسطين",
    "IL": "إسرائيل", "EG": "مصر", "LY": "ليبيا", "SD": "السودان",
    "IR": "إيران", "TR": "تركيا",
}

# تصنيف أحداث GDELT للكاميو
CAMEO_CATEGORIES = {
    # عسكري/أمني
    "18": "military", "19": "military", "20": "military",
    "17": "military", "15": "military",
    # دبلوماسي
    "01": "diplomatic", "02": "diplomatic", "03": "diplomatic",
    "04": "diplomatic", "05": "diplomatic",
    # إنساني
    "06": "humanitarian", "07": "humanitarian", "08": "humanitarian",
    # اقتصادي
    "09": "economic", "10": "economic", "11": "economic",
    # تصعيدي
    "13": "military", "14": "military", "16": "military",
}

CAMEO_SEVERITY = {
    "18": "critical", "19": "critical", "20": "critical",
    "17": "high", "15": "high", "16": "high",
    "13": "high", "14": "high",
    "01": "low", "02": "low", "03": "low",
    "04": "medium", "05": "medium",
    "06": "medium", "07": "medium", "08": "medium",
    "09": "low", "10": "medium", "11": "medium",
}

GDELT_GEO_API = "https://api.gdeltproject.org/api/v2/geo/geo"
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

                        # تحقق من عدم التكرار
                        from sqlalchemy import select
                        existing = await session.execute(
                            select(Event).where(Event.source_id == source_id)
                        )
                        if existing.scalar_one_or_none():
                            continue

                        # تحديد التصنيف من العنوان
                        title = article.get("title", "")
                        category, severity = _classify_from_title(title)

                        # تحديد الدولة
                        country_code = _extract_country(title, article.get("sourcecountry", ""))

                        event = Event(
                            source="gdelt",
                            source_id=source_id,
                            title=title,
                            description=article.get("seendate", ""),
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

                        session.add(event)
                        count += 1

                    except Exception as e:
                        logger.error(f"خطأ في معالجة مقال GDELT: {e}")
                        continue

                await session.commit()

    except Exception as e:
        logger.error(f"خطأ في جمع بيانات GDELT: {e}")

    logger.info(f"GDELT: تم جمع {count} حدث جديد")
    return count


def _classify_from_title(title: str) -> tuple:
    """تصنيف الحدث من العنوان"""
    title_lower = title.lower()

    military_keywords = ["attack", "strike", "bomb", "missile", "military", "war", "troops",
                         "airstrike", "soldier", "combat", "drone", "هجوم", "قصف", "صاروخ",
                         "عسكري", "غارة", "طائرة مسيرة", "kill", "dead", "casualt"]
    nuclear_keywords = ["nuclear", "uranium", "atomic", "radiation", "نووي", "يورانيوم",
                        "إشعاع", "centrifuge", "enrichment", "iaea", "تخصيب"]
    diplomatic_keywords = ["diplomat", "negotiate", "peace", "treaty", "summit", "un ",
                           "united nations", "ceasefire", "دبلوماسي", "مفاوضات", "سلام",
                           "هدنة", "وقف إطلاق", "اتفاق"]
    humanitarian_keywords = ["humanitarian", "refugee", "aid", "civilian", "displaced",
                             "إنساني", "لاجئ", "مساعدات", "نازح", "إغاثة"]

    if any(kw in title_lower for kw in nuclear_keywords):
        return "nuclear", "high"
    if any(kw in title_lower for kw in military_keywords):
        return "military", "high"
    if any(kw in title_lower for kw in diplomatic_keywords):
        return "diplomatic", "medium"
    if any(kw in title_lower for kw in humanitarian_keywords):
        return "humanitarian", "medium"

    return "general", "low"


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
