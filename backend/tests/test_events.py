"""
رصد - اختبارات /api/events/* بما فيها /country-index (v1.3)
"""
import pytest


@pytest.mark.asyncio
async def test_events_root(client, seed_events):
    r = await client.get("/api/events/")
    assert r.status_code == 200
    data = r.json()
    assert "events" in data and "total" in data
    titles = [e["title"] for e in data["events"]]
    assert any("نباطيم" in t for t in titles)


@pytest.mark.asyncio
async def test_events_filter_by_category(client, seed_events):
    r = await client.get("/api/events/", params={"category": "military"})
    assert r.status_code == 200
    for e in r.json()["events"]:
        if e["source"] == "test":
            assert e["category"] == "military"


@pytest.mark.asyncio
async def test_events_filter_by_country(client, seed_events):
    r = await client.get("/api/events/", params={"country_code": "IL"})
    assert r.status_code == 200
    for e in r.json()["events"]:
        if e["source"] == "test":
            assert e["country_code"] == "IL"


@pytest.mark.asyncio
async def test_events_map(client, seed_events):
    r = await client.get("/api/events/map")
    assert r.status_code == 200
    arr = r.json()
    assert isinstance(arr, list)
    for e in arr:
        assert e["latitude"] is not None
        assert e["longitude"] is not None


@pytest.mark.asyncio
async def test_stats(client, seed_events):
    r = await client.get("/api/events/stats")
    assert r.status_code == 200
    data = r.json()
    for key in ("total", "categories", "severities", "countries", "sources", "escalation_index"):
        assert key in data
    assert 0 <= data["escalation_index"] <= 100


@pytest.mark.asyncio
async def test_country_index(client, seed_events):
    """v1.3 — مؤشر استخبارات الدول"""
    r = await client.get("/api/events/country-index", params={"hours": 72, "top": 10})
    assert r.status_code == 200
    data = r.json()
    assert "ranking" in data and "total_countries" in data
    assert data["total_countries"] >= 3  # IL, IR, SY من seed_events
    # أعلى دولة لا بد أن تكون IL (حدث critical + HIGH = أعلى وزن)
    top = data["ranking"][0]
    assert top["country_code"] == "IL"
    assert top["score"] == 100.0
    # ترتيب تنازلي
    scores = [c["score"] for c in data["ranking"]]
    assert scores == sorted(scores, reverse=True)
    # حقول التحليل موجودة
    for field in ("country_code", "country_name", "score", "total", "by_severity", "by_category"):
        assert field in top


@pytest.mark.asyncio
async def test_country_index_validation(client):
    """hours out of range → 422"""
    r = await client.get("/api/events/country-index", params={"hours": 9999})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_stats_escalation_trend_in_one_query(client, seed_events):
    """الفترة السابقة والسلسلة الزمنية تأتيان مع المؤشر من استعلام واحد."""
    r = await client.get("/api/events/stats", params={"hours": 24})
    assert r.status_code == 200
    data = r.json()
    assert "escalation_prev" in data and "escalation_delta" in data
    series = data["escalation_series"]
    assert len(series) == 8
    assert all(0 <= p["value"] <= 100 for p in series)
    assert series == sorted(series, key=lambda p: p["t"]), "الشرائح بترتيب زمني تصاعدي"
    # seed_events: حدثان عسكريان (حرج + مرتفع) من ثلاثة خلال 24 ساعة
    assert data["escalation_index"] == 66.7
    assert round(data["escalation_index"] - data["escalation_prev"], 1) == data["escalation_delta"]


@pytest.mark.asyncio
async def test_map_respects_limit_and_collapses_stories(client, seed_events):
    r = await client.get("/api/events/map", params={"limit": 2})
    assert r.status_code == 200
    arr = r.json()
    assert len(arr) <= 2
    assert len({e["cluster_id"] for e in arr}) == len(arr), "ممثّل واحد لكل قصة"


@pytest.mark.asyncio
async def test_map_rejects_out_of_range_limit(client):
    r = await client.get("/api/events/map", params={"limit": 5000})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_latest_returns_newest_first(client, seed_events):
    r = await client.get("/api/events/latest", params={"limit": 5})
    assert r.status_code == 200
    arr = r.json()
    assert len(arr) <= 5
    dates = [e["event_date"] for e in arr]
    assert dates == sorted(dates, reverse=True)


@pytest.mark.asyncio
async def test_timeline_bounds_limit(client, seed_events):
    r = await client.get("/api/events/timeline", params={"hours": 48, "limit": 2})
    assert r.status_code == 200
    assert len(r.json()) <= 2
    assert (await client.get("/api/events/timeline", params={"limit": 0})).status_code == 422
