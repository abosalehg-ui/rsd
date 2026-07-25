"""رصد - اختبارات تصنيف أحداث إيران وتحديد مواقعها."""
from app.collectors.iran_osint import _classify_iran_event, _geolocate_iran, get_leaders_list


class TestClassifyIranEvent:
    def test_strike_keywords(self):
        assert _classify_iran_event("massive airstrike on the base") == ("strike", "military")

    def test_arabic_strike_keywords(self):
        subtype, category = _classify_iran_event("قصف على الموقع")
        assert (subtype, category) == ("strike", "military")

    def test_launch_when_no_strike_keyword_present(self):
        subtype, category = _classify_iran_event("sajjil test conducted")
        assert (subtype, category) == ("launch", "military")

    def test_movement(self):
        assert _classify_iran_event("irgc naval drills begin") == ("movement", "military")

    def test_nuclear(self):
        assert _classify_iran_event("iaea inspectors visit the site") == ("nuclear", "nuclear")

    def test_diplomatic(self):
        assert _classify_iran_event("new sanctions announced") == ("diplomatic", "diplomatic")

    def test_returns_none_pair_for_unrelated_text(self):
        # لا نُدرج الأخبار غير المصنّفة إطلاقاً — التوقيع يسمح بـ None صراحةً
        assert _classify_iran_event("local weather forecast") == (None, None)


class TestGeolocateIran:
    def test_specific_iranian_site_wins_over_country(self):
        lat, lon, name, code = _geolocate_iran("enrichment resumed at natanz in iran")
        assert code == "IR"
        assert name == "نطنز"
        assert (round(lat, 2), round(lon, 2)) == (33.73, 51.73)

    def test_fordow(self):
        _, _, name, code = _geolocate_iran("centrifuges at fordow")
        assert (name, code) == ("فردو", "IR")

    def test_falls_back_to_the_shared_country_matcher(self):
        _, _, _, code = _geolocate_iran("explosions reported in gaza")
        assert code == "PS"

    def test_red_sea_maps_to_yemen(self):
        _, _, _, code = _geolocate_iran("shipping attacked in the red sea")
        assert code == "YE"

    def test_defaults_to_tehran_when_nothing_matches(self):
        lat, lon, name, code = _geolocate_iran("unspecified regional tension")
        assert code == "IR"
        assert name == "إيران"
        assert (round(lat, 2), round(lon, 2)) == (35.69, 51.39)

    def test_always_returns_a_four_tuple_of_the_right_types(self):
        lat, lon, name, code = _geolocate_iran("anything")
        assert isinstance(lat, float) and isinstance(lon, float)
        assert isinstance(name, str) and isinstance(code, str)


def test_leaders_list_shape():
    leaders = get_leaders_list()
    assert len(leaders) >= 10
    ids = [leader["id"] for leader in leaders]
    assert len(ids) == len(set(ids)), "معرّفات القادة يجب أن تكون فريدة"
    for leader in leaders:
        for field in ("id", "name", "name_en", "role", "keywords"):
            assert field in leader
        assert leader["keywords"], "كل قائد يحتاج كلمات مفتاحية للمطابقة"
