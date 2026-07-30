"""رصد - جامع بيانات UCDP
جامعة أوبسالا لبيانات النزاعات - بديل مجاني عن ACLED
"""
import json
import logging

import httpx

from ..models.database import get_session_factory, insert_event_if_new
from ..processors.dates import parse_ymd
from ..processors.text_analysis import COUNTRY_COORDS, ME_COUNTRY_NAMES

logger = logging.getLogger("rasad.ucdp")

UCDP_API = "https://ucdpapi.pcr.uu.se/api/gedevents/24.1"

# اسم الدولة كما يكتبه UCDP → رمز ISO. الإحداثيات والاسم العربي يأتيان من
# `text_analysis` (مصدر واحد) بدل نسختين محليّتين هنا.
UCDP_COUNTRY_CODES = {
    "Palestine": "PS",
    "Israel": "IL",
    "Yemen (North Yemen)": "YE",
    "Syria": "SY",
    "Lebanon": "LB",
    "Iran": "IR",
    "Iraq": "IQ",
    "Saudi Arabia": "SA",
    "Egypt": "EG",
    "Turkey (Ottoman Empire)": "TR",
    "Libya": "LY",
    "Sudan": "SD",
}


async def collect_ucdp_events() -> int:
    """جمع أحداث النزاعات من UCDP"""
    count = 0
    session_factory = get_session_factory()
    if not session_factory:
        return 0

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # جلب أحداث الشرق الأوسط
            params = {
                "pagesize": 100,
                "page": 0,
            }

            response = await client.get(UCDP_API, params=params)

            if response.status_code != 200:
                logger.warning(f"UCDP API returned {response.status_code}")
                return 0

            data = response.json()
            events = data.get("Result", [])

            async with session_factory() as session:
                for event_data in events:
                    try:
                        country = event_data.get("country", "")
                        code = UCDP_COUNTRY_CODES.get(country)
                        if not code:
                            continue

                        event_id = event_data.get("id", "")
                        source_id = f"ucdp_{event_id}"

                        default_lat, default_lon, _ = COUNTRY_COORDS[code]
                        lat = event_data.get("latitude", default_lat)
                        lon = event_data.get("longitude", default_lon)

                        deaths_a = event_data.get("deaths_a", 0) or 0
                        deaths_b = event_data.get("deaths_b", 0) or 0
                        deaths_civilians = event_data.get("deaths_civilians", 0) or 0
                        total_deaths = deaths_a + deaths_b + deaths_civilians

                        severity = "low"
                        if total_deaths > 50:
                            severity = "critical"
                        elif total_deaths > 10:
                            severity = "high"
                        elif total_deaths > 0:
                            severity = "medium"

                        side_a = event_data.get("side_a", "")
                        side_b = event_data.get("side_b", "")
                        title = f"نزاع مسلح: {side_a} vs {side_b} - {country}"

                        # إدراج ذرّي مانع للتكرار — كبقية الجامعين. النمط
                        # السابق (SELECT ثم add) كان يُنفّذ استعلاماً لكل حدث
                        # ويترك سباقاً بين الجامع المجدول والتحديث اليدوي.
                        inserted = await insert_event_if_new(
                            session,
                            source="ucdp",
                            source_id=source_id,
                            title=title,
                            description=f"وفيات: {total_deaths} (مدنيون: {deaths_civilians})",
                            url=f"https://ucdp.uu.se/event/{event_id}",
                            category="military",
                            severity=severity,
                            latitude=float(lat) if lat else default_lat,
                            longitude=float(lon) if lon else default_lon,
                            country=ME_COUNTRY_NAMES.get(code, ""),
                            country_code=code,
                            location_name=event_data.get("where_description", ""),
                            event_date=parse_ymd(event_data.get("date_start")),
                            extra_data=json.dumps({
                                "deaths_total": total_deaths,
                                "deaths_civilians": deaths_civilians,
                                "side_a": side_a,
                                "side_b": side_b,
                                "type_of_violence": event_data.get("type_of_violence", ""),
                            }),
                        )
                        if inserted:
                            count += 1

                    except Exception as e:
                        logger.error(f"خطأ في حدث UCDP: {e}")
                        continue

                await session.commit()

    except Exception as e:
        logger.error(f"خطأ عام في UCDP: {e}")
        raise  # إشارة فشل صادقة بدل 0 صامت

    logger.info(f"UCDP: تم جمع {count} حدث نزاع جديد")
    return count
