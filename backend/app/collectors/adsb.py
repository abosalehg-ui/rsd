"""رصد - جامع بيانات الطيران ADS-B
يتتبع الرحلات الجوية فوق الشرق الأوسط عبر adsb.lol (مجاني بدون مفتاح)
مع كشف الطائرات العسكرية
"""
import logging
from datetime import datetime, timezone
from math import asin, cos, radians, sin, sqrt
from typing import Dict, Optional, Tuple

import httpx

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

# لقطة آخر جمع ناجح — تقرأها /flights/live بدل استدعاء المزوّد الخارجي والكتابة
# في DB عند كل طلب من كل عميل (PERF-1). تحدّثها الوظيفة المجدولة وحدها.
_last_snapshot: Dict = {"total": 0, "military": 0, "flights": [], "updated_at": None}

# إزالة تكرار كتابات المسارات: نسجّل صفّاً فقط عند حركة معتبرة أو بعد فجوة
# زمنية، بدل صفّ لكل طائرة كل 30 ثانية.
_MIN_MOVE_KM = 5.0
_MAX_GAP_SECONDS = 600      # 10 دقائق — نضمن نقطة دورية حتى للطائرة الواقفة
_TRACK_MEMORY_SECONDS = 3600

# icao24 → (آخر تسجيل، خط العرض، خط الطول)
_last_recorded: Dict[str, Tuple[datetime, float, float]] = {}


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
                await _persist_military_tracks(session_factory, parsed, now)

    except Exception as e:
        logger.error(f"خطأ في جمع بيانات الطيران: {e}")

    # حدّث اللقطة المشتركة (تقرأها /flights/live)
    _last_snapshot.update(
        total=flights_data["total"],
        military=flights_data["military"],
        flights=flights_data["flights"],
        updated_at=datetime.now(timezone.utc).isoformat(),
    )

    logger.info(f"ADS-B: {flights_data['total']} رحلة ({flights_data['military']} عسكرية)")
    return flights_data


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """المسافة بالكيلومترات بين نقطتين على سطح الأرض."""
    r = 6371.0
    p1, p2 = radians(lat1), radians(lat2)
    dp = radians(lat2 - lat1)
    dl = radians(lon2 - lon1)
    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * r * asin(sqrt(a))


def _should_record(flight: Dict, now: datetime) -> bool:
    """هل نُسجّل صفّاً جديداً لهذه الطائرة؟

    التسجيل عند كل دورة (30 ثانية) كان ينتج ~144 ألف صف يومياً لبيانات شبه
    ثابتة. نكتفي بصفّ عند تغيّر الموقع أكثر من `_MIN_MOVE_KM` أو مرور
    `_MAX_GAP_SECONDS` — يقلّص الحجم بأكثر من 90% مع الحفاظ على شكل المسار.
    """
    icao = flight["icao24"]
    lat, lon = flight["latitude"], flight["longitude"]
    if lat is None or lon is None:
        return False

    last = _last_recorded.get(icao)
    if last is None:
        _last_recorded[icao] = (now, lat, lon)
        return True

    last_at, last_lat, last_lon = last
    moved = _haversine_km(last_lat, last_lon, lat, lon)
    elapsed = (now - last_at).total_seconds()
    if moved >= _MIN_MOVE_KM or elapsed >= _MAX_GAP_SECONDS:
        _last_recorded[icao] = (now, lat, lon)
        return True
    return False


def _prune_recorded(now: datetime) -> None:
    """أسقط الطائرات التي اختفت — يمنع نمو ذاكرة التتبّع بلا حدود."""
    stale = [
        icao for icao, (seen_at, _, _) in _last_recorded.items()
        if (now - seen_at).total_seconds() > _TRACK_MEMORY_SECONDS
    ]
    for icao in stale:
        del _last_recorded[icao]


async def _persist_military_tracks(session_factory, parsed: list, now: datetime) -> None:
    """يحفظ مسارات الطائرات العسكرية التي تحرّكت فعلاً منذ آخر تسجيل."""
    try:
        to_save = [f for f in parsed if f["is_military"] and _should_record(f, now)]
        _prune_recorded(now)
        if not to_save:
            return

        async with session_factory() as session:
            for flight in to_save:
                session.add(FlightTrack(
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
                ))
            await session.commit()
    except Exception as e:
        logger.warning(f"DB save error: {e}")


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
    """يعيد آخر لقطة مُجمَّعة (من الوظيفة المجدولة) دون استدعاء المزوّد الخارجي
    أو الكتابة في DB — يمنع تضخيم الطلبات عبر العملاء المتعددين (PERF-1).

    عند عدم توفّر لقطة بعد (إقلاع بارد) نجمع مرة واحدة فقط."""
    if _last_snapshot["updated_at"] is None:
        return await collect_flights()
    return _last_snapshot
