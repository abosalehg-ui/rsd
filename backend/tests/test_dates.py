"""رصد - اختبارات تحويل التواريخ المشترك.

كل الدوال يجب أن تعيد datetime **واعياً بالمنطقة الزمنية** — الخلط بين الواعي
والعاري كان يسبب مقارنات فاشلة في طبقة API.
"""
from datetime import datetime, timezone
from types import SimpleNamespace

from app.processors.dates import parse_compact, parse_entry_date, parse_iso, parse_ymd, utcnow


def _aware(dt):
    return dt.tzinfo is not None and dt.utcoffset() is not None


class TestUtcNow:
    def test_is_timezone_aware_utc(self):
        now = utcnow()
        assert _aware(now)
        assert now.tzinfo == timezone.utc


class TestParseIso:
    def test_parses_z_suffix(self):
        dt = parse_iso("2026-03-01T12:30:00Z")
        assert (dt.year, dt.month, dt.day, dt.hour) == (2026, 3, 1, 12)
        assert _aware(dt)

    def test_parses_explicit_offset_and_normalises_to_utc(self):
        dt = parse_iso("2026-03-01T15:00:00+03:00")
        assert dt.hour == 12
        assert dt.tzinfo == timezone.utc

    def test_naive_input_is_assumed_utc(self):
        assert _aware(parse_iso("2026-03-01T12:00:00"))

    def test_falls_back_to_now_on_garbage(self):
        assert _aware(parse_iso("not-a-date"))
        assert _aware(parse_iso(None))
        assert _aware(parse_iso(""))


class TestParseCompact:
    def test_parses_gdelt_stamp(self):
        dt = parse_compact("20260301T123000Z"[:14])
        assert _aware(dt)

    def test_parses_plain_fourteen_digits(self):
        dt = parse_compact("20260301123000")
        assert (dt.year, dt.month, dt.day, dt.hour, dt.minute) == (2026, 3, 1, 12, 30)

    def test_falls_back_on_short_or_bad_input(self):
        assert _aware(parse_compact("2026"))
        assert _aware(parse_compact(None))


class TestParseYmd:
    def test_parses_date_only(self):
        dt = parse_ymd("2026-03-01")
        assert (dt.year, dt.month, dt.day) == (2026, 3, 1)
        assert _aware(dt)

    def test_accepts_a_longer_timestamp_and_takes_the_date(self):
        assert parse_ymd("2026-03-01T09:00:00").day == 1

    def test_falls_back_on_bad_input(self):
        assert _aware(parse_ymd("nope"))
        assert _aware(parse_ymd(None))


class TestParseEntryDate:
    def test_uses_published_parsed(self):
        entry = SimpleNamespace(published_parsed=(2026, 3, 1, 12, 0, 0, 0, 0, 0))
        dt = parse_entry_date(entry)
        assert dt.year == 2026
        assert _aware(dt)

    def test_falls_back_to_updated_parsed(self):
        entry = SimpleNamespace(published_parsed=None, updated_parsed=(2026, 5, 2, 8, 0, 0, 0, 0, 0))
        assert parse_entry_date(entry).month == 5

    def test_falls_back_to_now_when_absent(self):
        assert _aware(parse_entry_date(SimpleNamespace()))

    def test_survives_a_malformed_time_tuple(self):
        entry = SimpleNamespace(published_parsed=("bad", "tuple"))
        assert isinstance(parse_entry_date(entry), datetime)
