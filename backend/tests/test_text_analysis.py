"""رصد - اختبارات وحدة لتحليل النصوص المشترك"""
from app.processors.text_analysis import classify, geolocate


class TestClassify:
    def test_nuclear_base_category_forced(self):
        assert classify("anything", base_category="nuclear") == ("nuclear", "high")

    def test_nuclear_keyword(self):
        cat, sev = classify("Iran uranium enrichment at Natanz")
        assert cat == "nuclear"

    def test_military_high(self):
        cat, sev = classify("Airstrike hits military base")
        assert cat == "military"
        assert sev == "high"

    def test_military_critical_on_death(self):
        cat, sev = classify("Missile strike killed dozens")
        assert cat == "military"
        assert sev == "critical"

    def test_arabic_military(self):
        cat, _ = classify("قصف صاروخي على الموقع")
        assert cat == "military"

    def test_diplomatic(self):
        cat, sev = classify("Ceasefire negotiations resume")
        assert cat == "diplomatic"
        assert sev == "medium"

    def test_economic(self):
        cat, _ = classify("New sanctions on oil exports")
        assert cat == "economic"

    def test_general_fallback(self):
        cat, sev = classify("Local weather update")
        assert cat == "general"
        assert sev == "low"


class TestGeolocate:
    def test_gaza(self):
        code, name, lat, lon = geolocate("Explosions reported in Gaza")
        assert code == "PS"
        assert lat is not None and lon is not None

    def test_arabic_iran(self):
        code, name, lat, lon = geolocate("تصريحات من طهران")
        assert code == "IR"

    def test_no_match(self):
        code, name, lat, lon = geolocate("Generic headline")
        assert code == ""
        assert lat is None
