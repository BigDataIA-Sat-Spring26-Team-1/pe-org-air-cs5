
import pytest
from uuid import uuid4

@pytest.mark.asyncio
async def test_assessments_full_flow(client):
    ind_res = await client.get("/api/v1/industries/")
    ind_id = ind_res.json()[0]["id"]
    
    comp_payload = {"name": "AAA Assessment Test Corp", "ticker": f"AT{uuid4().hex[:4]}".upper(), "industry_id": ind_id}
    comp_res = await client.post("/api/v1/companies/", json=comp_payload)
    company_id = comp_res.json()["id"]

    assess_payload = {
        "company_id": company_id,
        "assessment_type": "due_diligence",
        "primary_assessor": "Test Case"
    }
    res = await client.post("/api/v1/assessments", json=assess_payload)
    assert res.status_code == 201
    assessment_id = res.json()["id"]

    res = await client.get(f"/api/v1/assessments?company_id={company_id}")
    assert res.status_code == 200
    items = res.json()["items"]
    print("Assessment list items:", items)
    assert any(str(a["id"]) == str(assessment_id) for a in items)

    res = await client.get(f"/api/v1/assessments/{assessment_id}")
    assert res.status_code == 200

    score_payload = {
        "assessment_id": assessment_id,
        "dimension": "talent",
        "score": 85.0,
        "evidence_count": 5
    }
    res = await client.post(f"/api/v1/assessments/{assessment_id}/scores", json=score_payload)
    assert res.status_code == 201
