"""
Tests for CS5 MCP Server integration.

Covers:
  - MCPToolCaller HTTP client (used by LangGraph agents to call MCP tools)
  - MCP tool wrappers (get_org_air_score, get_evidence, get_justification, get_gap_analysis)
  - Error handling / non-200 responses
  - MCP server HTTP endpoints (live — auto-skipped if server not running)

Note: langchain_openai and langchain_anthropic are only available inside Docker.
      Unit tests mock at the httpx level so no LLM calls are made.
"""
import json
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Skip entire module if app-stack deps are absent (local dev without Docker)
pytest.importorskip("langchain_openai", reason="app stack not installed locally — run inside Docker")
import app.agents.specialists  # noqa: E402 — must import after importorskip to resolve patch paths


# ── helpers ───────────────────────────────────────────────────────────────────
def _make_httpx_response(data: dict, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = data
    if status >= 400:
        resp.raise_for_status = MagicMock(side_effect=Exception(f"HTTP {status}"))
    else:
        resp.raise_for_status = MagicMock()
    return resp


def _make_score_response(org_air: float = 78.5) -> dict:
    return {
        "result": json.dumps({
            "company_id": "NVDA",
            "org_air": org_air,
            "vr_score": 82.0,
            "hr_score": 75.0,
            "synergy_score": 68.0,
        })
    }


def _make_gap_analysis_response() -> dict:
    return {
        "result": json.dumps({
            "company_id": "NVDA",
            "current_score": 78.5,
            "target_score": 85.0,
            "projected_ebitda_pct": 3.8,
            "gaps": [
                {"dimension": "ai_governance", "gap": 3.0},
                {"dimension": "culture", "gap": 2.5},
            ],
        })
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MCPToolCaller
# ═══════════════════════════════════════════════════════════════════════════════
class TestMCPToolCaller:
    async def test_call_tool_success(self):
        from app.agents.specialists import MCPToolCaller
        caller = MCPToolCaller(base_url="http://mcp-server:3001")
        mock_resp = _make_httpx_response({"result": '{"org_air": 78.5}'})
        with patch.object(caller.client, "post", new_callable=AsyncMock, return_value=mock_resp):
            result = await caller.call_tool("calculate_org_air_score", {"company_id": "NVDA"})
        assert '"org_air"' in result

    async def test_call_tool_posts_to_correct_endpoint(self):
        from app.agents.specialists import MCPToolCaller
        caller = MCPToolCaller(base_url="http://mcp-server:3001")
        mock_resp = _make_httpx_response({"result": "{}"})
        with patch.object(caller.client, "post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
            await caller.call_tool("get_portfolio_summary", {})
        mock_post.assert_awaited_once_with(
            "http://mcp-server:3001/tools/get_portfolio_summary",
            json={},
        )

    async def test_call_tool_raises_on_http_error(self):
        from app.agents.specialists import MCPToolCaller
        caller = MCPToolCaller(base_url="http://mcp-server:3001")
        mock_resp = _make_httpx_response({}, status=500)
        with patch.object(caller.client, "post", new_callable=AsyncMock, return_value=mock_resp):
            with pytest.raises(Exception):
                await caller.call_tool("calculate_org_air_score", {"company_id": "NVDA"})

    async def test_call_tool_returns_empty_dict_when_no_result_key(self):
        from app.agents.specialists import MCPToolCaller
        caller = MCPToolCaller(base_url="http://mcp-server:3001")
        mock_resp = _make_httpx_response({"status": "ok"})  # no 'result' key
        with patch.object(caller.client, "post", new_callable=AsyncMock, return_value=mock_resp):
            result = await caller.call_tool("health", {})
        assert result == "{}"

    async def test_call_tool_uses_env_default_url(self):
        """When no base_url passed, reads MCP_SERVER_URL from env."""
        import os
        with patch.dict(os.environ, {"MCP_SERVER_URL": "http://custom-mcp:9000"}):
            from app.agents.specialists import MCPToolCaller
            caller = MCPToolCaller()
        assert caller.base_url == "http://custom-mcp:9000"


# ═══════════════════════════════════════════════════════════════════════════════
# LangChain tool wrappers
# ═══════════════════════════════════════════════════════════════════════════════
class TestMCPToolWrappers:
    async def test_get_org_air_score_tool(self):
        from app.agents.specialists import get_org_air_score, mcp_client
        with patch.object(mcp_client, "call_tool", new_callable=AsyncMock,
                          return_value=json.dumps({"org_air": 81.0})) as mock_call:
            result = await get_org_air_score.ainvoke({"company_id": "AAPL"})
        mock_call.assert_awaited_once_with("calculate_org_air_score", {"company_id": "AAPL"})
        data = json.loads(result)
        assert data["org_air"] == 81.0

    async def test_get_evidence_tool(self):
        from app.agents.specialists import get_evidence, mcp_client
        evidence = [{"dimension": "talent", "content": "Strong hiring"}]
        with patch.object(mcp_client, "call_tool", new_callable=AsyncMock,
                          return_value=json.dumps(evidence)):
            result = await get_evidence.ainvoke({"company_id": "MSFT", "dimension": "talent"})
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert parsed[0]["dimension"] == "talent"

    async def test_get_justification_tool(self):
        from app.agents.specialists import get_justification, mcp_client
        just = {"dimension": "data_infrastructure", "score": 75.0, "justification": "Robust pipelines."}
        with patch.object(mcp_client, "call_tool", new_callable=AsyncMock,
                          return_value=json.dumps(just)):
            result = await get_justification.ainvoke(
                {"company_id": "NVDA", "dimension": "data_infrastructure"}
            )
        parsed = json.loads(result)
        assert parsed["dimension"] == "data_infrastructure"

    async def test_get_gap_analysis_tool(self):
        from app.agents.specialists import get_gap_analysis, mcp_client
        gap = {"current_score": 78.5, "target_score": 85.0, "projected_ebitda_pct": 3.8, "gaps": []}
        with patch.object(mcp_client, "call_tool", new_callable=AsyncMock,
                          return_value=json.dumps(gap)):
            result = await get_gap_analysis.ainvoke({"company_id": "NVDA", "target": 85.0})
        parsed = json.loads(result)
        assert parsed["projected_ebitda_pct"] == 3.8


# ═══════════════════════════════════════════════════════════════════════════════
# MCP Server HTTP endpoints (live — auto-skipped if server not running)
# ═══════════════════════════════════════════════════════════════════════════════
class TestMCPServerHTTP:
    """
    Integration tests against the real MCP server at localhost:3001.
    Auto-skipped when Docker is not running.
    """

    @pytest.fixture(autouse=True)
    async def check_server(self):
        import httpx
        try:
            async with httpx.AsyncClient(timeout=3.0) as c:
                resp = await c.get("http://localhost:3001/health")
                if resp.status_code != 200:
                    pytest.skip("MCP server not healthy")
        except Exception:
            pytest.skip("MCP server not reachable at localhost:3001")

    async def test_health_endpoint_returns_200(self):
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as c:
            resp = await c.get("http://localhost:3001/health")
        assert resp.status_code == 200

    async def test_calculate_org_air_score_tool(self):
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as c:
            resp = await c.post(
                "http://localhost:3001/tools/calculate_org_air_score",
                json={"company_id": "NVDA"},
            )
        assert resp.status_code == 200
        result = json.loads(resp.json()["result"])
        assert "org_air" in result
        assert 0 <= result["org_air"] <= 100

    async def test_get_portfolio_summary_tool(self):
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as c:
            resp = await c.post(
                "http://localhost:3001/tools/get_portfolio_summary",
                json={},
            )
        assert resp.status_code == 200
        assert "result" in resp.json()

    async def test_run_gap_analysis_tool(self):
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as c:
            resp = await c.post(
                "http://localhost:3001/tools/run_gap_analysis",
                json={"company_id": "NVDA", "target_org_air": 85.0},
            )
        assert resp.status_code == 200
        result = json.loads(resp.json()["result"])
        assert any(k in result for k in ("projected_ebitda_pct", "gap", "gaps"))

    async def test_batch_generate_justifications_returns_all_dimensions(self):
        import httpx
        async with httpx.AsyncClient(timeout=60.0) as c:
            resp = await c.post(
                "http://localhost:3001/tools/batch_generate_justifications",
                json={"company_id": "NVDA"},
            )
        assert resp.status_code == 200
        result = json.loads(resp.json()["result"])
        expected_dims = {
            "data_infrastructure", "talent", "use_case_portfolio",
            "technology_stack", "ai_governance", "leadership", "culture",
        }
        assert expected_dims.issubset(set(result.keys()))
