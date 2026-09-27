"""رصد - اختبارات تصنيف أحداث إيران وتحديد مواقعها وربط القادة."""
import pytest

from app.collectors.iran_osint import (
    _classify_iran_event,
    _geolocate_iran,
    _locate_iran,
    get_leaders_list,
    leaders_mentioned,
)


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
        assert "نطنز" in name
        assert (round(lat, 2), round(lon, 2)) == (33.72, 51.73)

    def test_fordow(self):
        _, _, name, code = _geolocate_iran("centrifuges at fordow")
        assert "فوردو" in name and code == "IR"

    def test_barakah_is_in_the_uae_not_arak(self):
        """«Barakah» تحوي «arak»: البحث بجزء النص كان يضعها في أراك/إيران."""
        lat, lon, name, code, precision = _locate_iran(
            "UAE Barakah nuclear plant reports drone attack, IRGC blamed"
        )
        assert code == "AE"
        assert precision == "facility"
        assert (round(lat, 1), round(lon, 1)) == (24.0, 52.2)

    def test_mubarak_is_not_arak(self):
        """«Mubarak» تحوي «arak» أيضًا — الموقع هو إيران (الدولة المذكورة) لا مدينة أراك."""
        lat, lon, _, code, precision = _locate_iran("Mubarak-era officials comment on Iran strike")
        assert (code, precision) == ("IR", "country")
        assert (round(lat, 1), round(lon, 1)) != (34.1, 49.7), "ليست أراك"

    @pytest.mark.parametrize("title", [
        "Iranian navy drills in Persian Gulf near Strait of Hormuz",
        "tanker seized in the strait of hormuz",
    ])
    def test_water_bodies_carry_no_country_code(self, title):
        """المسطّحات المائية بلا رمز دولة كي لا تُنسب لإيران فتضخّم مؤشرها."""
        _, _, _, code, precision = _locate_iran(title)
        assert code == ""
        assert precision == "region"

    def test_default_precision_is_country(self):
        *_, precision = _locate_iran("unspecified regional tension")
        assert precision == "country"

    def test_falls_back_to_the_shared_country_matcher(self):
        _, _, _, code = _geolocate_iran("explosions reported in gaza")
        assert code == "PS"

    def test_red_sea_is_a_maritime_region_not_a_country(self):
        """البحر الأحمر لا يُنسب لليمن كي لا يضخّم مؤشرها بأحداث ملاحية دولية."""
        lat, _, name, code = _geolocate_iran("shipping attacked in the red sea")
        assert code == ""
        assert name == "البحر الأحمر"
        assert lat is not None

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


class TestLeaderMentions:
    def test_full_name_matches(self):
        ids = {lead["id"] for lead in leaders_mentioned("Mohammad Eslami says enrichment continues")}
        assert ids == {8}

    def test_arabic_name_matches_with_clitics(self):
        ids = {lead["id"] for lead in leaders_mentioned("تصريحات لعراقجي حول المفاوضات")}
        assert ids == {6}

    @pytest.mark.parametrize("title", [
        "الجمهورية الإسلامية الإيرانية تعلن عن مناورات عسكرية",
        "Islamic Republic marks anniversary",
        "iran's islamist movement protests",
    ])
    def test_islamic_republic_is_not_eslami(self, title):
        """«الإسلامية» تحوي «إسلامي»: البحث بجزء النص كان يُنسب كل خبر عن
        الجمهورية الإسلامية لرئيس منظمة الطاقة الذرية."""
        assert leaders_mentioned(title) == []

    def test_several_leaders_in_one_text(self):
        ids = {lead["id"] for lead in leaders_mentioned("Araghchi and Shamkhani meet in Muscat")}
        assert ids == {6, 10}
