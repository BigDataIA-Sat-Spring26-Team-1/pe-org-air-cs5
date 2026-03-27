"""
Specialist Agents - Domain-specific agents for the due diligence workflow.
"""
from typing import Dict, Any
from datetime import datetime, timezone
import json
import os

import httpx
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.tools import tool
import structlog

from agents.state import DueDiligenceState
from app.services.memory import mem0_client

logger = structlog.get_logger()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class MCPToolCaller:
    def __init__(self, base_url: str = None):
        # In docker the api container sets MCP_SERVER_URL=http://mcp-server:3001.
        # Locally it falls back to localhost:3001 (same port the SSE server binds to).
        if base_url is None:
            base_url = os.getenv("MCP_SERVER_URL", "http://localhost:3001")
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        response = await self.client.post(
            f"{self.base_url}/tools/{tool_name}",
            json=arguments,
        )
        response.raise_for_status()
        return response.json().get("result", "{}")


mcp_client = MCPToolCaller()


@tool
async def get_org_air_score(company_id: str) -> str:
    """Calculate Org-AI-R score for a company."""
    return await mcp_client.call_tool("calculate_org_air_score", {"company_id": company_id})


@tool
async def get_evidence(company_id: str, dimension: str = "all") -> str:
    """Fetch evidence signals for a company."""
    return await mcp_client.call_tool("get_company_evidence", {"company_id": company_id, "dimension": dimension})


@tool
async def get_justification(company_id: str, dimension: str) -> str:
    """Generate a justification for a given dimension."""
    return await mcp_client.call_tool("generate_justification", {"company_id": company_id, "dimension": dimension})


@tool
async def get_gap_analysis(company_id: str, target: float) -> str:
    """Run gap analysis for a company against a target score."""
    return await mcp_client.call_tool("run_gap_analysis", {"company_id": company_id, "target_org_air": target})


class SECAnalysisAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
        self.tools = [get_evidence]

    async def analyze(self, state: DueDiligenceState) -> Dict[str, Any]:
        company_id = state["company_id"]

        # Recall any prior SEC/evidence findings for this company
        prior = await mem0_client.search_memory(
            "SEC filing evidence data infrastructure governance",
            company_id=company_id,
        )

        evidence_result = await get_evidence.ainvoke({"company_id": company_id, "dimension": "all"})
        findings = json.loads(evidence_result) if evidence_result else []

        # Persist findings so future runs can build on them
        await mem0_client.add_memory(
            f"SEC analysis for {company_id}: {len(findings)} evidence items found covering "
            "data_infrastructure, ai_governance, technology_stack.",
            company_id=company_id,
            metadata={"agent": "sec_analyst", "assessment_type": state.get("assessment_type", "full")},
        )

        content = f"SEC analysis complete for {company_id}"
        if prior:
            content += f" (recalled {len(prior)} prior memory entries)"

        return {
            "sec_analysis": {
                "company_id": company_id,
                "findings": findings,
                "dimensions_covered": ["data_infrastructure", "ai_governance", "technology_stack"],
                "prior_context": prior,
            },
            "messages": [
                {
                    "role": "assistant",
                    "content": content,
                    "agent_name": "sec_analyst",
                    "timestamp": _now_utc(),
                }
            ],
        }


class ScoringAgent:
    def __init__(self):
        self.llm = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0.2)
        self.tools = [get_org_air_score, get_justification]

    async def calculate(self, state: DueDiligenceState) -> Dict[str, Any]:
        company_id = state["company_id"]

        # Check if we have a prior score to compare against
        prior = await mem0_client.search_memory(
            "Org-AI-R score assessment result",
            company_id=company_id,
        )

        score_result = await get_org_air_score.ainvoke({"company_id": company_id})
        score_data = json.loads(score_result)
        org_air = score_data.get("org_air", 0.0)
        requires_approval = org_air > 85 or org_air < 40
        approval_reason = f"Score {org_air:.1f} outside normal range [40, 85]" if requires_approval else None

        # Store the score in memory for trend tracking across sessions
        await mem0_client.add_memory(
            f"Org-AI-R score for {company_id}: {org_air:.1f} "
            f"(VR={score_data.get('vr_score', 'N/A')}, HR={score_data.get('hr_score', 'N/A')}). "
            f"HITL required: {requires_approval}.",
            company_id=company_id,
            metadata={"agent": "scorer", "org_air": org_air},
        )

        content = (
            f"Scoring complete: Org-AI-R = {org_air:.1f}"
            + (" [REQUIRES APPROVAL]" if requires_approval else "")
        )
        if prior:
            content += f" | Prior context: {prior[0][:120]}"

        return {
            "scoring_result": score_data,
            "requires_approval": requires_approval,
            "approval_reason": approval_reason,
            "approval_status": "pending" if requires_approval else None,
            "messages": [
                {
                    "role": "assistant",
                    "content": content,
                    "agent_name": "scorer",
                    "timestamp": _now_utc(),
                }
            ],
        }


class EvidenceAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
        self.tools = [get_justification]

    async def justify(self, state: DueDiligenceState) -> Dict[str, Any]:
        company_id = state["company_id"]

        # Pull any prior justification context before generating new ones
        prior = await mem0_client.search_memory(
            "dimension justification evidence strength gaps",
            company_id=company_id,
        )

        dimensions = ["data_infrastructure", "talent", "use_case_portfolio"]
        justifications = {}
        for dim in dimensions:
            result = await get_justification.ainvoke({"company_id": company_id, "dimension": dim})
            justifications[dim] = json.loads(result)

        # Summarise and persist key justification findings
        dim_summary = ", ".join(
            f"{d}: score={j.get('score', 'N/A')}"
            for d, j in justifications.items()
            if isinstance(j, dict)
        )
        await mem0_client.add_memory(
            f"Evidence justifications for {company_id} — {dim_summary}.",
            company_id=company_id,
            metadata={"agent": "evidence_agent", "dimensions": dimensions},
        )

        return {
            "evidence_justifications": {
                "company_id": company_id,
                "justifications": justifications,
                "prior_context": prior,
            },
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Generated justifications for {len(justifications)} dimensions",
                    "agent_name": "evidence_agent",
                    "timestamp": _now_utc(),
                }
            ],
        }


class ValueCreationAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
        self.tools = [get_gap_analysis]

    async def plan(self, state: DueDiligenceState) -> Dict[str, Any]:
        company_id = state["company_id"]

        # Check for prior value creation plans or gap analysis results
        prior = await mem0_client.search_memory(
            "gap analysis value creation EBITDA initiatives",
            company_id=company_id,
        )

        gap_result = await get_gap_analysis.ainvoke({"company_id": company_id, "target": 80.0})
        gap_data = json.loads(gap_result)
        projected_impact = gap_data.get("projected_ebitda_pct", 3.5)
        requires_approval = projected_impact > 5.0 or state.get("requires_approval", False)
        approval_reason = state.get("approval_reason") or (
            f"EBITDA {projected_impact}% > 5%" if projected_impact > 5 else None
        )

        # Persist gap analysis highlights for future sessions
        top_gaps = [g.get("dimension") for g in gap_data.get("gaps", [])[:3]]
        await mem0_client.add_memory(
            f"Value creation plan for {company_id}: projected EBITDA impact {projected_impact}%. "
            f"Top gaps: {', '.join(top_gaps) if top_gaps else 'none identified'}.",
            company_id=company_id,
            metadata={"agent": "value_creator", "projected_ebitda_pct": projected_impact},
        )

        content = f"Value creation plan complete. Projected impact: {projected_impact}%"
        if prior:
            content += f" | Prior: {prior[0][:120]}"

        return {
            "value_creation_plan": {
                "company_id": company_id,
                "gap_analysis": gap_data,
                "prior_context": prior,
            },
            "requires_approval": requires_approval,
            "approval_reason": approval_reason,
            "messages": [
                {
                    "role": "assistant",
                    "content": content,
                    "agent_name": "value_creator",
                    "timestamp": _now_utc(),
                }
            ],
        }


sec_agent = SECAnalysisAgent()
scoring_agent = ScoringAgent()
evidence_agent = EvidenceAgent()
value_agent = ValueCreationAgent()
