
import pytest
from uuid import uuid4

@pytest.mark.asyncio
async def test_full_company_flow(client):
    ind_res = await client.get("/api/v1/industries/")
    assert ind_res.status_code == 200
    ind_id = ind_res.json()[0]["id"]
    
    ticker = f"TC{uuid4().hex[:4]}".upper()
    payload = {"name": "AAA Test", "ticker": ticker, "industry_id": ind_id}
    
    res = await client.post("/api/v1/companies/", json=payload)
    assert res.status_code == 201
    cid = res.json()["id"]

    res = await client.get(f"/api/v1/companies/{cid}")
    assert res.status_code == 200
    assert str(res.json()["id"]) == str(cid)

    await client.delete(f"/api/v1/companies/{cid}")

@pytest.mark.asyncio
async def test_signals_endpoints(client):
    res = await client.get("/api/v1/signals/", params={"ticker": "MSFT", "category": "talent"})
    assert res.status_code in [200, 404, 422]

@pytest.mark.asyncio
async def test_system_endpoints(client):
    res = await client.get("/health")
    assert res.status_code == 200
    
    res = await client.get("/api/v1/metrics/summary")
    assert res.status_code == 200

@pytest.mark.asyncio
async def test_config_vars(client):
    res = await client.get("/api/v1/config/vars")
    assert res.status_code == 200
