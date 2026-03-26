"""
Specialist Agents - Domain-specific agents for the due diligence workflow.
"""
from typing import Dict, Any
from datetime import datetime
import json

import httpx
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.tools import tool
import structlog

from agents.state import DueDiligenceState

logger = structlog.get_logger()


class MCPToolCaller:
    def __init__(self, base_url: str = "http://localhost:3000"):
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
        evidence_result = await get_evidence.ainvoke({"company_id": company_id, "dimension": "all"})
        return {
            "sec_analysis": {
                "company_id": company_id,
                "findings": json.loads(evidence_result) if evidence_result else [],
                "dimensions_covered": ["data_infrastructure", "ai_governance", "technology_stack"],
            },
            "messages": [
                {
                    "role": "assistant",
                    "content": f"SEC analysis complete for {company_id}",
                    "agent_name": "sec_analyst",
                    "timestamp": datetime.utcnow(),
                }
            ],
        }


class ScoringAgent:
    def __init__(self):
        self.llm = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0.2)
        self.tools = [get_org_air_score, get_justification]

    async def calculate(self, state: DueDiligenceState) -> Dict[str, Any]:
        company_id = state["company_id"]
        score_result = await get_org_air_score.ainvoke({"company_id": company_id})
        score_data = json.loads(score_result)
        org_air = score_data["org_air"]
        requires_approval = org_air > 85 or org_air < 40
        approval_reason = f"Score {org_air:.1f} outside normal range [40, 85]" if requires_approval else None
        return {
            "scoring_result": score_data,
            "requires_approval": requires_approval,
            "approval_reason": approval_reason,
            "approval_status": "pending" if requires_approval else None,
            "messages": [
                {
                    "role": "assistant",
                    "content": (
                        f"Scoring complete: Org-AI-R = {org_air:.1f}"
                        + (" [REQUIRES APPROVAL]" if requires_approval else "")
                    ),
                    "agent_name": "scorer",
                    "timestamp": datetime.utcnow(),
                }
            ],
        }


class EvidenceAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
        self.tools = [get_justification]

    async def justify(self, state: DueDiligenceState) -> Dict[str, Any]:
        company_id = state["company_id"]
        dimensions = ["data_infrastructure", "talent", "use_case_portfolio"]
        justifications = {}
        for dim in dimensions:
            result = await get_justification.ainvoke({"company_id": company_id, "dimension": dim})
            justifications[dim] = json.loads(result)
        return {
            "evidence_justifications": {
                "company_id": company_id,
                "justifications": justifications,
            },
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Generated justifications for {len(justifications)} dimensions",
                    "agent_name": "evidence_agent",
                    "timestamp": datetime.utcnow(),
                }
            ],
        }


class ValueCreationAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
        self.tools = [get_gap_analysis]

    async def plan(self, state: DueDiligenceState) -> Dict[str, Any]:
        company_id = state["company_id"]
        gap_result = await get_gap_analysis.ainvoke({"company_id": company_id, "target": 80.0})
        gap_data = json.loads(gap_result)
        projected_impact = gap_data.get("projected_ebitda_pct", 3.5)
        requires_approval = projected_impact > 5.0 or state.get("requires_approval", False)
        approval_reason = state.get("approval_reason") or (
            f"EBITDA {projected_impact}% > 5%" if projected_impact > 5 else None
        )
        return {
            "value_creation_plan": {
                "company_id": company_id,
                "gap_analysis": gap_data,
            },
            "requires_approval": requires_approval,
            "approval_reason": approval_reason,
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Value creation plan complete. Projected impact: {projected_impact}%",
                    "agent_name": "value_creator",
                    "timestamp": datetime.utcnow(),
                }
            ],
        }


sec_agent = SECAnalysisAgent()
scoring_agent = ScoringAgent()
evidence_agent = EvidenceAgent()
value_agent = ValueCreationAgent()
