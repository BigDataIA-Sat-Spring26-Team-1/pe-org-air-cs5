
import pytest
from uuid import uuid4

@pytest.mark.asyncio
async def test_health_check(client):
    res = await client.get("/health")
    assert res.status_code == 200

@pytest.mark.asyncio
async def test_root_endpoint(client):
    res = await client.get("/")
    assert res.status_code == 200

@pytest.mark.asyncio
async def test_company_creation(client):
    ind_res = await client.get("/api/v1/industries/")
    assert ind_res.status_code == 200
    ind_id = ind_res.json()[0]["id"]
    
    payload = {
        "name": f"Test Co {uuid4().hex[:6]}",
        "ticker": "TEST",
        "industry_id": ind_id
    }
    
    res = await client.post("/api/v1/companies/", json=payload)
    assert res.status_code == 201