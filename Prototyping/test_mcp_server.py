import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool, Resource, Prompt, PromptMessage,
    TextContent
)

# Mocked ebitda calculator and gap analyzer since they don't exist
class EBITDAProjector:
    def project(self, company_id, entry_score, exit_score, h_r_score):
        class Projection:
            delta_air = exit_score - entry_score
            conservative_pct = 2.0
            base_pct = 3.5
            optimistic_pct = 5.0
            risk_adjusted_pct = 3.0
            requires_approval = False
        return Projection()

ebitda_calculator = EBITDAProjector()

class GapAnalyzer:
    def analyze(self, company_id, current_scores, target_org_air):
        return {
            "company_id": company_id,
            "target": target_org_air,
            "gaps": ["Missing robust data pipeline", "No AI Governance framework"],
            "initiatives": ["Deploy Snowflake", "Establish AI Ethics Board"],
            "estimated_investment": "$1.5M - $2.5M",
            "priority": "High"
        }

gap_analyzer = GapAnalyzer()

# To run tests against the backend, we can just use the CS clients we tested
import sys
import os
import sys

# We add pe-org-air-platform to Python Path to import from app
sys.path.append(os.path.join(os.path.dirname(__file__), "../pe-org-air-platform"))
from app.services.integration.portfolio_data_service import portfolio_data_service
from app.services.integration.cs2_client import CS2Client
from app.services.integration.cs3_client import CS3Client
from app.services.integration.cs4_client import CS4Client

mcp_server = Server("pe-orgair-server-prototype")
cs2_client = CS2Client(base_url="http://localhost")
cs3_client = CS3Client(base_url="http://localhost")
cs4_client = CS4Client(base_url="http://localhost")

@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="calculate_org_air_score",
            description="Calculate Org-AI-R score for a company using CS3 scoring engine.",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_id": {"type": "string", "description": "Company ticker (e.g., 'NVDA')"},
                },
                "required": ["company_id"],
            },
        ),
        Tool(
            name="project_ebitda_impact",
            description="Project EBITDA impact from AI improvements using v2.0 model.",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_id": {"type": "string"},
                    "entry_score": {"type": "number"},
                    "target_score": {"type": "number"},
                    "h_r_score": {"type": "number"},
                },
                "required": ["company_id", "entry_score", "target_score", "h_r_score"],
            },
        ),
        # Adding gap analysis for safety
        Tool(
            name="run_gap_analysis",
            description="Analyze gaps and generate 100-day improvement plan.",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_id": {"type": "string"},
                    "target_org_air": {"type": "number", "minimum": 0, "maximum": 100},
                },
                "required": ["company_id", "target_org_air"],
            },
        ),
    ]

@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "calculate_org_air_score":
        try:
            # Reusing the tested integration code!
            assessment_data = await cs3_client.list_assessments(company_id=arguments["company_id"])
            items = assessment_data.get("items", [])
            if items:
                v = items[0]
                return [TextContent(type="text", text=json.dumps({
                    "company_id": arguments["company_id"],
                    "org_air": v.get("org_air_score", 0.0),
                    "vr_score": v.get("v_r_score", 0.0),
                    "hr_score": v.get("h_r_score", 0.0)
                }, indent=2))]
            return [TextContent(type="text", text=json.dumps({"error": "No assessment found"}))]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]
    elif name == "project_ebitda_impact":
        res = ebitda_calculator.project(arguments["company_id"], arguments["entry_score"], arguments["target_score"], arguments["h_r_score"])
        return [TextContent(type="text", text=f"Base impact: {res.base_pct}%")]
    elif name == "run_gap_analysis":
        res = gap_analyzer.analyze(arguments["company_id"], {}, arguments["target_org_air"])
        return [TextContent(type="text", text=json.dumps(res))]
    return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def _test():
    tools = await list_tools()
    print("Registered tools: ", [t.name for t in tools])
    print("Testing tool call: calculate_org_air_score for NVDA...")
    res = await call_tool("calculate_org_air_score", {"company_id": "NVDA"})
    print("Result:")
    print(res[0].text)

    print("Testing tool call: project_ebitda_impact...")
    res = await call_tool("project_ebitda_impact", {"company_id": "DG", "entry_score": 40.0, "target_score": 80.0, "h_r_score": 60.0})
    print(res[0].text)

if __name__ == "__main__":
    asyncio.run(_test())
