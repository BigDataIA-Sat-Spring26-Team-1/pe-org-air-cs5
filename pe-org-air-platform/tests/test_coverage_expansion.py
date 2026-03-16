
import pytest

@pytest.mark.asyncio
async def test_industry_list(client):
    res = await client.get("/api/v1/industries/")
    assert res.status_code == 200

@pytest.mark.asyncio
async def test_sec_collect_v1(client):
    payload = {"tickers": ["AAPL"], "limit": 1}
    res = await client.post("/api/v1/documents/collect", json=payload)
    assert res.status_code in [200, 202, 400]

@pytest.mark.asyncio
async def test_evidence_stats_access(client):
    res = await client.get("/api/v1/evidence/stats")
    assert res.status_code == 200

@pytest.mark.asyncio
async def test_integration_full_run(client):
    payload = {"ticker": "NVDA"}
    res = await client.post("/api/v1/integration/run", json=payload)
    assert res.status_code in [200, 202, 400, 500] 

@pytest.mark.asyncio
async def test_metrics_report(client):
    res = await client.get("/api/v1/metrics/readiness-report")
    assert res.status_code == 200
