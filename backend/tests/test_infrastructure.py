"""
رصد - اختبارات /api/infrastructure (قواعد + خطوط أنابيب)

بيانات ثابتة، لذا الاختبار يتحقّق من البنية والفلاتر دون قاعدة بيانات.
"""
import pytest


@pytest.mark.asyncio
async def test_bases_list(client):
    r = await client.get("/api/infrastructure/bases")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 15  # 19 قاعدة فعلياً
    assert isinstance(data["bases"], list)
    base = data["bases"][0]
    for field in ("id", "name_ar", "name_en", "country", "country_code", "operator", "type", "latitude", "longitude"):
        assert field in base, f"missing {field}"


@pytest.mark.asyncio
async def test_bases_filter_by_country(client):
    r = await client.get("/api/infrastructure/bases", params={"country": "IL"})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    for b in data["bases"]:
        assert b["country_code"] == "IL"


@pytest.mark.asyncio
async def test_bases_filter_by_operator(client):
    r = await client.get("/api/infrastructure/bases", params={"operator": "US"})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 5
    for b in data["bases"]:
        assert "us" in b["operator"].lower()


@pytest.mark.asyncio
async def test_bases_filter_by_type(client):
    r = await client.get("/api/infrastructure/bases", params={"base_type": "naval"})
    assert r.status_code == 200
    for b in r.json()["bases"]:
        assert b["type"] == "naval"


@pytest.mark.asyncio
async def test_pipelines_list(client):
    r = await client.get("/api/infrastructure/pipelines")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 8
    p = data["pipelines"][0]
    assert "coordinates" in p
    assert isinstance(p["coordinates"], list)
    assert len(p["coordinates"]) >= 2
    # كل إحداثية [lat, lng]
    for lat, lng in p["coordinates"]:
        assert -90 <= lat <= 90
        assert -180 <= lng <= 180


@pytest.mark.asyncio
async def test_pipelines_filter_oil(client):
    r = await client.get("/api/infrastructure/pipelines", params={"pipeline_type": "oil"})
    assert r.status_code == 200
    for p in r.json()["pipelines"]:
        assert p["type"] == "oil"


@pytest.mark.asyncio
async def test_pipelines_filter_gas(client):
    r = await client.get("/api/infrastructure/pipelines", params={"pipeline_type": "gas"})
    assert r.status_code == 200
    for p in r.json()["pipelines"]:
        assert p["type"] == "gas"
