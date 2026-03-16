
import pytest
import time
from uuid import UUID

@pytest.mark.asyncio
class TestApplicationLogicFlow:
    industry_id = None
    company_id = None
    assessment_id = None

    async def test_01_industries(self, client):
        res = await client.get("/api/v1/industries/")
        assert res.status_code == 200
        TestApplicationLogicFlow.industry_id = res.json()[0]["id"]

    async def test_02_companies(self, client):
        payload = {
            "name": f"AAA Logic Flow {int(time.time())}",
            "ticker": "LF",
            "industry_id": TestApplicationLogicFlow.industry_id
        }
        res = await client.post("/api/v1/companies/", json=payload)
        assert res.status_code == 201
        TestApplicationLogicFlow.company_id = res.json()["id"]

        res = await client.get("/api/v1/companies/")
        ids = [str(c["id"]) for c in res.json()["items"]]
        assert str(TestApplicationLogicFlow.company_id) in ids

    async def test_03_assessments(self, client):
        payload = {
            "company_id": TestApplicationLogicFlow.company_id,
            "assessment_type": "due_diligence",
            "primary_assessor": "Pipeline"
        }
        res = await client.post("/api/v1/assessments", json=payload)
        assert res.status_code == 201
        TestApplicationLogicFlow.assessment_id = res.json()["id"]

    async def test_04_cleanup(self, client):
        res = await client.delete(f"/api/v1/companies/{TestApplicationLogicFlow.company_id}")
        assert res.status_code == 204