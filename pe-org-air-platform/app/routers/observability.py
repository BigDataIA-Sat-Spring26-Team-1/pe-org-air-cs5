"""
Observability API — exposes Prometheus counter snapshots as JSON for the frontend.

Endpoint:
  GET /api/v1/observability/metrics-snapshot
"""
from fastapi import APIRouter
from typing import Dict, Any
import structlog

router = APIRouter()
logger = structlog.get_logger()

TRACKED_METRICS = {
    "mcp_tool_calls_total",
    "agent_invocations_total",
    "hitl_approvals_total",
    "cs_client_calls_total",
}


@router.get("/metrics-snapshot")
async def get_metrics_snapshot() -> Dict[str, Any]:
    """
    Collect current Prometheus counter values and return structured JSON.

    Groups samples by metric family and label combination so the frontend
    can render tables without parsing the Prometheus text format.
    """
    try:
        from prometheus_client import REGISTRY

        snapshot: Dict[str, Any] = {
            "mcp_tool_calls": {},
            "agent_invocations": {},
            "hitl_approvals": {},
            "cs_client_calls": {},
        }

        for metric_family in REGISTRY.collect():
            name = metric_family.name

            if name == "mcp_tool_calls_total":
                for sample in metric_family.samples:
                    if sample.name.endswith("_total"):
                        tool = sample.labels.get("tool_name", "unknown")
                        status = sample.labels.get("status", "unknown")
                        if tool not in snapshot["mcp_tool_calls"]:
                            snapshot["mcp_tool_calls"][tool] = {"success": 0, "error": 0}
                        snapshot["mcp_tool_calls"][tool][status] = int(sample.value)

            elif name == "agent_invocations_total":
                for sample in metric_family.samples:
                    if sample.name.endswith("_total"):
                        agent = sample.labels.get("agent_name", "unknown")
                        status = sample.labels.get("status", "unknown")
                        if agent not in snapshot["agent_invocations"]:
                            snapshot["agent_invocations"][agent] = {"success": 0, "error": 0}
                        snapshot["agent_invocations"][agent][status] = int(sample.value)

            elif name == "hitl_approvals_total":
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

            elif name == "cs_client_calls_total":
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
