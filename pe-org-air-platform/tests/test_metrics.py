"""
Tests for Prometheus Metrics — Task 10.6.

Verifies metric definitions, decorator behavior for success/error paths,
and duration observation using prometheus_client REGISTRY introspection.
"""

import pytest
import asyncio
from unittest.mock import patch
from prometheus_client import Counter, Histogram, REGISTRY

from app.services.observability.metrics import (
    MCP_TOOL_CALLS,
    MCP_TOOL_DURATION,
    AGENT_INVOCATIONS,
    AGENT_DURATION,
    HITL_APPROVALS,
    CS_CLIENT_CALLS,
    track_mcp_tool,
    track_agent,
    track_cs_client,
)


# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------

class TestMetricDefinitions:

    def test_mcp_tool_calls_is_counter(self):
        assert isinstance(MCP_TOOL_CALLS, Counter)

    def test_mcp_tool_duration_is_histogram(self):
        assert isinstance(MCP_TOOL_DURATION, Histogram)

    def test_agent_invocations_is_counter(self):
        assert isinstance(AGENT_INVOCATIONS, Counter)

    def test_agent_duration_is_histogram(self):
        assert isinstance(AGENT_DURATION, Histogram)

    def test_hitl_approvals_is_counter(self):
        assert isinstance(HITL_APPROVALS, Counter)

    def test_cs_client_calls_is_counter(self):
        assert isinstance(CS_CLIENT_CALLS, Counter)

    def test_mcp_tool_calls_labels(self):
        assert MCP_TOOL_CALLS._labelnames == ("tool_name", "status")

    def test_agent_invocations_labels(self):
        assert AGENT_INVOCATIONS._labelnames == ("agent_name", "status")

    def test_hitl_approvals_labels(self):
        assert HITL_APPROVALS._labelnames == ("reason", "decision")

    def test_cs_client_calls_labels(self):
        assert CS_CLIENT_CALLS._labelnames == ("service", "endpoint", "status")


# ---------------------------------------------------------------------------
# track_mcp_tool decorator
# ---------------------------------------------------------------------------

class TestTrackMcpTool:

    @pytest.mark.asyncio
    async def test_success_increments_counter(self):
        @track_mcp_tool("test_tool")
        async def my_tool():
            return "ok"

        before = MCP_TOOL_CALLS.labels(tool_name="test_tool", status="success")._value.get()
        result = await my_tool()
        after = MCP_TOOL_CALLS.labels(tool_name="test_tool", status="success")._value.get()

        assert result == "ok"
        assert after == before + 1

    @pytest.mark.asyncio
    async def test_error_increments_error_counter(self):
        @track_mcp_tool("fail_tool")
        async def my_tool():
            raise ValueError("boom")

        before = MCP_TOOL_CALLS.labels(tool_name="fail_tool", status="error")._value.get()
        with pytest.raises(ValueError, match="boom"):
            await my_tool()
        after = MCP_TOOL_CALLS.labels(tool_name="fail_tool", status="error")._value.get()

        assert after == before + 1

    @pytest.mark.asyncio
    async def test_duration_observed(self):
        @track_mcp_tool("timed_tool")
        async def my_tool():
            await asyncio.sleep(0.01)
            return 42

        result = await my_tool()
        assert result == 42
        # Check histogram was observed by inspecting collected samples
        metrics = list(MCP_TOOL_DURATION.labels(tool_name="timed_tool").collect())
        assert any(s.value > 0 for m in metrics for s in m.samples if s.name.endswith('_count'))


# ---------------------------------------------------------------------------
# track_agent decorator
# ---------------------------------------------------------------------------

class TestTrackAgent:

    @pytest.mark.asyncio
    async def test_success_increments_counter(self):
        @track_agent("test_agent")
        async def my_agent():
            return {"state": "done"}

        before = AGENT_INVOCATIONS.labels(agent_name="test_agent", status="success")._value.get()
        result = await my_agent()
        after = AGENT_INVOCATIONS.labels(agent_name="test_agent", status="success")._value.get()

        assert result == {"state": "done"}
        assert after == before + 1

    @pytest.mark.asyncio
    async def test_error_increments_error_counter(self):
        @track_agent("fail_agent")
        async def my_agent():
            raise RuntimeError("agent crashed")

        before = AGENT_INVOCATIONS.labels(agent_name="fail_agent", status="error")._value.get()
        with pytest.raises(RuntimeError, match="agent crashed"):
            await my_agent()
        after = AGENT_INVOCATIONS.labels(agent_name="fail_agent", status="error")._value.get()

        assert after == before + 1

    @pytest.mark.asyncio
    async def test_duration_observed(self):
        @track_agent("timed_agent")
        async def my_agent():
            await asyncio.sleep(0.01)
            return "done"

        await my_agent()
        metrics = list(AGENT_DURATION.labels(agent_name="timed_agent").collect())
        assert any(s.value > 0 for m in metrics for s in m.samples if s.name.endswith('_count'))


# ---------------------------------------------------------------------------
# track_cs_client decorator
# ---------------------------------------------------------------------------

class TestTrackCsClient:

    @pytest.mark.asyncio
    async def test_success_increments_counter(self):
        @track_cs_client("cs1", "/companies")
        async def call_cs1():
            return [{"id": "c1"}]

        before = CS_CLIENT_CALLS.labels(service="cs1", endpoint="/companies", status="success")._value.get()
        result = await call_cs1()
        after = CS_CLIENT_CALLS.labels(service="cs1", endpoint="/companies", status="success")._value.get()

        assert result == [{"id": "c1"}]
        assert after == before + 1

    @pytest.mark.asyncio
    async def test_error_increments_error_counter(self):
        @track_cs_client("cs3", "/assessments")
        async def call_cs3():
            raise ConnectionError("timeout")

        before = CS_CLIENT_CALLS.labels(service="cs3", endpoint="/assessments", status="error")._value.get()
        with pytest.raises(ConnectionError, match="timeout"):
            await call_cs3()
        after = CS_CLIENT_CALLS.labels(service="cs3", endpoint="/assessments", status="error")._value.get()

        assert after == before + 1

    @pytest.mark.asyncio
    async def test_preserves_function_name(self):
        @track_cs_client("cs2", "/signals")
        async def fetch_signals():
            return []

        assert fetch_signals.__name__ == "fetch_signals"


# ---------------------------------------------------------------------------
# HITL Approvals (manual counter usage)
# ---------------------------------------------------------------------------

class TestHitlApprovals:

    def test_can_increment_hitl_approvals(self):
        before = HITL_APPROVALS.labels(reason="budget_override", decision="approved")._value.get()
        HITL_APPROVALS.labels(reason="budget_override", decision="approved").inc()
        after = HITL_APPROVALS.labels(reason="budget_override", decision="approved")._value.get()

        assert after == before + 1

    def test_hitl_denied(self):
        before = HITL_APPROVALS.labels(reason="score_adjustment", decision="denied")._value.get()
        HITL_APPROVALS.labels(reason="score_adjustment", decision="denied").inc()
        after = HITL_APPROVALS.labels(reason="score_adjustment", decision="denied")._value.get()

        assert after == before + 1
