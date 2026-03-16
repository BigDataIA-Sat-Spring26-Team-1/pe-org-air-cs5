
import pytest
import asyncio
import time
from uuid import uuid4

@pytest.mark.asyncio
async def test_concurrent_read_requests(client):
    tasks = [client.get("/api/v1/industries/") for _ in range(10)]
    responses = await asyncio.gather(*tasks)
    
    for res in responses:
        assert res.status_code == 200
        assert len(res.json()) > 0

@pytest.mark.asyncio
async def test_concurrent_write_operations(client):
    ind_res = await client.get("/api/v1/industries/")
    industry_id = ind_res.json()[0]["id"]
    
    unique_id = uuid4().hex[:4]
    payloads = [
        {
            "name": f"Concurrent {i}-{unique_id}",
            "ticker": f"C{i}{unique_id}".upper()[:5],
            "industry_id": industry_id
        }
        for i in range(5)
    ]
    
    tasks = [client.post("/api/v1/companies/", json=p) for p in payloads]
    responses = await asyncio.gather(*tasks)
    
    for res in responses:
        assert res.status_code == 201

@pytest.mark.asyncio
async def test_interleaved_read_write(client):
    ind_res = await client.get("/api/v1/industries/")
    industry_id = ind_res.json()[0]["id"]
    
    payload = {
        "name": f"Interleave {int(time.time())}",
        "ticker": "INTLV",
        "industry_id": industry_id
    }
    
    res_write, res_read = await asyncio.gather(
        client.post("/api/v1/companies/", json=payload),
        client.get("/api/v1/companies/")
    )
    
    assert res_write.status_code == 201
    assert res_read.status_code == 200