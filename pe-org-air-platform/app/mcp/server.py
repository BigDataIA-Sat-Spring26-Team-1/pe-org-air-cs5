"""
MCP Server Core (Lab 9.2) - Exposing CS1-CS4 API tools.
"""
import asyncio
import json
import structlog
from typing import Dict, Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent
)

# Integrations
from app.services.integration.portfolio_data_service import portfolio_data_service
from app.services.value_creation.ebitda import ebitda_calculator
from app.services.value_creation.gap_analysis import gap_analyzer

logger = structlog.get_logger()
mcp_server = Server("pe-orgair-cs5-server")

@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """Expose CS1-CS4 endpoints as LLM tools."""
    return [
        Tool(
            name="get_portfolio_summary",
            description="Fetch all portfolio companies with scores from CS1-CS3.",
            inputSchema={
                "type": "object",
                "properties": {
                    "fund_id": {"type": "string"},
                },
                "required": ["fund_id"],
            },
        ),
        Tool(
            name="calculate_org_air_score",
            description="Calculate Org-AI-R score for a company using CS3 scoring engine.",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_id": {"type": "string", "description": "Company ticker or ID (e.g., 'NVDA')"},
                },
                "required": ["company_id"],
            },
        ),
        Tool(
            name="get_company_evidence",
            description="Fetch granular evidence signals (patents, SEC, etc.) from CS2.",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_id": {"type": "string"},
                },
                "required": ["company_id"],
            },
        ),
        Tool(
            name="generate_justification",
            description="Generate a CS4 justification via RAG for a given dimension.",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_id": {"type": "string"},
                    "dimension": {"type": "string", "enum": ["talent", "data_infrastructure", "ai_governance"]},
                },
                "required": ["company_id", "dimension"],
            },
        ),
        Tool(
            name="project_ebitda_impact",
            description="Project financial metrics impact based on CS3 scores.",
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
        Tool(
            name="run_gap_analysis",
            description="Analyze gaps to target state and suggest interventions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_id": {"type": "string"},
                    "target_org_air": {"type": "number"},
                },
                "required": ["company_id", "target_org_air"],
            },
        ),
    ]

@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute the tools natively."""
    logger.info("tool_called", tool=name, args=arguments)
    
    try:
        if name == "get_portfolio_summary":
            fund_id = arguments["fund_id"]
            views = await portfolio_data_service.get_portfolio_view(fund_id)
            # Serialize
            return [TextContent(type="text", text=json.dumps([{
                "company_id": v.company_id,
                "ticker": v.ticker,
                "org_air_score": v.org_air,
                "v_r_score": v.vr_score,
                "h_r_score": v.hr_score,
            } for v in views], indent=2))]

        elif name == "calculate_org_air_score":
            company_id = arguments["company_id"]
            assessment_data = await portfolio_data_service.cs3.list_assessments(company_id=company_id)
            items = assessment_data.get("items", [])
            if not items:
                return [TextContent(type="text", text=json.dumps({"error": f"No assessment for {company_id}"}))]
            
            v = items[0]
            return [TextContent(type="text", text=json.dumps({
                "org_air": v.get("org_air_score", 0.0),
                "vr_score": v.get("v_r_score", 0.0),
                "hr_score": v.get("h_r_score", 0.0),
            }, indent=2))]

        elif name == "get_company_evidence":
            company_id = arguments["company_id"]
            evidence = await portfolio_data_service.cs2.get_evidence(ticker=company_id)
            return [TextContent(type="text", text=json.dumps({
                "count": len(evidence),
                "items": evidence[:5] # limit returned text so context isn't blown out
            }, indent=2))]

        elif name == "generate_justification":
            # Using CS4 client
            company_id = arguments["company_id"]
            from app.models.rag import Dimension # Dynamic import
            dim = Dimension(arguments["dimension"])
            res = await portfolio_data_service.cs4.generate_justification(company_id, dim)
            return [TextContent(type="text", text=json.dumps({
                "score": res.score,
                "level": res.level_name,
                "strength": res.evidence_strength,
                "rubric": res.rubric_criteria
            }, indent=2))]

        elif name == "project_ebitda_impact":
            proj = ebitda_calculator.project(
                arguments["company_id"], 
                arguments["entry_score"], 
                arguments["target_score"], 
                arguments["h_r_score"]
            )
            return [TextContent(type="text", text=json.dumps({
                "base_case_pct": proj.base_pct,
                "conservative_pct": proj.conservative_pct,
                "optimistic_pct": proj.optimistic_pct,
                "delta_air": proj.delta_air
            }, indent=2))]

        elif name == "run_gap_analysis":
            res = gap_analyzer.analyze(
                arguments["company_id"],
                {}, 
                arguments["target_org_air"]
            )
            return [TextContent(type="text", text=json.dumps(res, indent=2))]

        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    except Exception as e:
        logger.error("tool_execution_failed", error=str(e))
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

async def main():
    logger.info("mcp_server_started")
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(read_stream, write_stream, mcp_server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
