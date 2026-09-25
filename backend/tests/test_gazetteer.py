"""رصد - اختبارات تحديد الموقع والمسافة إلى المملكة."""
import pytest

from app.processors.gazetteer import locate, nearest_ksa_point
from app.processors.text_analysis import geolocate


class TestLocate:
    def test_target_country_wins_over_first_mentioned(self):
        """كانت IL تُختار لأنها تسبق IR في القاموس؛ الآن لأنها الهدف ("at")."""
        assert locate("Iran fires missiles at Israel").country_code == "IL"

    def test_first_mention_when_no_target_preposition(self):
        assert locate("Iran foreign minister meets Saudi counterpart").country_code == "IR"

    @pytest.mark.parametrize("title,code", [
        ("Oman hosts US-Iran talks", "OM"),
        ("عمان تستضيف محادثات", "OM"),
        ("Drone intercepted over Abu Dhabi", "AE"),
        ("انفجار في الدوحة", "QA"),
        ("الكويت تعلن حالة التأهب", "KW"),
        ("مناورات في البحرين", "BH"),
    ])
    def test_gulf_states_are_known(self, title, code):
        assert locate(title).country_code == code

    def test_amman_with_jordan_context_is_jordan(self):
        assert locate("اجتماع في عمان بحضور وزير خارجية الأردن").country_code == "JO"

    def test_city_precision(self):
        loc = locate("Explosion reported in Isfahan")
        assert (loc.country_code, loc.precision) == ("IR", "city")

    def test_facility_precision_uses_facility_coordinates(self):
        loc = locate("IAEA inspectors return to Fordow")
        assert loc.precision == "facility"
        assert loc.facility_id == "ir-fordow"
        assert round(loc.lat, 1) == 34.9

    def test_maritime_region_has_no_country(self):
        loc = locate("Tanker attacked in the Red Sea")
        assert (loc.country_code, loc.precision) == ("", "region")

    def test_leader_name_only_when_no_country_named(self):
        assert locate("نتنياهو: تدمير نووي إيران كان أسهل قراراتي").country_code == "IR"
        assert locate("نتنياهو يلتقي ترامب").country_code == "IL"

    @pytest.mark.parametrize("title", ["وُلد في مسقط رأسه", "القوة القاهرة تؤجل التسليم"])
    def test_idioms_are_not_places(self, title):
        assert locate(title).precision == "none"

    def test_legacy_wrapper(self):
        code, name, lat, lon = geolocate("Explosions reported in Gaza")
        assert code == "PS" and lat is not None


class TestKsaDistance:
    def test_inside_the_kingdom_is_near_zero(self):
        dist, name = nearest_ksa_point(26.43, 50.10)
        assert dist < 5 and name == "الدمام"

    def test_bushehr_is_within_300km(self):
        dist, _ = nearest_ksa_point(28.829, 50.886)
        assert 200 < dist < 300

    def test_no_coordinates(self):
        assert nearest_ksa_point(None, None) is None
