"""رصد - اختبارات المطابقة بحدود الكلمة والتطبيع وتنظيف النصوص."""
import pytest

from app.processors.matching import KeywordSet
from app.processors.normalize import clean_text, normalize_for_match, split_source_suffix
from app.processors.text_analysis import classify


def hits(terms, text):
    return KeywordSet(terms).matched_terms(normalize_for_match(text))


class TestWordBoundaries:
    """كل حالة هنا كانت تُطابَق خطأً بالبحث عن جزء النص (`kw in text`)."""

    @pytest.mark.parametrize("term,text", [
        ("war", "Rain warning in Cairo"),
        ("aid", "Minister said talks resume"),
        ("dead", "Deadline passes for deal"),
        ("قتل", "الرئيس يقتلع جذور الفساد"),
        ("un", "Stock run on bank"),
        ("oil", "Turmoil in markets"),
        ("test", "Latest protest in the capital"),
    ])
    def test_substring_inside_another_word_does_not_match(self, term, text):
        assert hits([term], text) == []

    @pytest.mark.parametrize("term,text", [
        ("war", "fears of a regional war"),
        ("قتل", "سقوط قتلى في القصف"),
        ("قتل", "بالقتل العمد"),
        ("نووي", "المنشآت النووية"),
        ("إشعاع", "ارتفاع مستويات الإشعاعات"),
        ("enrich*", "uranium enrichment levels"),
        ("60%", "enriched to ٦٠٪"),
        ("cobalt 60", "a Cobalt-60 source"),
        ("الطاقة الذرية", "الوكالة الدولية للطاقة الذرية"),
    ])
    def test_real_inflections_still_match(self, term, text):
        assert hits([term], text) == [term]

    def test_overlapping_phrases_count_once(self):
        ks = KeywordSet(["هيئة الرقابة النووية والإشعاعية", "الرقابة النووية", "هيئة الرقابة"])
        assert ks.count(normalize_for_match("هيئة الرقابة النووية والإشعاعية تعلن")) == 1


class TestClassifierRegressions:
    @pytest.mark.parametrize("title", [
        "Rain warning in Cairo",
        "الرئيس اللبناني يقتلع جذور الفساد",
        "Stock run on bank",
    ])
    def test_not_military(self, title):
        assert classify(title)[0] != "military"

    def test_said_is_not_humanitarian(self):
        assert classify("Minister said talks will resume")[0] == "diplomatic"

    def test_deadline_is_not_critical(self):
        assert classify("Deadline passes for Gaza deal")[1] != "critical"


class TestCleaning:
    def test_entities_and_tags_are_removed(self):
        raw = "مباشر: &amp;quot;بقوة فور إعطاء الضوء الأخضر&amp;quot; <b>الشرق الأوسط</b>"
        assert clean_text(raw) == 'مباشر: "بقوة فور إعطاء الضوء الأخضر" الشرق الأوسط'

    def test_cap(self):
        assert clean_text("x" * 50, cap=10) == "x" * 10

    def test_arabic_normalisation(self):
        assert normalize_for_match("الإشعاعيّة") == normalize_for_match("الاشعاعيه")

    def test_source_suffix_split_only_when_it_matches_the_publisher(self):
        assert split_source_suffix("خبر عاجل - سكاي نيوز عربية", "سكاي نيوز عربية") == ("خبر عاجل", "سكاي نيوز عربية")
        # شرطة داخل العنوان لا تُقتطع حين لا تطابق المصدر المعروف
        assert split_source_suffix("Iran - US talks resume", "Reuters") == ("Iran - US talks resume", "")
