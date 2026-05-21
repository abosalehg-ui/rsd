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
