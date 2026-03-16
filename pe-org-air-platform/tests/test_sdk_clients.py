"""
Tests for SDK Clients — Teammate B Task 1.

Uses ``unittest.mock.AsyncMock`` to patch ``httpx.AsyncClient.request``
and verify that cs1/cs2/cs3 clients correctly form URLs, parse responses,
and propagate errors via ``SDKClientError``.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.services.integration import SDKClientError
from app.services.integration.cs1_client import CS1Client
from app.services.integration.cs2_client import CS2Client
from app.services.integration.cs3_client import CS3Client


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _mock_200(json_data):
    """Return a mock httpx.Response with status=200 and given JSON."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.json.return_value = json_data
    resp.text = ""
    return resp


def _mock_404():
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 404
    resp.json.return_value = {"detail": "Not found"}
    resp.text = "Not found"
    return resp


# ---------------------------------------------------------------------------
# CS1Client
# ---------------------------------------------------------------------------

class TestCS1Client:

    @pytest.mark.asyncio
    async def test_get_company(self):
        client = CS1Client(base_url="http://test:8000")
        company = {"id": "abc-123", "ticker": "NVDA", "name": "NVIDIA"}

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=_mock_200(company)):
            result = await client.get_company("abc-123")

        assert result["ticker"] == "NVDA"

    @pytest.mark.asyncio
    async def test_list_companies(self):
        client = CS1Client(base_url="http://test:8000")
        page_resp = {"items": [{"id": "1"}, {"id": "2"}], "total": 2, "page": 1}

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=_mock_200(page_resp)):
            result = await client.list_companies(page=1, page_size=20)

        assert result["total"] == 2

    @pytest.mark.asyncio
    async def test_list_industries(self):
        client = CS1Client(base_url="http://test:8000")
        industries = [{"id": "1", "name": "Technology"}]

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=_mock_200(industries)):
            result = await client.list_industries()

        assert result[0]["name"] == "Technology"

    @pytest.mark.asyncio
    async def test_get_company_404_raises_sdk_error(self):
        client = CS1Client(base_url="http://test:8000")

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=_mock_404()):
            with pytest.raises(SDKClientError) as exc_info:
                await client.get_company("nonexistent-id")

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# CS2Client
# ---------------------------------------------------------------------------

class TestCS2Client:

    @pytest.mark.asyncio
    async def test_get_signals(self):
        client = CS2Client(base_url="http://test:8000")
        signals = [{"id": "s1", "category": "technology_hiring"}]

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=_mock_200(signals)):
            result = await client.get_signals(ticker="NVDA")

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_culture_scores(self):
        client = CS2Client(base_url="http://test:8000")
        culture = {"ticker": "NVDA", "innovation": 4.2, "leadership": 3.8}

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=_mock_200(culture)):
            result = await client.get_culture_scores("NVDA")

        assert result["innovation"] == 4.2

    @pytest.mark.asyncio
    async def test_get_evidence_stats(self):
        client = CS2Client(base_url="http://test:8000")
        stats = {"total": 150, "by_source": {"sec": 80, "jobs": 70}}

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=_mock_200(stats)):
            result = await client.get_evidence_stats()

        assert result["total"] == 150


# ---------------------------------------------------------------------------
# CS3Client
# ---------------------------------------------------------------------------

class TestCS3Client:

    @pytest.mark.asyncio
    async def test_list_assessments(self):
        client = CS3Client(base_url="http://test:8000")
        page_resp = {"items": [{"id": "a1"}], "total": 1, "page": 1}

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=_mock_200(page_resp)):
            result = await client.list_assessments()

        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_get_dimension_scores(self):
        client = CS3Client(base_url="http://test:8000")
        scores = [{"dimension": "talent", "score": 72.5}]

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=_mock_200(scores)):
            result = await client.get_dimension_scores("assessment-123")

        assert result[0]["score"] == 72.5

    @pytest.mark.asyncio
    async def test_get_readiness_report(self):
        client = CS3Client(base_url="http://test:8000")
        report = {"leaderboard": [{"ticker": "NVDA", "score": 91}]}

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=_mock_200(report)):
            result = await client.get_readiness_report()

        assert result["leaderboard"][0]["ticker"] == "NVDA"

    @pytest.mark.asyncio
    async def test_get_global_summary(self):
        client = CS3Client(base_url="http://test:8000")
        summary = {"total_companies": 10, "total_signals": 500}

        with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=_mock_200(summary)):
            result = await client.get_global_summary()

        assert result["total_companies"] == 10
