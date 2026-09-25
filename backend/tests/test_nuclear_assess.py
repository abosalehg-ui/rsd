"""رصد - اختبارات تصنيف المخاطر النووية والإشعاعية ودرجتها."""
import pytest

from app.processors.nuclear import is_nuclear_relevant, severity_from_score
from app.processors.text_analysis import analyze


def nuc(title, **kw):
    return analyze(title, **kw).nuclear


class TestGate:
    @pytest.mark.parametrize("title", [
        "استخدام التكنولوجيا الحديثة لاختبار الحمض النووي لتحديد هوية الجنود",
        "DNA tests identify victims",
        "Solar radiation peaks this summer",
        "The nuclear family is changing",
    ])
    def test_non_atomic_uses_are_excluded(self, title):
        assert not is_nuclear_relevant(title)

    @pytest.mark.parametrize("title", [
        "الرئيس الإيراني: سنتخلى عن اليورانيوم المخصب بنسبة 60%",
        "IAEA Board of Governors meets on Iran",
        "Radioactive source missing in Dammam",
        "Inspectors return to Fordow",           # اسم منشأة وحده يكفي
    ])
    def test_relevant(self, title):
        assert is_nuclear_relevant(title)


class TestTopics:
    @pytest.mark.parametrize("title,topic", [
        ("Missile strike on Bushehr nuclear power plant", "military_threat"),
        ("Radioactive source missing from site in Dammam", "radioactive_source"),
        ("Radiation leak detected near reactor", "radiation_release"),
        ("IAEA Board of Governors to discuss Iran safeguards report", "safeguards_iaea"),
        ("Iran enriches uranium to 60% purity", "weapons_program"),
        ("هيئة الرقابة النووية والإشعاعية تنفذ تمرين طوارئ إشعاعية", "emergency_preparedness"),
        ("Nuclear medicine centre opens in Riyadh", "medical_industrial"),
        ("Snapback sanctions on Iran nuclear programme", "diplomacy_sanctions"),
    ])
    def test_topic(self, title, topic):
        assert nuc(title).topic == topic

    def test_radiological_topics_have_radiological_category(self):
        assert analyze("Radioactive source missing from site in Dammam").category == "radiological"


class TestScore:
    def test_strike_on_nearby_plant_is_critical(self):
        a = nuc("Missile strike on Bushehr nuclear power plant, radiation leak feared, residents evacuated")
        assert a.severity == "critical"
        assert a.components["proximity"] == 15      # بوشهر < 300 كم من المملكة
        assert a.facility_ids == ["ir-bushehr-1"]

    def test_reassurance_lowers_but_does_not_erase(self):
        alarm = nuc("Israeli strike hits Natanz enrichment site")
        calm = nuc("Israeli strike hits Natanz enrichment site; IAEA says no increase in off-site radiation levels")
        assert calm.reassuring and not alarm.reassuring
        assert calm.risk_score < alarm.risk_score
        assert calm.topic == "military_threat"
        assert calm.severity in ("high", "medium")

    def test_reassuring_phrase_does_not_trigger_release_topic(self):
        a = nuc("IAEA: no radiation leak at Bushehr after nearby blast")
        assert a.topic != "radiation_release"

    def test_drill_is_dampened(self):
        drill = nuc("Radiation emergency drill at Barakah")
        assert drill.components["dampening"] < 0
        assert drill.severity in ("low", "medium")

    def test_distant_industry_news_is_low(self):
        a = nuc("Uranium price rises", base_category="nuclear", source_kind="specialist")
        assert a.severity == "low"

    def test_statement_is_lower_than_incident(self):
        statement = nuc("نتنياهو: تدمير نووي إيران كان أسهل قراراتي")
        assert statement.components["statement"] < 0

    def test_score_is_bounded(self):
        a = nuc("Missile strike attack explosion on Bushehr nuclear plant radiation leak evacuated killed emergency")
        assert 0 <= a.risk_score <= 100

    def test_components_are_exposed_for_explanation(self):
        a = nuc("Radiation leak detected near reactor")
        assert {"base", "intensity", "dampening", "proximity", "source_trust"} <= set(a.components)


@pytest.mark.parametrize("score,sev", [(80, "critical"), (60, "high"), (35, "medium"), (10, "low")])
def test_severity_bands(score, sev):
    assert severity_from_score(score) == sev
