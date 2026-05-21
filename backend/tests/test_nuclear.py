"""
رصد - اختبارات /api/nuclear (v1.2)
"""
import pytest


@pytest.mark.asyncio
async def test_nuclear_facilities(client):
    r = await client.get("/api/nuclear/facilities")
    assert r.status_code == 200
    data = r.json()
    assert "facilities" in data
    assert data["total"] >= 5


@pytest.mark.asyncio
async def test_nuclear_filter_country(client):
    r = await client.get("/api/nuclear/facilities", params={"country": "IR"})
    assert r.status_code == 200
    for f in r.json()["facilities"]:
        assert f["country_code"] == "IR"


@pytest.mark.asyncio
async def test_nuclear_stats(client):
    r = await client.get("/api/nuclear/stats")
    assert r.status_code == 200
    data = r.json()
    assert "by_country" in data
    assert "by_type" in data
