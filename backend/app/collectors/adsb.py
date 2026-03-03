"""رصد - جامع بيانات الطيران ADS-B
يتتبع الرحلات الجوية فوق الشرق الأوسط عبر adsb.lol (مجاني بدون مفتاح)
مع كشف الطائرات العسكرية
"""
import httpx
import logging
from datetime import datetime, timezone
from typing import Dict, Optional
from ..models.database import FlightTrack, get_session_factory

logger = logging.getLogger("rasad.adsb")

ADSB_API = "https://api.adsb.lol/v2/lat/29/lon/42/dist/2000"

MILITARY_ICAO_PREFIXES = {
    "AE": "US Military", "AF": "US Military",
    "43C": "UK Military",
    "155": "Russian Military",
    "3A": "French Military", "3B": "French Military",
    "738": "Israeli Military",
    "4B8": "Turkish Military",
    "710": "Saudi Military",
    "730": "Iranian Military",
    "700": "Egyptian Military",
}

MILITARY_CALLSIGN_PATTERNS = [
    "RCH", "REACH", "DUKE", "EVAC", "NAVY", "HRKN", "RRR",
    "CASA", "IAF", "TUAF", "RSF", "IRAN", "FORTE", "JAKE", "HOMER",
]

MILITARY_SQUAWKS = ["7700", "7600", "7500", "0021", "0022", "0023"]
MILITARY_AIRCRAFT_TYPES = ["F16", "F15", "F35", "F18", "B52", "C130", "C17", "E3", "P8", "RC135", "U2"]


async def collect_flights() -> Dict:
    """جمع بيانات الطيران فوق الشرق الأوسط"""
    session_factory = get_session_factory()
    flights_data = {"total": 0, "military": 0, "flights": []}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(ADSB_API)

            if response.status_code == 429:
                logger.warning("adsb.lol: rate limit reached")
                return flights_data

            if response.status_code != 200:
                logger.warning(f"adsb.lol returned {response.status_code}")
                return flights_data

            data = response.json()
            aircraft_list = data.get("ac", [])
            if not aircraft_list:
                return flights_data

            flights_data["total"] = len(aircraft_list)
            now = datetime.now(timezone.utc)
            parsed = []

            for ac in aircraft_list:
                try:
                    flight = _parse_aircraft(ac)
                    if flight:
                        parsed.append(flight)
                        if flight["is_military"]:
                            flights_data["military"] += 1
                except Exception:
                    continue

            flights_data["flights"] = parsed

            if session_factory:
                try:
                    async with session_factory() as session:
                        for flight in parsed:
                            if flight["is_military"]:
                                track = FlightTrack(
                                    icao24=flight["icao24"],
                                    callsign=flight["callsign"],
                                    origin_country=flight["origin_country"],
                                    latitude=flight["latitude"],
                                    longitude=flight["longitude"],
                                    altitude=flight["altitude"],
                                    velocity=flight["velocity"],
                                    heading=flight["heading"],
                                    vertical_rate=flight.get("vertical_rate"),
                                    on_ground=flight["on_ground"],
                                    is_military=True,
                                    aircraft_type=flight.get("military_type", ""),
                                    squawk=flight.get("squawk", ""),
                                    tracked_at=now,
                                )
                                session.add(track)
                        await session.commit()
                except Exception as e:
                    logger.warning(f"DB save error: {e}")

    except Exception as e:
        logger.error(f"خطأ في جمع بيانات الطيران: {e}")

    logger.info(f"ADS-B: {flights_data['total']} رحلة ({flights_data['military']} عسكرية)")
    return flights_data


def _parse_aircraft(ac: dict) -> Optional[Dict]:
    lat = ac.get("lat")
    lon = ac.get("lon")
    if lat is None or lon is None:
        return None

    icao24 = ac.get("hex", "")
    callsign = (ac.get("flight") or "").strip()
    origin_country = ac.get("ownOp") or _country_from_icao(icao24)
    altitude = ac.get("alt_baro") or ac.get("alt_geom")
    if isinstance(altitude, (int, float)):
        altitude = round(altitude * 0.3048)
    velocity = ac.get("gs")
    if isinstance(velocity, (int, float)):
        velocity = round(velocity * 0.514444, 1)
    heading = ac.get("track") or ac.get("true_heading") or 0
    vertical_rate = ac.get("baro_rate") or ac.get("geom_rate")
    squawk = ac.get("squawk") or ""
    on_ground = ac.get("alt_baro") == "ground"
    aircraft_type = ac.get("t", "")

    is_military = False
    military_type = ""

    for prefix, mil_type in MILITARY_ICAO_PREFIXES.items():
        if icao24.upper().startswith(prefix):
            is_military = True
            military_type = mil_type
            break

    if callsign:
        for pattern in MILITARY_CALLSIGN_PATTERNS:
            if pattern in callsign.upper():
                is_military = True
                military_type = military_type or f"Military ({pattern})"
                break

    if squawk in MILITARY_SQUAWKS:
        is_military = True

    if aircraft_type.upper() in MILITARY_AIRCRAFT_TYPES:
        is_military = True
        military_type = military_type or f"Military ({aircraft_type})"

    return {
        "icao24": icao24,
        "callsign": callsign,
        "origin_country": origin_country,
        "latitude": lat,
        "longitude": lon,
        "altitude": altitude,
        "on_ground": on_ground,
        "velocity": velocity,
        "heading": heading,
        "vertical_rate": vertical_rate,
        "squawk": squawk,
        "is_military": is_military,
        "military_type": military_type,
        "aircraft_type": aircraft_type,
    }


def _country_from_icao(icao24: str) -> str:
    icao = icao24.upper()
    prefixes = {
        "738": "Israel", "710": "Saudi Arabia", "730": "Iran",
        "740": "Iraq", "760": "Jordan", "750": "Syria",
        "896": "UAE", "4B": "Turkey", "AE": "United States",
        "3A": "France", "3C": "Germany", "4C": "United Kingdom",
    }
    for prefix, country in prefixes.items():
        if icao.startswith(prefix):
            return country
    return "Unknown"


async def get_live_flights() -> Dict:
    return await collect_flights()
