"""رصد - اختبارات عدسة الأثر على المملكة: وسم القطاعات ودرجة الأثر."""
from __future__ import annotations

import json

import pytest

from app.processors.gazetteer import ksa_proximity, proximity_band
from app.processors.impact import (
    MENTION_FACTOR,
    PROXIMITY_FACTOR,
    SECTOR_KEYS,
    SEVERITY_FACTOR,
    assess_impact,
    direct_mention,
    impact_fields,
    parse_sectors,
    source_trust,
    tag_sectors,
)
from app.processors.nuclear import assess, proximity_adjustment
from app.processors.text_analysis import locate


class TestSectorTagging:
    @pytest.mark.parametrize("title,sector", [
        ("Houthi missile intercepted over Jazan", "security"),
        ("اعتراض صاروخ باليستي أطلقه الحوثيون", "security"),
        ("Refinery fire disrupts crude exports", "energy"),
        ("حريق في مصفاة يوقف صادرات النفط الخام", "energy"),
        ("Flights suspended as airspace closes", "aviation"),
        ("تعليق الرحلات الجوية وإغلاق المجال الجوي", "aviation"),
        ("Tanker attacked in the Red Sea", "shipping_ports"),
        ("استهداف ناقلة نفط في البحر الأحمر", "shipping_ports"),
        ("Tadawul stocks slide as investors flee", "markets"),
        ("تراجع الأسهم في تداول وسط قلق المستثمرين", "markets"),
        ("Wheat imports hit by drought", "food_water"),
        ("الجفاف يهدد محاصيل القمح", "food_water"),
        ("Cholera outbreak reported in Hodeidah hospital", "health"),
        ("تفشي الكوليرا في مستشفى الحديدة", "health"),
        ("Foreign minister arrives for ceasefire talks", "diplomacy"),
        ("وزير الخارجية يصل لمحادثات وقف إطلاق النار", "diplomacy"),
    ])
    def test_bilingual_lexicon(self, title, sector):
        assert sector in tag_sectors(title)

    @pytest.mark.parametrize("title,absent", [
        # حدود الكلمة: "war" ليست "warning"، "port" ليست "report" ولا "airport"
        ("Weather warning issued for the coast", "security"),
        ("Annual report published by the ministry", "shipping_ports"),
        ("New terminal opens at the airport", "shipping_ports"),
        # «WHO» ضمير لا منظمة الصحة العالمية
        ("Officials who said the meeting went well", "health"),
        # «صحة الخبر» صدق لا قطاع صحي
        ("مصادر تنفي صحة الخبر المتداول", "health"),
        # المياه الإقليمية ليست أمنًا مائيًا
        ("Navy patrols in territorial waters", "food_water"),
        # مخزون اليورانيوم ليس سوق أسهم، والوكالة الذرية ليست قطاع طاقة
        ("Iran uranium stockpile grows", "markets"),
        ("International Atomic Energy Agency board meets", "energy"),
        ("الوكالة الدولية للطاقة الذرية تعقد اجتماعها", "energy"),
        # إضراب عن الطعام ليس ضربة
        ("Prisoners on hunger strike", "security"),
    ])
    def test_word_boundary_false_positives(self, title, absent):
        assert absent not in tag_sectors(title)

    def test_title_counts_twice_and_orders_by_hits(self):
        hits = tag_sectors("Oil tanker struck by drone", "Shipping firms reroute vessels")
        assert list(hits)[0] == "shipping_ports"
        assert hits["shipping_ports"] > hits["security"]

    def test_untagged_event(self):
        assert tag_sectors("Local football club wins the cup") == {}


class TestDirectMention:
    @pytest.mark.parametrize("text,level", [
        ("Drone attack on Aramco facility", "asset"),
        ("هجوم على منشأة أرامكو في بقيق", "asset"),
        ("Saudi Arabia condemns the attack", "ksa"),
        ("انفجار قرب الرياض", "ksa"),
        ("Shipping through the Strait of Hormuz disrupted", "chokepoint"),
        ("تهديد الملاحة في باب المندب", "chokepoint"),
        ("Protests in Paris", "none"),
    ])
    def test_levels(self, text, level):
        assert direct_mention(text)[0] == level

    def test_asset_beats_country(self):
        level, matched = direct_mention("Saudi Aramco's Ras Tanura terminal hit")
        assert level == "asset"
        assert "ras tanura" in matched

    @pytest.mark.parametrize("text", [
        # «رياض» اسم علم، و«جبيل» مدينة لبنانية — لا إشارة للمملكة
        "رياض سلامة يمثل أمام القضاء",
        "انفجار في ميناء جبيل اللبناني",
        # «ينبع» وحدها فعل
        "الخلاف ينبع من سوء الفهم",
    ])
    def test_ambiguous_names_are_not_mentions(self, text):
        assert direct_mention(text)[0] == "none"

    def test_definite_forms_with_prepositions(self):
        assert direct_mention("وصل الوفد إلى الرياض")[0] == "ksa"
        assert direct_mention("اجتماع بالرياض")[0] == "ksa"
        assert direct_mention("زيارة للرياض")[0] == "ksa"


class TestSourceTrust:
    def test_known_kinds_reuse_nuclear_table(self):
        assert source_trust(source_kind="official") == 1.0
        assert source_trust(source_kind="analysis") == 0.8

    def test_ucdp_is_official(self):
        assert source_trust("ucdp") == 1.0

    def test_iran_osint_uses_feed_confidence(self):
        assert source_trust("iran_osint", confidence="HIGH") == 1.0
        assert source_trust("iran_osint", confidence="LOW") == 0.8

    def test_default_is_news(self):
        assert source_trust("gdelt") == 0.9


class TestProximity:
    def test_bands(self):
        assert proximity_band(None) == "unknown"
        assert proximity_band(100) == "adjacent"
        assert proximity_band(500) == "near"
        assert proximity_band(1000) == "regional"
        assert proximity_band(3000) == "far"

    def test_ksa_proximity(self):
        p = ksa_proximity(26.64, 50.16)
        assert p.band == "adjacent" and p.nearest_point == "رأس تنورة"
        assert ksa_proximity(None, None).band == "unknown"

    @pytest.mark.parametrize("km,points", [(None, -5), (10, 15), (500, 8), (1000, 3), (5000, -10)])
    def test_nuclear_adjustment_unchanged(self, km, points):
        assert proximity_adjustment(km) == points

    def test_nuclear_score_unchanged(self):
        """الأمثلة الموثّقة في docs/nuclear-risk-methodology.md تبقى كما هي."""
        title = "Missile strike on Bushehr nuclear power plant, radiation leak feared, residents evacuated"
        a = assess(title, location=locate(title))
        assert a.risk_score == 99.9
        assert a.components["proximity"] == 15


class TestImpactScore:
    def test_formula_is_the_product_of_factors(self):
        a = assess_impact(
            "Houthi drone attack on Aramco facility in Abqaiq",
            severity="critical", latitude=25.94, longitude=49.67, source_kind="news",
        )
        c = a.components
        assert c == {"severity": 1.0, "proximity": 1.0, "mention": 1.0, "source_trust": 0.9}
        assert a.score == 90.0
        assert a.mention == "asset"
        assert {"security", "energy"} <= set(a.sectors)

    def test_far_low_event_scores_low(self):
        a = assess_impact("Local elections held", severity="low", latitude=51.5, longitude=-0.1)
        assert a.proximity_band == "far"
        expected = 100 * SEVERITY_FACTOR["low"] * PROXIMITY_FACTOR["far"] * MENTION_FACTOR["none"] * 0.9
        assert a.score == round(expected, 1)
        assert a.score < 10

    def test_unknown_location_is_not_treated_as_far(self):
        unknown = assess_impact("Strike reported", severity="high")
        far = assess_impact("Strike reported", severity="high", latitude=51.5, longitude=-0.1)
        assert unknown.score > far.score

    def test_mention_raises_score(self):
        base = dict(severity="high", latitude=15.4, longitude=44.2)
        plain = assess_impact("Missile launched from Sanaa", **base)
        aimed = assess_impact("Missile launched from Sanaa toward Saudi Arabia", **base)
        assert aimed.score > plain.score

    def test_unknown_severity_falls_back_to_low(self):
        assert assess_impact("x", severity="weird").components["severity"] == SEVERITY_FACTOR["low"]

    def test_score_is_capped(self):
        a = assess_impact(
            "Aramco attack", severity="critical", latitude=26.6, longitude=50.1, source_kind="official",
        )
        assert 0 <= a.score <= 100

    def test_extra_payload(self):
        a = assess_impact("Drone attack near Jubail", severity="high", latitude=27.0, longitude=49.6)
        extra = a.as_extra()
        assert extra["nearest_ksa_point_en"] == "Jubail"
        assert extra["components"] == a.components


class TestImpactFields:
    def test_merges_into_extra_data(self):
        fields = {
            "title": "Tanker attacked in the Red Sea",
            "description": "",
            "severity": "high",
            "latitude": 15.0,
            "longitude": 42.0,
            "source": "rss",
            "extra_data": json.dumps({"source_kind": "official", "source_name": "SPA"}),
        }
        out = impact_fields(fields)
        extra = json.loads(out["extra_data"])
        assert extra["source_name"] == "SPA"
        assert extra["impact"]["components"]["source_trust"] == 1.0
        assert "shipping_ports" in json.loads(out["impact_sectors"])
        assert out["ksa_impact"] == extra["impact"]["score"]

    def test_tolerates_broken_extra(self):
        out = impact_fields({"title": "x", "extra_data": "{not json"})
        assert json.loads(out["extra_data"])["impact"]["score"] == out["ksa_impact"]

    def test_parse_sectors(self):
        assert parse_sectors('["energy", "bogus"]') == ["energy"]
        assert parse_sectors(None) == []
        assert parse_sectors("{oops") == []
        assert parse_sectors('{"a": 1}') == []

    def test_sector_keys(self):
        assert SECTOR_KEYS == (
            "security", "energy", "aviation", "shipping_ports", "markets", "food_water", "health", "diplomacy",
        )


@pytest.mark.parametrize("title,severity,lat,lon,expected", [
    # جدول الأمثلة في docs/ksa-impact-methodology.md
    ("هجوم بمسيرة على منشأة أرامكو في بقيق", "critical", 25.94, 49.67, 90.0),
    ("اعتراض صاروخ باليستي أطلق نحو الرياض", "critical", 24.7, 46.6, 81.0),
    ("استهداف ناقلة في البحر الأحمر قبالة الحديدة", "high", 14.8, 42.95, 57.4),
    ("Oil prices jump as tankers avoid the Strait of Hormuz", "medium", 26.5, 56.3, 30.6),
    ("Local elections held in London", "low", 51.5, -0.1, 4.0),
])
def test_documented_examples(title, severity, lat, lon, expected):
    assert assess_impact(title, severity=severity, latitude=lat, longitude=lon).score == expected
