"""رصد - اختبارات جامع ADS-B: تحليل الطائرات وكشف العسكري وإزالة تكرار المسارات."""
from datetime import datetime, timedelta, timezone

import pytest

from app.collectors import adsb
from app.collectors.adsb import _haversine_km, _parse_aircraft, _prune_recorded, _should_record


@pytest.fixture(autouse=True)
def _clear_track_memory():
    adsb._last_recorded.clear()
    yield
    adsb._last_recorded.clear()


class TestParseAircraft:
    def test_skips_aircraft_without_position(self):
        assert _parse_aircraft({"hex": "abc123"}) is None
        assert _parse_aircraft({"hex": "abc", "lat": 30.0}) is None

    def test_converts_altitude_feet_to_metres(self):
        f = _parse_aircraft({"hex": "a1", "lat": 30.0, "lon": 40.0, "alt_baro": 10000})
        assert f["altitude"] == round(10000 * 0.3048)

    def test_converts_ground_speed_knots_to_ms(self):
        f = _parse_aircraft({"hex": "a1", "lat": 30.0, "lon": 40.0, "gs": 100})
        assert f["velocity"] == pytest.approx(51.4, abs=0.1)

    def test_detects_ground_state(self):
        f = _parse_aircraft({"hex": "a1", "lat": 30.0, "lon": 40.0, "alt_baro": "ground"})
        assert f["on_ground"] is True

    def test_military_by_icao_prefix(self):
        f = _parse_aircraft({"hex": "AE1234", "lat": 30.0, "lon": 40.0})
        assert f["is_military"] is True
        assert f["military_type"] == "US Military"

    def test_military_by_callsign_pattern(self):
        f = _parse_aircraft({"hex": "c01234", "lat": 30.0, "lon": 40.0, "flight": "RCH512 "})
        assert f["is_military"] is True

    def test_military_by_emergency_squawk(self):
        f = _parse_aircraft({"hex": "c01234", "lat": 30.0, "lon": 40.0, "squawk": "7700"})
        assert f["is_military"] is True

    def test_military_by_aircraft_type(self):
        f = _parse_aircraft({"hex": "c01234", "lat": 30.0, "lon": 40.0, "t": "F16"})
        assert f["is_military"] is True

    def test_civilian_stays_civilian(self):
        f = _parse_aircraft({"hex": "c01234", "lat": 30.0, "lon": 40.0, "flight": "UAE201", "t": "A388"})
        assert f["is_military"] is False

    def test_country_inferred_from_icao_when_owner_missing(self):
        f = _parse_aircraft({"hex": "738abc", "lat": 32.0, "lon": 35.0})
        assert f["origin_country"] == "Israel"

    def test_owner_operator_wins_over_icao_guess(self):
        f = _parse_aircraft({"hex": "738abc", "lat": 32.0, "lon": 35.0, "ownOp": "Some Airline"})
        assert f["origin_country"] == "Some Airline"

    def test_unknown_prefix_falls_back(self):
        f = _parse_aircraft({"hex": "zzzzzz", "lat": 32.0, "lon": 35.0})
        assert f["origin_country"] == "Unknown"


class TestHaversine:
    def test_zero_distance(self):
        assert _haversine_km(30.0, 40.0, 30.0, 40.0) == pytest.approx(0.0, abs=1e-9)

    def test_known_distance_one_degree_latitude(self):
        # درجة عرض واحدة ≈ 111 كم
        assert _haversine_km(30.0, 40.0, 31.0, 40.0) == pytest.approx(111.2, abs=1.0)


class TestShouldRecord:
    def _flight(self, lat=30.0, lon=40.0, icao="abc123"):
        return {"icao24": icao, "latitude": lat, "longitude": lon}

    def test_records_first_sighting(self, ):
        now = datetime.now(timezone.utc)
        assert _should_record(self._flight(), now) is True

    def test_skips_a_stationary_aircraft_on_the_next_poll(self):
        now = datetime.now(timezone.utc)
        assert _should_record(self._flight(), now) is True
        # بعد 30 ثانية بلا حركة تُذكر — لا صفّ جديد
        assert _should_record(self._flight(), now + timedelta(seconds=30)) is False

    def test_records_after_a_significant_move(self):
        now = datetime.now(timezone.utc)
        _should_record(self._flight(lat=30.0), now)
        # ~0.1 درجة ≈ 11 كم > عتبة 5 كم
        assert _should_record(self._flight(lat=30.1), now + timedelta(seconds=30)) is True

    def test_records_periodically_even_when_parked(self):
        now = datetime.now(timezone.utc)
        _should_record(self._flight(), now)
        assert _should_record(self._flight(), now + timedelta(seconds=601)) is True

    def test_tracks_each_aircraft_independently(self):
        now = datetime.now(timezone.utc)
        assert _should_record(self._flight(icao="aaa"), now) is True
        assert _should_record(self._flight(icao="bbb"), now) is True
        assert _should_record(self._flight(icao="aaa"), now + timedelta(seconds=5)) is False

    def test_ignores_flights_without_coordinates(self):
        now = datetime.now(timezone.utc)
        assert _should_record({"icao24": "x", "latitude": None, "longitude": None}, now) is False

    def test_prune_drops_aircraft_that_disappeared(self):
        now = datetime.now(timezone.utc)
        _should_record(self._flight(icao="gone"), now)
        assert "gone" in adsb._last_recorded
        _prune_recorded(now + timedelta(seconds=3601))
        assert "gone" not in adsb._last_recorded
