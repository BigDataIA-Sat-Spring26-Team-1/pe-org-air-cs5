"""
Observability API — exposes Prometheus counter snapshots as JSON for the frontend.

Merges metrics from:
  - API process registry (agent invocations, HITL approvals, CS client calls)
  - MCP server process via /metrics-json HTTP endpoint (MCP tool calls)

Endpoint:
  GET /api/v1/observability/metrics-snapshot
"""
from fastapi import APIRouter
from typing import Dict, Any
import os
import httpx
import structlog

router = APIRouter()
logger = structlog.get_logger()

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:3001")


@router.get("/metrics-snapshot")
async def get_metrics_snapshot() -> Dict[str, Any]:
    """
    Collect current Prometheus counter values and return structured JSON.

    Groups samples by metric family and label combination so the frontend
    can render tables without parsing the Prometheus text format.
    Merges MCP tool call metrics fetched from the MCP server process.
    """
    try:
        from prometheus_client import REGISTRY

        snapshot: Dict[str, Any] = {
            "mcp_tool_calls": {},
            "agent_invocations": {},
            "hitl_approvals": {},
            "cs_client_calls": {},
        }

        # Fetch MCP tool call metrics from the MCP server (separate process)
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                mcp_resp = await client.get(f"{MCP_SERVER_URL}/metrics-json")
                if mcp_resp.status_code == 200:
                    mcp_data = mcp_resp.json()
                    snapshot["mcp_tool_calls"] = mcp_data.get("mcp_tool_calls", {})
        except Exception as e:
            logger.warning("mcp_metrics_fetch_failed", error=str(e))

        for metric_family in REGISTRY.collect():
            name = metric_family.name

            # prometheus_client 0.8+ strips _total from family.name for Counters
            if name == "agent_invocations":
                for sample in metric_family.samples:
                    if sample.name.endswith("_total"):
                        agent = sample.labels.get("agent_name", "unknown")
                        status = sample.labels.get("status", "unknown")
                        if agent not in snapshot["agent_invocations"]:
                            snapshot["agent_invocations"][agent] = {"success": 0, "error": 0}
                        snapshot["agent_invocations"][agent][status] = int(sample.value)

            elif name == "hitl_approvals":
                for sample in metric_family.samples:
                    if sample.name.endswith("_total"):
                        reason = sample.labels.get("reason", "unknown")
                        decision = sample.labels.get("decision", "unknown")
                        key = f"{reason}:{decision}"
                        snapshot["hitl_approvals"][key] = {
                            "reason": reason,
                            "decision": decision,
                            "count": int(sample.value),
                        }

            elif name == "cs_client_calls":
                for sample in metric_family.samples:
                    if sample.name.endswith("_total"):
                        service = sample.labels.get("service", "unknown")
                        endpoint = sample.labels.get("endpoint", "unknown")
                        status = sample.labels.get("status", "unknown")
                        key = f"{service}:{endpoint}"
                        if key not in snapshot["cs_client_calls"]:
                            snapshot["cs_client_calls"][key] = {
                                "service": service,
                                "endpoint": endpoint,
                                "success": 0,
                                "error": 0,
                            }
                        snapshot["cs_client_calls"][key][status] = int(sample.value)

        return snapshot

    except Exception as e:
        logger.error("metrics_snapshot_failed", error=str(e))
        # Return empty structure so frontend renders gracefully even before any metrics are recorded
        return {
            "mcp_tool_calls": {},
            "agent_invocations": {},
            "hitl_approvals": {},
            "cs_client_calls": {},
        }
