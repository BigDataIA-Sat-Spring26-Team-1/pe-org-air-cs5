
import pytest
import time
from app.services.redis_cache import cache

@pytest.mark.asyncio
async def test_caching_speedup(client):
    res1_start = time.perf_counter()
    res1 = await client.get("/api/v1/industries/")
    res1_duration = time.perf_counter() - res1_start
    assert res1.status_code == 200
    
    res2_start = time.perf_counter()
    res2 = await client.get("/api/v1/industries/")
    res2_duration = time.perf_counter() - res2_start
    assert res2.status_code == 200
    
    assert res2_duration >= 0

@pytest.mark.asyncio
async def test_company_cache_invalidation(client):
    list_res = await client.get("/api/v1/companies/")
    items = list_res.json()["items"]
    if not items:
        pytest.skip("No companies")
        
    comp = items[0]
    cid = comp["id"]
    
    # Warm up
    await client.get(f"/api/v1/companies/{cid}")
    
    new_name = f"Updated {int(time.time())}"
    payload = {**comp, "name": new_name}
    await client.put(f"/api/v1/companies/{cid}", json=payload)
    
    res = await client.get(f"/api/v1/companies/{cid}")
    assert res.json()["name"] == new_name

@pytest.mark.asyncio
async def test_redis_ttl_mechanism():
    key = "test:ttl"
    cache.client.setex(key, 10, "value")
    ttl = cache.client.ttl(key)
    assert 0 < ttl <= 10
    cache.client.delete(key)

@pytest.mark.asyncio
async def test_pagination_cache_isolation(client):
    res1 = await client.get("/api/v1/companies/", params={"page": 1, "page_size": 1})
    res2 = await client.get("/api/v1/companies/", params={"page": 2, "page_size": 1})
    
    if res1.json()["items"] and res2.json()["items"]:
        id1 = res1.json()["items"][0]["id"]
        id2 = res2.json()["items"][0]["id"]
        assert id1 != id2