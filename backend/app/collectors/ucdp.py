"""رصد - جامع بيانات UCDP
جامعة أوبسالا لبيانات النزاعات - بديل مجاني عن ACLED
"""
import httpx
import json
import logging
from datetime import datetime, timezone
from ..models.database import Event, get_session_factory

logger = logging.getLogger("rasad.ucdp")

UCDP_API = "https://ucdpapi.pcr.uu.se/api/gedevents/24.1"

# دول الشرق الأوسط
ME_COUNTRY_IDS = {
    "Palestine": ("PS", 31.5, 34.47),
    "Israel": ("IL", 31.77, 35.23),
    "Yemen (North Yemen)": ("YE", 15.55, 48.52),
    "Syria": ("SY", 34.8, 38.99),
    "Lebanon": ("LB", 33.87, 35.51),
    "Iran": ("IR", 35.69, 51.39),
    "Iraq": ("IQ", 33.31, 44.37),
    "Saudi Arabia": ("SA", 24.71, 46.68),
    "Egypt": ("EG", 30.04, 31.24),
    "Turkey (Ottoman Empire)": ("TR", 39.93, 32.86),
    "Libya": ("LY", 32.9, 13.18),
    "Sudan": ("SD", 15.59, 32.53),
}

ME_COUNTRY_NAMES = {
    "PS": "فلسطين", "IL": "إسرائيل", "YE": "اليمن", "SY": "سوريا",
    "LB": "لبنان", "IR": "إيران", "IQ": "العراق", "SA": "السعودية",
    "EG": "مصر", "TR": "تركيا", "LY": "ليبيا", "SD": "السودان",
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
                        if country not in ME_COUNTRY_IDS:
                            continue

                        event_id = event_data.get("id", "")
                        source_id = f"ucdp_{event_id}"

                        from sqlalchemy import select
                        existing = await session.execute(
                            select(Event).where(Event.source_id == source_id)
                        )
                        if existing.scalar_one_or_none():
                            continue

                        country_info = ME_COUNTRY_IDS[country]
                        lat = event_data.get("latitude", country_info[1])
                        lon = event_data.get("longitude", country_info[2])

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

                        event = Event(
                            source="ucdp",
                            source_id=source_id,
                            title=title,
                            description=f"وفيات: {total_deaths} (مدنيون: {deaths_civilians})",
                            url=f"https://ucdp.uu.se/event/{event_id}",
                            category="military",
                            severity=severity,
                            latitude=float(lat) if lat else country_info[1],
                            longitude=float(lon) if lon else country_info[2],
                            country=ME_COUNTRY_NAMES.get(country_info[0], ""),
                            country_code=country_info[0],
                            location_name=event_data.get("where_description", ""),
                            event_date=_parse_date(event_data.get("date_start")),
                            extra_data=json.dumps({
                                "deaths_total": total_deaths,
                                "deaths_civilians": deaths_civilians,
                                "side_a": side_a,
                                "side_b": side_b,
                                "type_of_violence": event_data.get("type_of_violence", ""),
                            }),
                        )

                        session.add(event)
                        count += 1

                    except Exception as e:
                        logger.error(f"خطأ في حدث UCDP: {e}")
                        continue

                await session.commit()

    except Exception as e:
        logger.error(f"خطأ عام في UCDP: {e}")

    logger.info(f"UCDP: تم جمع {count} حدث نزاع جديد")
    return count


def _parse_date(date_str) -> datetime:
    if date_str:
        try:
            return datetime.strptime(str(date_str)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            pass
    return datetime.now(timezone.utc)
