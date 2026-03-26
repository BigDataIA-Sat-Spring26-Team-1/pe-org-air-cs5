"""
MCP Server - Exposes CS1-CS4 API tools over SSE transport (HTTP) so Claude
Desktop and other MCP-compatible clients can connect remotely.

Endpoints:
  GET  /sse           - SSE stream (MCP protocol handshake + events)
  POST /messages/     - Client-to-server MCP messages
  POST /tools/<name>  - Lightweight HTTP bridge used by MCPToolCaller in agents
  GET  /health        - Liveness probe for docker healthcheck

Transport is selected via MCP_TRANSPORT env var:
  sse   (default) - runs Starlette/uvicorn HTTP server on MCP_PORT (3001)
  stdio           - runs classic stdio transport for local Claude Desktop use
"""
import asyncio
import json
import os
import structlog
from typing import Dict, Any

import uvicorn
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    Prompt,
    PromptArgument,
    PromptMessage,
)
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

# Integrations
from app.services.integration.portfolio_data_service import portfolio_data_service
from app.services.value_creation.ebitda import ebitda_calculator
from app.services.value_creation.gap_analysis import gap_analyzer

logger = structlog.get_logger()
mcp_server = Server("pe-orgair-cs5-server")

_uuid_to_ticker_cache: Dict[str, str] = {}

async def _resolve_ticker(company_id: str) -> str:
    """Convert a company UUID to its ticker. Returns company_id unchanged if it already looks like a ticker."""
    if len(company_id) != 36 or "-" not in company_id:
        return company_id
    if company_id in _uuid_to_ticker_cache:
        return _uuid_to_ticker_cache[company_id]
    try:
        views = await portfolio_data_service.get_portfolio_view("growth_fund_v")
        for v in views:
            _uuid_to_ticker_cache[v.company_id] = v.ticker
        return _uuid_to_ticker_cache.get(company_id, company_id)
    except Exception:
        return company_id


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

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
                    "dimension": {
                        "type": "string",
                        "enum": [
                            "talent",
                            "data_infrastructure",
                            "ai_governance",
                            "use_case_portfolio",
                            "technology_stack",
                            "data_culture",
                            "innovation_velocity",
                        ],
                    },
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


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------

@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute the tools natively."""
    logger.info("tool_called", tool=name, args=arguments)

    try:
        if name == "get_portfolio_summary":
            fund_id = arguments["fund_id"]
            views = await portfolio_data_service.get_portfolio_view(fund_id)
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
            ticker = await _resolve_ticker(company_id)
            evidence = await portfolio_data_service.cs2.get_evidence(ticker=ticker)
            return [TextContent(type="text", text=json.dumps({
                "count": len(evidence),
                "items": evidence[:5],  # cap to avoid blowing out LLM context
            }, indent=2))]

        elif name == "generate_justification":
            company_id = arguments["company_id"]
            ticker = await _resolve_ticker(company_id)
            from app.models.rag import Dimension
            dim = Dimension(arguments["dimension"])
            res = await portfolio_data_service.cs4.generate_justification(ticker, dim)
            return [TextContent(type="text", text=json.dumps({
                "score": res.score,
                "level": res.level_name,
                "strength": res.evidence_strength,
                "rubric": res.rubric_criteria,
            }, indent=2))]

        elif name == "project_ebitda_impact":
            proj = ebitda_calculator.project(
                arguments["company_id"],
                arguments["entry_score"],
                arguments["target_score"],
                arguments["h_r_score"],
            )
            return [TextContent(type="text", text=json.dumps({
                "base_case_pct": proj.base_pct,
                "conservative_pct": proj.conservative_pct,
                "optimistic_pct": proj.optimistic_pct,
                "delta_air": proj.delta_air,
            }, indent=2))]

        elif name == "run_gap_analysis":
            company_id = arguments["company_id"]
            target_org_air = arguments["target_org_air"]

            # Build current_scores from CS3 assessment data so gap analysis uses
            # real scores instead of the 30.0 fallback default.
            current_scores: dict = {}
            try:
                ticker = await _resolve_ticker(company_id)
                assessment_data = await portfolio_data_service.cs3.list_assessments(company_id=ticker)
                items = assessment_data.get("items", [])
                if items:
                    v = items[0]
                    org_air = float(v.get("org_air_score") or 0.0)
                    vr_score = float(v.get("v_r_score") or 0.0)
                    hr_score = float(v.get("h_r_score") or 0.0)
                    if org_air > 0:
                        # Map composite scores to the 7 dimensions as reasonable proxies.
                        # HR dimensions: talent, data_culture
                        # VR dimensions: use_case_portfolio
                        # Tech dimensions: data_infrastructure, technology_stack, innovation_velocity
                        # Governance: ai_governance
                        current_scores = {
                            "talent": round(hr_score * 0.95, 1),
                            "data_culture": round(hr_score * 0.85, 1),
                            "use_case_portfolio": round(vr_score * 0.95, 1),
                            "data_infrastructure": round((org_air + vr_score) / 2 * 0.88, 1),
                            "technology_stack": round(org_air * 0.92, 1),
                            "innovation_velocity": round(org_air * 0.82, 1),
                            "ai_governance": round(org_air * 0.78, 1),
                            "leadership": round(org_air * 0.75, 1),
                        }
            except Exception:
                pass  # fall through to default 30.0 if CS3 is unavailable

            res = gap_analyzer.analyze(company_id, current_scores, target_org_air)
            return [TextContent(type="text", text=json.dumps(res, indent=2))]

        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    except Exception as e:
        logger.error("tool_execution_failed", tool=name, error=str(e))
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

@mcp_server.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(
            uri="orgair://parameters/v2.0",
            name="Org-AI-R Scoring Parameters v2.0",
            description="Current scoring parameters: alpha, beta, gamma values",
        ),
        Resource(
            uri="orgair://sectors",
            name="Sector Definitions",
            description="Sector baselines and weights",
        ),
    ]


@mcp_server.read_resource()
async def read_resource(uri: str) -> str:
    if uri == "orgair://parameters/v2.0":
        return json.dumps({
            "version": "2.0",
            "alpha": 0.60,
            "beta": 0.12,
            "gamma_0": 0.0025,
            "gamma_1": 0.05,
            "gamma_2": 0.025,
            "gamma_3": 0.01,
        })
    elif uri == "orgair://sectors":
        return json.dumps({
            "technology": {"h_r_base": 85, "weight_talent": 0.18},
            "healthcare": {"h_r_base": 75, "weight_governance": 0.18},
        })
    return "{}"


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

@mcp_server.list_prompts()
async def list_prompts() -> list[Prompt]:
    return [
        Prompt(
            name="due_diligence_assessment",
            description="Complete due diligence assessment for a company",
            arguments=[PromptArgument(name="company_id", required=True)],
        ),
        Prompt(
            name="ic_meeting_prep",
            description="Prepare Investment Committee meeting package",
            arguments=[PromptArgument(name="company_id", required=True)],
        ),
    ]


@mcp_server.get_prompt()
async def get_prompt(name: str, arguments: Dict[str, Any]) -> list[PromptMessage]:
    company_id = arguments.get("company_id", "<company_id>")

    if name == "due_diligence_assessment":
        return [
            PromptMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=(
                        f"Perform due diligence for {company_id}.\n"
                        "1. Calculate Org-AI-R score using calculate_org_air_score\n"
                        "2. For any dimension scoring below 60, call generate_justification "
                        "to get evidence-backed analysis\n"
                        "3. Run run_gap_analysis with target_org_air=75\n"
                        "4. Call project_ebitda_impact with the entry and target scores\n"
                        "5. Summarise findings: overall readiness level, top 3 gaps, "
                        "recommended 100-day actions"
                    ),
                ),
            )
        ]

    if name == "ic_meeting_prep":
        return [
            PromptMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=(
                        f"Prepare the Investment Committee package for {company_id}.\n\n"
                        "Step 1 – Portfolio context\n"
                        "  Call get_portfolio_summary with the relevant fund_id to locate "
                        f"{company_id} and establish its Fund-AI-R benchmark.\n\n"
                        "Step 2 – Org-AI-R deep dive\n"
                        f"  Call calculate_org_air_score for {company_id}.\n"
                        "  For every dimension below 70, call generate_justification to "
                        "retrieve rubric criteria, supporting evidence, and identified gaps.\n\n"
                        "Step 3 – Value creation thesis\n"
                        "  Call run_gap_analysis with target_org_air=80 to identify the "
                        "highest-impact improvement levers.\n"
                        "  Call project_ebitda_impact using the current and target scores.\n\n"
                        "Step 4 – IC memo structure\n"
                        "  Produce a structured memo with the following sections:\n"
                        "  • Executive Summary (2-3 sentences)\n"
                        "  • Org-AI-R Scorecard (table: dimension, score, level, key gap)\n"
                        "  • Investment Thesis (how AI readiness drives EBITDA expansion)\n"
                        "  • Risk Factors (dimensions below 50, governance concerns)\n"
                        "  • 100-Day Value Creation Plan (top 3 actions with owners)\n"
                        "  • Recommendation: Proceed / Conditional / Pass"
                    ),
                ),
            )
        ]

    return []


# ---------------------------------------------------------------------------
# SSE transport — Starlette app (used when MCP_TRANSPORT=sse)
# ---------------------------------------------------------------------------

sse_transport = SseServerTransport("/messages/")


async def handle_sse(request: Request):
    """MCP SSE handshake — Claude Desktop connects here."""
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(
            streams[0], streams[1], mcp_server.create_initialization_options()
        )


async def handle_tool_http(request: Request):
    """
    Simple HTTP bridge so MCPToolCaller (used by LangGraph agents) can call
    tools without speaking the full MCP wire protocol.

    POST /tools/<tool_name>   body: { ...tool arguments }
    Returns: { "result": "<json string>" }
    """
    tool_name = request.path_params["tool_name"]
    try:
        body = await request.json()
    except Exception:
        body = {}
    results = await call_tool(tool_name, body)
    text = results[0].text if results else "{}"
    return JSONResponse({"result": text})


async def health(request: Request):
    return JSONResponse({"status": "ok", "server": "pe-orgair-mcp"})


async def metrics_json(request: Request):
    """Expose MCP server Prometheus counters as JSON for the observability dashboard."""
    try:
        from prometheus_client import REGISTRY
        snapshot: dict = {"mcp_tool_calls": {}}
        for metric_family in REGISTRY.collect():
            if metric_family.name == "mcp_tool_calls_total":
                for sample in metric_family.samples:
                    if sample.name.endswith("_total"):
                        tool = sample.labels.get("tool_name", "unknown")
                        status = sample.labels.get("status", "unknown")
                        if tool not in snapshot["mcp_tool_calls"]:
                            snapshot["mcp_tool_calls"][tool] = {"success": 0, "error": 0}
                        snapshot["mcp_tool_calls"][tool][status] = int(sample.value)
        return JSONResponse(snapshot)
    except Exception:
        return JSONResponse({"mcp_tool_calls": {}})


starlette_app = Starlette(
    routes=[
        Route("/health", endpoint=health),
        Route("/metrics-json", endpoint=metrics_json),
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse_transport.handle_post_message),
        Route("/tools/{tool_name}", endpoint=handle_tool_http, methods=["POST"]),
    ]
)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    transport = os.getenv("MCP_TRANSPORT", "sse")

    if transport == "stdio":
        logger.info("mcp_server_started", transport="stdio")
        async with stdio_server() as (read_stream, write_stream):
            await mcp_server.run(
                read_stream, write_stream, mcp_server.create_initialization_options()
            )
    else:
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "3001"))
        logger.info("mcp_server_started", transport="sse", host=host, port=port)
        config = uvicorn.Config(starlette_app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
