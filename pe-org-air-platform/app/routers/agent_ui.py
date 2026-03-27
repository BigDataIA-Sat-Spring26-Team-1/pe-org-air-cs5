from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from typing import List, Dict, Any, Optional
import structlog
import os
import time
from pydantic import BaseModel
from datetime import datetime

from app.services.observability.metrics import AGENT_INVOCATIONS, AGENT_DURATION, HITL_APPROVALS

# Services
from app.services.integration.portfolio_data_service import portfolio_data_service, PortfolioCompanyView
from app.services.analytics.fund_air import fund_air_calculator
from app.services.tracking.assessment_history import create_history_service
from app.agents.supervisor import dd_graph
from app.agents.state import DueDiligenceState

router = APIRouter(prefix="/agent-ui", tags=["Agent UI Integration"])
logger = structlog.get_logger()

# ── In-memory HITL pending store ──────────────────────────────────────────────
# Maps thread_id → {config, company_id, hitl_data, created_at}
# MemorySaver keeps the paused graph state alive for the same process lifetime.
_pending_hitl: Dict[str, Dict[str, Any]] = {}


def _track_workflow_metrics(result: dict, elapsed_seconds: float) -> None:
    """Record Prometheus metrics for each completed agent stage in the workflow."""
    messages = result.get("messages") or []
    agent_names = {m.get("agent_name") for m in messages if isinstance(m, dict) and m.get("agent_name")}

    stage_map = {
        "sec_analyst": "sec_analysis_agent",
        "scorer": "scoring_agent",
        "evidence_agent": "evidence_agent",
        "value_creator": "value_creation_agent",
        "hitl": "hitl_check",
        "supervisor": "supervisor",
    }

    for raw_name, metric_name in stage_map.items():
        if raw_name in agent_names:
            AGENT_INVOCATIONS.labels(agent_name=metric_name, status="success").inc()

    # Overall workflow duration attributed to the supervisor
    AGENT_DURATION.labels(agent_name="due_diligence_workflow").observe(elapsed_seconds)

    # HITL metric
    requires_approval = result.get("requires_approval", False)
    if requires_approval:
        approval_status = result.get("approval_status") or "pending"
        approval_reason = (result.get("approval_reason") or "score_threshold")[:40]
        decision = "approved" if approval_status == "approved" else "pending"
        HITL_APPROVALS.labels(reason=approval_reason, decision=decision).inc()

# Initialise history service using shared clients
history_service = create_history_service(portfolio_data_service.cs1, portfolio_data_service.cs3, portfolio_data_service.cs2)

class AgentTriggerRequest(BaseModel):
    company_id: str
    assessment_type: str = "full"
    requested_by: str = "analyst"
    target_org_air: float = 75.0


class HITLDecisionRequest(BaseModel):
    approved: bool
    reviewed_by: str = "analyst"
    notes: Optional[str] = ""

@router.get("/portfolio", response_model=List[PortfolioCompanyView])
async def get_portfolio_dashboard_view(fund_id: str = "growth_fund_v"):
    """Fetch live portfolio data for the dashboard."""
    try:
        return await portfolio_data_service.get_portfolio_view(fund_id)
    except Exception as e:
        logger.error("get_portfolio_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fund-air")
async def get_fund_air_metrics(fund_id: str = "growth_fund_v"):
    """Fetch EV-weighted Fund-AI-R score."""
    try:
        portfolio = await portfolio_data_service.get_portfolio_view(fund_id)

        # Enterprise values are derived from CS1 revenue data as a proxy
        # (EV = revenue_mm * sector multiple). Real EV data would come from
        # a dedicated portfolio positions table in CS1.
        ev_mapping = {
            c.ticker: c.org_air * 1000.0  # scaled proxy until CS1 exposes EV
            for c in portfolio
        }

        metrics = fund_air_calculator.calculate_fund_metrics(
            fund_id=fund_id,
            companies=portfolio,
            enterprise_values=ev_mapping
        )

        return metrics
    except Exception as e:
        logger.error("fund_air_calculation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/trigger-due-diligence")
async def trigger_agentic_workflow(request: AgentTriggerRequest):
    """
    Trigger agentic due diligence workflow.

    Returns one of two shapes:
      {"status": "completed",    "thread_id": ..., ...full result...}
      {"status": "pending_hitl", "thread_id": ..., "hitl_data": {...}}

    When "pending_hitl" is returned the graph is paused at the HITL node.
    Call POST /agent-ui/hitl/{thread_id}/decision to resume it.
    """
    try:
        thread_id = f"dd-{request.company_id}-{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}"
        config = {"configurable": {"thread_id": thread_id}}

        initial_state: DueDiligenceState = {
            "company_id": request.company_id,
            "assessment_type": request.assessment_type,
            "requested_by": request.requested_by,
            "messages": [],
            "sec_analysis": None,
            "talent_analysis": None,
            "scoring_result": None,
            "evidence_justifications": None,
            "value_creation_plan": None,
            "next_agent": None,
            "requires_approval": False,
            "approval_reason": None,
            "approval_status": None,
            "approved_by": None,
            "started_at": datetime.utcnow(),
            "completed_at": None,
            "total_tokens": 0,
            "error": None,
        }

        t_start = time.perf_counter()
        result = await dd_graph.ainvoke(initial_state, config)
        elapsed = time.perf_counter() - t_start

        # Check whether the graph paused at the HITL interrupt or ran to completion
        graph_state = await dd_graph.aget_state(config)
        is_interrupted = bool(graph_state.next)  # non-empty → graph still has pending nodes

        if is_interrupted:
            # Extract the interrupt payload the node sent to the reviewer
            hitl_data: Dict[str, Any] = {}
            for task in (graph_state.tasks or []):
                interrupts = getattr(task, "interrupts", None) or []
                if interrupts:
                    hitl_data = interrupts[0].value if hasattr(interrupts[0], "value") else {}
                    break

            _pending_hitl[thread_id] = {
                "thread_id": thread_id,
                "config": config,
                "company_id": request.company_id,
                "hitl_data": hitl_data,
                "created_at": datetime.utcnow().isoformat(),
                "partial_result": result,
            }

            logger.info("hitl_interrupt_detected", thread_id=thread_id, company_id=request.company_id)
            HITL_APPROVALS.labels(
                reason=(result.get("approval_reason") or "score_threshold")[:40],
                decision="pending",
            ).inc()

            return {
                "status": "pending_hitl",
                "thread_id": thread_id,
                "company_id": request.company_id,
                "hitl_data": hitl_data,
                # Include partial results so the frontend can show scores already computed
                "scoring_result": result.get("scoring_result"),
                "requires_approval": result.get("requires_approval"),
                "approval_reason": result.get("approval_reason"),
                "messages": result.get("messages", []),
            }

        # Graph completed normally — track metrics and return
        _track_workflow_metrics(result, elapsed)
        return {"status": "completed", "thread_id": thread_id, **result}

    except Exception as e:
        AGENT_INVOCATIONS.labels(agent_name="due_diligence_workflow", status="error").inc()
        logger.error("workflow_trigger_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ── HITL management endpoints ─────────────────────────────────────────────────

@router.get("/hitl/pending")
async def list_pending_hitl():
    """List all workflows currently paused at a HITL gate."""
    return [
        {
            "thread_id": v["thread_id"],
            "company_id": v["company_id"],
            "hitl_data": v["hitl_data"],
            "created_at": v["created_at"],
        }
        for v in _pending_hitl.values()
    ]


@router.get("/hitl/{thread_id}")
async def get_hitl_details(thread_id: str):
    """Return the HITL interrupt payload for a specific paused workflow."""
    if thread_id not in _pending_hitl:
        raise HTTPException(status_code=404, detail="Thread not found or already resolved")
    entry = _pending_hitl[thread_id]
    return {
        "thread_id": thread_id,
        "company_id": entry["company_id"],
        "hitl_data": entry["hitl_data"],
        "created_at": entry["created_at"],
    }


@router.post("/hitl/{thread_id}/decision")
async def submit_hitl_decision(thread_id: str, body: HITLDecisionRequest):
    """
    Resume a paused workflow with a human decision.

    The graph's hitl_approval_node receives the decision dict and continues
    running to completion.  Returns the final workflow result.
    """
    if thread_id not in _pending_hitl:
        raise HTTPException(status_code=404, detail="Thread not found or already resolved")

    entry = _pending_hitl.pop(thread_id)
    config = entry["config"]

    try:
        from langgraph.types import Command

        t_start = time.perf_counter()
        result = await dd_graph.ainvoke(
            Command(resume={
                "approved": body.approved,
                "reviewed_by": body.reviewed_by,
                "notes": body.notes or "",
            }),
            config,
        )
        elapsed = time.perf_counter() - t_start

        _track_workflow_metrics(result, elapsed)

        is_rejected = result.get("approval_status") == "rejected"
        HITL_APPROVALS.labels(
            reason=(result.get("approval_reason") or "score_threshold")[:40],
            decision="approved" if body.approved else "rejected",
        ).inc()

        logger.info(
            "hitl_decision_applied",
            thread_id=thread_id,
            approved=body.approved,
            reviewed_by=body.reviewed_by,
        )

        final_status = "rejected" if is_rejected else "completed"
        return {"status": final_status, "thread_id": thread_id, **result}

    except Exception as e:
        # Put the entry back so it can be retried
        _pending_hitl[thread_id] = entry
        logger.error("hitl_resume_failed", thread_id=thread_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{company_id}")
async def get_company_history(company_id: str):
    """Fetch assessment history."""
    try:
        return await history_service.get_history(company_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-ic-memo/{company_id}")
async def generate_ic_memo_endpoint(company_id: str, assessment_type: str = "full"):
    """Generate IC Memo Word document for a company and return it as a download."""
    try:
        from app.agents.bonus.ic_memo_generator import generate_ic_memo
        output_path = await generate_ic_memo(company_id, assessment_type)
        if not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="File generation failed")
        return FileResponse(
            path=output_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"ic_memo_{company_id}.docx",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("ic_memo_generation_failed", company_id=company_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-lp-letter/{company_id}")
async def generate_lp_letter_endpoint(company_id: str, assessment_type: str = "full"):
    """Generate LP Letter Word document for a company and return it as a download."""
    try:
        from app.agents.bonus.lp_letter_generator import generate_lp_letter
        output_path = await generate_lp_letter(company_id, assessment_type)
        if not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="File generation failed")
        return FileResponse(
            path=output_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"lp_letter_{company_id}.docx",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("lp_letter_generation_failed", company_id=company_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mcp-tools")
async def get_mcp_tools():
    """Return the list of MCP tools, prompts, and resources exposed by the MCP server."""
    return {
        "tools": [
            {
                "name": "get_portfolio_summary",
                "description": "Fetch all portfolio companies with scores from CS1-CS3.",
                "parameters": [
                    {"name": "fund_id", "type": "string", "required": True, "description": "Fund identifier (e.g. growth_fund_v)"},
                ],
            },
            {
                "name": "calculate_org_air_score",
                "description": "Calculate Org-AI-R score for a company using CS3 scoring engine.",
                "parameters": [
                    {"name": "company_id", "type": "string", "required": True, "description": "Company ticker or ID (e.g. NVDA)"},
                ],
            },
            {
                "name": "get_company_evidence",
                "description": "Fetch granular evidence signals (patents, SEC, etc.) from CS2.",
                "parameters": [
                    {"name": "company_id", "type": "string", "required": True, "description": "Company ticker or UUID"},
                ],
            },
            {
                "name": "generate_justification",
                "description": "Generate a CS4 RAG-backed justification for a single dimension.",
                "parameters": [
                    {"name": "company_id", "type": "string", "required": True, "description": "Company ticker or UUID"},
                    {
                        "name": "dimension",
                        "type": "enum",
                        "required": True,
                        "description": "AI readiness dimension to justify",
                        "values": ["talent", "data_infrastructure", "ai_governance", "use_case_portfolio", "technology_stack", "culture", "leadership"],
                    },
                ],
            },
            {
                "name": "batch_generate_justifications",
                "description": "Generate CS4 RAG justifications for multiple dimensions in parallel (faster than calling generate_justification repeatedly).",
                "parameters": [
                    {"name": "company_id", "type": "string", "required": True, "description": "Company ticker or UUID"},
                    {
                        "name": "dimensions",
                        "type": "array",
                        "required": False,
                        "description": "Dimensions to justify. Omit to fetch all 7.",
                        "values": ["talent", "data_infrastructure", "ai_governance", "use_case_portfolio", "technology_stack", "culture", "leadership"],
                    },
                ],
            },
            {
                "name": "project_ebitda_impact",
                "description": "Project financial metrics impact based on CS3 scores.",
                "parameters": [
                    {"name": "company_id", "type": "string", "required": True, "description": "Company ticker or UUID"},
                    {"name": "entry_score", "type": "number", "required": True, "description": "Org-AI-R score at investment entry"},
                    {"name": "target_score", "type": "number", "required": True, "description": "Target Org-AI-R score"},
                    {"name": "h_r_score", "type": "number", "required": True, "description": "Human Readiness score"},
                ],
            },
            {
                "name": "run_gap_analysis",
                "description": "Analyze gaps to target state and suggest interventions.",
                "parameters": [
                    {"name": "company_id", "type": "string", "required": True, "description": "Company ticker or UUID"},
                    {"name": "target_org_air", "type": "number", "required": True, "description": "Target Org-AI-R score to reach"},
                ],
            },
        ],
        "prompts": [
            {
                "name": "due_diligence_assessment",
                "description": "Complete due diligence assessment for a company",
                "arguments": [{"name": "company_id", "required": True}],
                "workflow": (
                    "1. Calculate Org-AI-R score using calculate_org_air_score\n"
                    "2. For any dimension scoring below 60, call generate_justification to get evidence-backed analysis\n"
                    "3. Run run_gap_analysis with target_org_air=75\n"
                    "4. Call project_ebitda_impact with the entry and target scores\n"
                    "5. Summarise findings: overall readiness level, top 3 gaps, recommended 100-day actions"
                ),
            },
            {
                "name": "ic_meeting_prep",
                "description": "Prepare Investment Committee meeting package",
                "arguments": [{"name": "company_id", "required": True}],
                "workflow": (
                    "Step 1 – Portfolio context\n"
                    "  Call get_portfolio_summary with the relevant fund_id to locate the company and establish its Fund-AI-R benchmark.\n\n"
                    "Step 2 – Org-AI-R deep dive\n"
                    "  Call calculate_org_air_score. For every dimension below 70, call generate_justification to retrieve rubric criteria, supporting evidence, and identified gaps.\n\n"
                    "Step 3 – Value creation thesis\n"
                    "  Call run_gap_analysis with target_org_air=80 to identify the highest-impact improvement levers.\n"
                    "  Call project_ebitda_impact using the current and target scores.\n\n"
                    "Step 4 – IC memo structure\n"
                    "  Produce a structured memo with:\n"
                    "  • Executive Summary (2-3 sentences)\n"
                    "  • Org-AI-R Scorecard (table: dimension, score, level, key gap)\n"
                    "  • Investment Thesis (how AI readiness drives EBITDA expansion)\n"
                    "  • Risk Factors (dimensions below 50, governance concerns)\n"
                    "  • 100-Day Value Creation Plan (top 3 actions with owners)\n"
                    "  • Recommendation: Proceed / Conditional / Pass"
                ),
            },
        ],
        "resources": [
            {
                "uri": "orgair://parameters/v2.0",
                "name": "Org-AI-R Scoring Parameters v2.0",
                "description": "Current scoring parameters: alpha, beta, gamma values",
                "example": {"version": "2.0", "alpha": 0.60, "beta": 0.12, "gamma_0": 0.0025, "gamma_1": 0.05, "gamma_2": 0.025, "gamma_3": 0.01},
            },
            {
                "uri": "orgair://sectors",
                "name": "Sector Definitions",
                "description": "Sector baselines and weights",
                "example": {"technology": {"h_r_base": 85, "weight_talent": 0.18}, "healthcare": {"h_r_base": 75, "weight_governance": 0.18}},
            },
        ],
    }
