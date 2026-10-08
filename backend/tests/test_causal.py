"""رصد - اختبارات محرّك سلاسل السبب والأثر (processors/causal).

لكل قالب حالات إيجابية وسلبية بالعربية والإنجليزية، ثم قواعد الزمن والكيان
المشترك وصيغة الثقة. السلبية مقصودة بقدر الإيجابية: الرابط الخاطئ يضلّل أكثر
من غيابه.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.processors import causal
from app.processors.causal import (
    TEMPLATE_BY_ID,
    TEMPLATES,
    build_story_facts,
    entity_factor,
    entity_label,
    evaluate_pair,
    extract_entities,
    propose_links,
    same_incident,
    time_factor,
)
from app.processors.gazetteer import mentions

T0 = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
_ids = iter(range(1, 10_000))


def story(title, hours=0.0, *, sid=None, **fields):
    """قصة من خبر واحد بعد `hours` ساعة من T0."""
    sid = sid or next(_ids)
    row = dict(
        id=sid, title=title, description="", event_date=T0 + timedelta(hours=hours),
        risk_score=None, severity="high", category="military", topic=None, event_type=None,
        facility_id=None, source="rss", confidence="LOW", extra_data=None, impact_sectors=None,
    )
    row.update(fields)
    return build_story_facts(sid, [SimpleNamespace(**row)])


def check(rule, cause, effect):
    return evaluate_pair(TEMPLATE_BY_ID[rule], cause, effect)


def assert_link(rule, cause, effect):
    cand, why = check(rule, cause, effect)
    assert why == "ok", why
    assert cand.rule_id == rule
    assert 0.4 <= cand.confidence <= 1.0
    return cand


def assert_no_link(rule, cause, effect, reason):
    cand, why = check(rule, cause, effect)
    assert cand is None
    assert why == reason


# ===== القالب ١: هجوم في الخليج أو اليمن ← طاقة أو ملاحة =====

class TestGulfAttackEnergyShipping:
    rule = "gulf_attack_energy_shipping"

    def test_en_shipping_suspension(self):
        cand = assert_link(self.rule, story("Houthi missile attack on tanker in Red Sea"),
                           story("Shipping firms suspend Red Sea transits", 5))
        assert [s["key"] for s in cand.evidence["shared"]] == ["red_sea"]
        assert "region:red_sea" in cand.evidence["cause_terms"]

    def test_ar_shipping_suspension(self):
        assert_link(self.rule, story("هجوم حوثي بصاروخ على ناقلة في البحر الأحمر"),
                    story("شركات الشحن تعلق العبور في البحر الأحمر", 6))

    def test_en_oil_price_move(self):
        cand = assert_link(self.rule, story("Israeli strikes hit Iran oil depot"),
                           story("Oil prices jump as Iran tensions rise", 3))
        assert {"oil price*", "jump*"} & set(cand.evidence["effect_terms"]) or "oil" in cand.evidence["effect_terms"]

    def test_ar_oil_price_move_even_when_effect_mentions_the_attack(self):
        # الحركة السعرية أثرٌ لا يلتبس بالحادثة، فتُقبل وإن ذكر العنوان الهجوم
        assert_link(self.rule, story("هجوم بطائرات مسيرة على منشأة نفطية في السعودية"),
                    story("ارتفاع أسعار النفط بعد الهجوم على السعودية", 4))

    def test_falling_oil_is_not_an_effect_of_an_attack(self):
        assert_no_link(self.rule, story("Israeli strikes hit Iran oil depot"),
                       story("Oil prices fall as Iran tensions ease", 3), "effect")
        assert_no_link(self.rule, story("Israeli strikes hit Iran oil depot"),
                       story("Oil jumps on Fed rate cut hopes despite Iran", 3), "effect")

    def test_opec_policy_is_not_an_effect(self):
        assert_no_link(self.rule, story("Houthi missile attack on tanker near Saudi coast"),
                       story("OPEC+ agrees to cut oil output, Saudi Arabia says", 5), "effect")

    def test_attack_outside_gulf_is_not_a_cause(self):
        assert_no_link(self.rule, story("Russian missile attack on Kyiv"),
                       story("Oil prices jump as Russia tensions rise", 3), "cause")

    def test_sector_noun_without_disruption_is_not_an_effect(self):
        assert_no_link(self.rule, story("Iran threatens to close the Strait of Hormuz"),
                       story("Tanker docks at Fujairah port", 5), "effect")
        assert_no_link(self.rule, story("إيران تهدد بإغلاق مضيق هرمز"),
                       story("ناقلة تصل إلى ميناء الفجيرة", 5), "effect")

    def test_attack_with_physical_disruption_is_the_same_incident(self):
        # «هجوم يوقف الملاحة» وصفٌ للحادثة نفسها غالبًا، لا أثرٌ لها
        assert_no_link(self.rule, story("Houthi missile hits tanker in Red Sea"),
                       story("Houthi missile attack halts shipping in Red Sea", 3), "effect")

    def test_requires_a_shared_entity(self):
        assert_no_link(self.rule, story("Houthi missile attack on tanker in Red Sea"),
                       story("Oil prices jump 4%", 3), "entity")


# ===== القالب ٢: حدث نووي ← تحرّك دبلوماسي أو عقوبات =====

class TestNuclearDiplomacy:
    rule = "nuclear_diplomacy"

    def test_en_enrichment_then_sanctions(self):
        cand = assert_link(
            self.rule,
            story("IAEA says Iran enriched uranium to 60% at Fordow", category="nuclear", topic="weapons_program"),
            story("EU imposes new sanctions on Iran over nuclear programme", 10,
                  category="nuclear", topic="diplomacy_sanctions"),
        )
        assert "topic:weapons_program" in cand.evidence["cause_terms"]

    def test_ar_enrichment_then_security_council(self):
        assert_link(
            self.rule,
            story("الوكالة الذرية: إيران خصبت اليورانيوم بنسبة 60% في فوردو",
                  category="nuclear", topic="weapons_program"),
            story("مجلس الأمن يعقد جلسة طارئة بشأن البرنامج النووي الإيراني", 12,
                  category="nuclear", topic="weapons_program"),
        )

    def test_shared_facility_is_stronger_than_country(self):
        cause = story("Explosion reported at Natanz enrichment site", category="nuclear", topic="safety_incident")
        by_facility = assert_link(self.rule, cause, story(
            "Board of Governors to discuss Natanz incident", 6, category="nuclear", topic="safeguards_iaea"))
        by_country = assert_link(self.rule, cause, story(
            "Board of Governors to discuss Iran", 6, category="nuclear", topic="safeguards_iaea"))
        assert by_facility.confidence > by_country.confidence

    def test_non_nuclear_sanctions_are_not_an_effect(self):
        assert_no_link(
            self.rule,
            story("IAEA says Iran enriched uranium to 60%", category="nuclear", topic="weapons_program"),
            story("EU imposes sanctions on Iran over drone exports", 10, category="economic"),
            "effect",
        )

    def test_energy_program_news_is_not_a_cause(self):
        assert_no_link(
            self.rule,
            story("إيران تعلن خطة لمحطة نووية جديدة", category="nuclear", topic="energy_program"),
            story("عقوبات أوروبية جديدة على إيران بسبب البرنامج النووي", 10,
                  category="nuclear", topic="diplomacy_sanctions"),
            "cause",
        )

    def test_a_diplomatic_story_cannot_be_the_cause(self):
        assert_no_link(
            self.rule,
            story("UN Security Council meets on Iran enrichment", category="nuclear", topic="weapons_program"),
            story("EU imposes new sanctions on Iran over nuclear programme", 10,
                  category="nuclear", topic="diplomacy_sanctions"),
            "cause_is_effect",
        )


# ===== القالب ٣: ضربة ← رد انتقامي =====

class TestStrikeRetaliation:
    rule = "strike_retaliation"

    def test_en(self):
        cand = assert_link(self.rule, story("Israel strikes targets in Iran"),
                           story("Iran launches retaliatory strikes on Israel", 8))
        assert {s["key"] for s in cand.evidence["shared"]} == {"IL", "IR"}

    def test_ar(self):
        assert_link(self.rule, story("إسرائيل تشن غارات على إيران"),
                    story("إيران تطلق صواريخ ردا على الهجوم الإسرائيلي", 8))

    def test_iran_osint_event_type_counts_as_strike(self):
        assert_link(self.rule, story("Explosions reported near Isfahan, Iran", event_type="strike"),
                    story("Iran fires missiles at Israel in retaliation", 6))

    def test_labor_strike_is_not_a_cause(self):
        assert_no_link(self.rule, story("General strike paralyses Beirut"),
                       story("Israeli jets hit Beirut in retaliation", 5), "cause")

    def test_striking_a_deal_is_not_a_cause(self):
        assert_no_link(self.rule, story("Saudi Arabia strikes deal with Iran"),
                       story("Iran fires missiles in retaliation at Saudi Arabia", 5), "cause")

    def test_retaliatory_tariffs_are_not_retaliation(self):
        assert_no_link(self.rule, story("Israel strikes Iran"),
                       story("Iran announces retaliatory tariffs on Israel", 5), "effect")
        assert_no_link(self.rule, story("إسرائيل تقصف إيران"),
                       story("إيران تفرض رسوما جمركية ردا على الهجوم الإسرائيلي", 5), "effect")

    def test_a_vow_is_not_retaliation(self):
        assert_no_link(self.rule, story("Israel strikes Iran"),
                       story("Iran vows revenge against Israel", 3), "effect")

    def test_a_retaliation_cannot_be_the_cause_of_its_own_report(self):
        # تقريران عن الرد نفسه: الأول ليس «سببًا» للثاني
        assert_no_link(self.rule, story("Iran launches retaliatory strikes on Israel"),
                       story("Retaliatory strikes from Iran hit Israel", 3), "cause_is_effect")


# ===== القالب ٤: ضربة ← إطلاق صواريخ =====

class TestStrikeLaunch:
    rule = "strike_launch"

    def test_en_two_shared_countries(self):
        assert_link(self.rule, story("Israel strikes Iran"), story("Iran fires missiles at Israel", 5))

    def test_ar_two_shared_countries(self):
        assert_link(self.rule, story("إسرائيل تقصف إيران"),
                    story("إيران تطلق صواريخ باليستية نحو إسرائيل", 5))

    def test_one_shared_country_is_too_weak(self):
        assert_no_link(self.rule, story("Israel strikes Gaza"),
                       story("Hezbollah fires rockets at Israel", 4), "entity_strength")

    def test_satellite_launch_is_not_military(self):
        assert_no_link(self.rule, story("Israel strikes Iran"),
                       story("Iran satellite launch used ballistic missile technology, Israel says", 5),
                       "effect")

    def test_launch_event_type_needs_a_missile_in_the_title(self):
        assert_link(self.rule, story("Israel strikes Iran"),
                    story("Iran tests new missile, Israel on alert", 5, event_type="launch"))
        assert_no_link(self.rule, story("Israel strikes Iran"),
                       story("Iran launches investigation, Israel says", 5, event_type="launch"), "effect")


# ===== القالب ٥: هجوم على أصل سعودي ← طيران أو أسواق =====

class TestKsaAssetAviationMarkets:
    rule = "ksa_asset_aviation_markets"

    def test_en_markets(self):
        cand = assert_link(self.rule, story("Houthi drone attack on Aramco facility in Abqaiq"),
                           story("Saudi stocks fall after Aramco attack", 2))
        assert ("asset", "aramco") in {(s["kind"], s["key"]) for s in cand.evidence["shared"]}

    def test_ar_aviation(self):
        cand = assert_link(self.rule, story("هجوم بطائرة مسيرة على مطار أبها"),
                           story("تعليق الرحلات في مطار أبها", 2))
        assert cand.evidence["shared"][0]["key"] == "abha_airport"

    def test_target_located_in_the_kingdom(self):
        assert_link(self.rule, story("Missile attack on Jazan"),
                    story("Flights suspended at Jazan airport", 3))

    def test_sharing_only_the_kingdom_is_not_evidence(self):
        # الطرفان سعوديان بحكم القالب: هجوم في بقيق لا يفسّر تعليق رحلات أبها
        assert_no_link(self.rule, story("Houthi drone attack on Aramco facility in Abqaiq"),
                       story("تعليق الرحلات في مطار أبها", 3), "entity")
        assert_no_link(self.rule, story("هجوم بطائرة مسيرة على مطار أبها"),
                       story("Saudi stocks fall after Aramco attack", 3), "entity")

    def test_saudi_led_strike_is_not_an_attack_on_a_saudi_asset(self):
        assert_no_link(self.rule, story("Saudi-led coalition strikes Sanaa"),
                       story("Flights suspended at Sanaa airport", 4), "cause")

    def test_effect_must_concern_the_kingdom(self):
        assert_no_link(self.rule, story("Houthi drone attack on Jazan"),
                       story("Flights suspended at Aden airport", 4), "effect")
        assert_no_link(self.rule, story("Houthi drone attack on Aramco facility"),
                       story("Gold prices rise", 4), "effect")

    def test_market_move_must_point_the_expected_way(self):
        cause = story("Houthi drone attack on Aramco facility in Abqaiq")
        assert_no_link(self.rule, cause, story("Saudi stocks rise after Aramco attack", 2), "effect")
        assert_link(self.rule, cause, story("تراجع الأسهم السعودية بعد هجوم أرامكو", 2))
        assert_link(self.rule, cause, story("Volatility hits Saudi stocks after Aramco attack", 2))

    def test_move_attributed_to_another_driver_is_not_an_effect(self):
        assert_no_link(self.rule, story("Houthi drone attack on Aramco facility in Abqaiq"),
                       story("Saudi stocks fall as Aramco profit drops", 4), "effect")

    def test_attack_report_with_disruption_is_the_same_incident(self):
        assert_no_link(self.rule, story("Drone attack on Abha airport"),
                       story("Drone attack halts flights at Abha airport", 2), "effect")


# ===== قواعد مشتركة =====

class TestTimeWindow:
    rule = "strike_retaliation"

    def _pair(self, hours):
        return story("Israel strikes targets in Iran"), story("Iran launches retaliatory strikes on Israel", hours)

    def test_effect_before_cause_is_rejected(self):
        assert_no_link(self.rule, *self._pair(-5), "order")

    def test_less_than_an_hour_apart_is_rejected(self):
        assert_no_link(self.rule, *self._pair(0.5), "order")

    def test_beyond_72_hours_is_rejected(self):
        assert_no_link(self.rule, *self._pair(73), "window")

    def test_confidence_decays_after_a_day(self):
        early = assert_link(self.rule, *self._pair(10))
        late = assert_link(self.rule, *self._pair(70))
        assert early.evidence["components"]["time"] == 1.0
        assert late.confidence < early.confidence

    @pytest.mark.parametrize("hours,factor", [(1, 1.0), (24, 1.0), (48, 0.875), (72, 0.75)])
    def test_time_factor(self, hours, factor):
        assert time_factor(hours) == factor


class TestSharedEntities:
    def test_no_shared_entity_no_link(self):
        assert_no_link("strike_retaliation", story("Israel strikes Gaza"),
                       story("Houthis fire missiles at ships in retaliation", 5), "entity")

    def test_description_mentions_do_not_count(self):
        cause = story("Houthi missile attack on tanker", description="The ship was in the Red Sea.")
        effect = story("Shipping firms suspend Red Sea transits", 5)
        assert ("waterway", "red_sea") not in cause.entities
        assert_no_link("gulf_attack_energy_shipping", cause, effect, "entity")

    def test_entity_factor(self):
        assert entity_factor([("country", "IR")]) == 0.8
        assert entity_factor([("country", "IL"), ("country", "IR")]) == 0.85
        assert entity_factor([("asset", "aramco"), ("country", "SA")]) == 1.0
        assert entity_factor([]) == 0.0

    def test_extract_entities(self):
        ents = extract_entities("Araghchi says Iran will respond in the Gulf of Aden", None)
        assert ("leader", "ir6") in ents
        assert ("waterway", "gulf_of_aden") in ents
        assert ("country", "IR") in ents
        # الأصل نفسه باللغتين مفتاح واحد
        assert ("asset", "aramco") in extract_entities("أرامكو تعلن")
        assert ("asset", "aramco") in extract_entities("Aramco says")
        assert ("facility", "ir-natanz") in extract_entities("Anything", "ir-natanz")

    def test_entity_labels(self):
        assert entity_label("country", "IR") == ("إيران", "Iran")
        assert entity_label("waterway", "red_sea") == ("البحر الأحمر", "Red Sea")
        assert entity_label("facility", "ir-natanz")[1].startswith("Natanz")
        assert entity_label("asset", "aramco") == ("أرامكو", "Aramco")
        assert entity_label("leader", "unknown") == ("unknown", "unknown")

    def test_gazetteer_mentions_lists_everything(self):
        m = mentions("Israel strikes Tehran as tankers leave the Strait of Hormuz near Natanz")
        assert {"IL", "IR"} <= m.countries
        assert "tehran" in m.places
        assert "hormuz" in m.waterways
        assert "ir-natanz" in m.facilities
        assert mentions("").countries == frozenset()


class TestConfidence:
    def test_formula(self):
        cand = assert_link("gulf_attack_energy_shipping", story("Houthi missile attack on tanker in Red Sea"),
                           story("Shipping firms suspend Red Sea transits", 5))
        c = cand.evidence["components"]
        assert c == {
            "template": 0.8, "entity": 0.95, "time": 1.0, "match": 0.76,
            "source_trust": 0.9, "cause_trust": 0.9, "effect_trust": 0.9,
        }
        assert cand.confidence == round(0.8 * 0.95 * 1.0 * 0.9, 2) == 0.68
        assert cand.evidence["hours"] == 5.0

    def test_source_trust_is_the_weaker_end(self):
        cause = story("Israel strikes targets in Iran", source="ucdp")
        effect = story("Iran launches retaliatory strikes on Israel", 6)
        cand = assert_link("strike_retaliation", cause, effect)
        assert cand.evidence["components"]["cause_trust"] == 1.0
        assert cand.evidence["components"]["source_trust"] == 0.9

    def test_story_takes_its_best_source(self):
        rows = [
            SimpleNamespace(id=500, title="Israel strikes Iran", event_date=T0, risk_score=None, severity="high",
                            category="military", topic=None, event_type=None, facility_id=None, source="rss",
                            confidence="LOW", extra_data=None, impact_sectors=None),
            SimpleNamespace(id=501, title="Israeli strikes on Iranian sites", event_date=T0 - timedelta(hours=1),
                            risk_score=None, severity="critical", category="military", topic=None,
                            event_type=None, facility_id=None, source="rss", confidence="LOW",
                            extra_data=json.dumps({"source_kind": "official"}), impact_sectors=None),
        ]
        f = build_story_facts(500, rows)
        assert f.trust == 1.0
        assert f.first_seen == T0 - timedelta(hours=1)
        assert f.rep_id == 501                       # الأشد يمثّل القصة

    def test_min_confidence_threshold(self):
        stories = [story("Houthi missile attack on tanker in Red Sea"),
                   story("Shipping firms suspend Red Sea transits", 5)]
        assert len(propose_links(stories)) == 1
        assert propose_links(stories, min_confidence=0.7) == []


class TestProposeLinks:
    def test_one_link_per_pair_keeps_the_strongest_rule(self):
        cause = story("Houthi drone attack on Aramco facility in Abqaiq")
        effect = story("Oil prices jump after Aramco attack in Saudi Arabia", 3)
        assert check("gulf_attack_energy_shipping", cause, effect)[1] == "ok"
        links = propose_links([cause, effect])
        assert len(links) == 1
        assert links[0].rule_id == "ksa_asset_aviation_markets"

    def test_keeps_at_most_two_causes_per_effect(self):
        causes = [story(f"Houthi missile attack number {i} on tanker in Red Sea", i) for i in range(4)]
        effect = story("Shipping firms suspend Red Sea transits", 10)
        links = propose_links(causes + [effect])
        assert len(links) == 2
        assert all(lk.effect_id == effect.id for lk in links)

    def test_effect_scope(self):
        cause = story("Israel strikes targets in Iran")
        effect = story("Iran launches retaliatory strikes on Israel", 6)
        assert propose_links([cause, effect], effect_ids=[cause.id]) == []
        assert len(propose_links([cause, effect], effect_ids=[effect.id])) == 1

    def test_refiners_hook(self):
        stories = [story("Israel strikes targets in Iran"), story("Iran launches retaliatory strikes on Israel", 6)]
        assert propose_links(stories, refiners=[lambda cands: []]) == []

    def test_same_story_is_never_linked(self):
        s = story("Israel strikes targets in Iran")
        assert check("strike_retaliation", s, s) == (None, "same_story")

    def test_templates_are_well_formed(self):
        assert len({t.id for t in TEMPLATES}) == len(TEMPLATES) == 5
        for t in TEMPLATES:
            assert 0 < t.weight <= 1 and t.relation_ar and t.relation_en
        assert {d["id"] for d in causal.describe_templates()} == set(TEMPLATE_BY_ID)


class TestSameIncident:
    def test_near_identical_titles_with_nothing_new(self):
        cause = story("Houthis attack tanker carrying Saudi oil in Red Sea")
        effect = story("Tanker carrying Saudi oil attacked by Houthis in Red Sea", 2)
        assert same_incident(cause, effect, ["attack"])

    def test_close_titles_with_a_new_consequence(self):
        cause = story("Israel strikes targets in Iran")
        effect = story("Iran launches retaliatory strikes on Israel", 2)
        assert not same_incident(cause, effect, ["retaliatory strike*"])

    def test_field_evidence(self):
        cause = story("Iran nuclear site Fordow inspection", topic="safeguards_iaea")
        effect = story("Iran nuclear site Fordow inspection talks", 2, topic="diplomacy_sanctions")
        assert not same_incident(cause, effect, ["topic:diplomacy_sanctions"])
        assert same_incident(cause, effect, ["topic:safeguards_iaea"])


class TestFalsePositiveSweep:
    """دفعة عناوين واقعية تتشارك كيانات ومفردات بلا علاقة سببية: لا رابط."""

    HEADLINES = [
        ("Saudi Arabia strikes deal with Iran on trade", 0),
        ("Iran's president visits Muscat for talks", 2),
        ("General strike paralyses Beirut", 3),
        ("OPEC+ agrees to cut oil output, Saudi Arabia says", 5),
        ("Tanker docks at Fujairah port", 6),
        ("Iran vows revenge against Israel", 8),
        ("Iran launches investigation into Tehran fire", 9),
        ("Saudi stocks rise on strong bank earnings", 11),
        ("Flights resume normally at King Khalid airport", 12),
        ("إيران تعلن خطة لمحطة نووية جديدة", 14),
        ("ناقلة تصل إلى ميناء الفجيرة", 15),
        ("وزير الخارجية السعودي يلتقي نظيره الإيراني في الرياض", 17),
        ("إيران تفرض رسوما جمركية جديدة على الواردات", 20),
        ("Israel's economy grows 2% in third quarter", 22),
        ("Houthi leader gives speech in Sanaa", 25),
        ("Yemenia adds new flights from Aden", 30),
        ("Oil prices steady as markets await Fed decision", 33),
    ]

    # أسباب حقيقية في أول الفترة: كل عنوان بعدها يُختبر أثرًا محتملًا لها
    CAUSES = [
        ("Houthi missile attack on tanker in Red Sea", -2),
        ("Israel strikes targets in Iran", -1.5),
        ("Houthi drone attack on Aramco facility in Abqaiq", -1),
        ("IAEA says Iran enriched uranium to 60% at Fordow", -1),
    ]

    def test_no_links_without_causes(self):
        stories = [story(title, hours) for title, hours in self.HEADLINES]
        assert propose_links(stories, min_confidence=0.0) == []

    def test_noise_after_real_causes_is_not_linked(self):
        causes = [story(t, h, category="nuclear", topic="weapons_program") if "IAEA" in t else story(t, h)
                  for t, h in self.CAUSES]
        noise = [story(title, hours) for title, hours in self.HEADLINES]
        links = propose_links(causes + noise, min_confidence=0.0)
        assert [(lk.cause_id, lk.effect_id, lk.rule_id) for lk in links] == []
