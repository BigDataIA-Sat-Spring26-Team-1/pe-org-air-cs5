from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
import structlog
from pydantic import BaseModel
from datetime import datetime

# Services
from app.services.integration.portfolio_data_service import portfolio_data_service, PortfolioCompanyView
from app.services.analytics.fund_air import fund_air_calculator
from app.services.tracking.assessment_history import history_tracker, create_history_service
from app.agents.supervisor import dd_graph
from app.agents.state import DueDiligenceState

router = APIRouter(prefix="/agent-ui", tags=["Agent UI Integration"])
logger = structlog.get_logger()

# Initialise history service using shared clients
history_service = create_history_service(portfolio_data_service.cs1, portfolio_data_service.cs3)

class AgentTriggerRequest(BaseModel):
    company_id: str
    assessment_type: str = "full"
    requested_by: str = "analyst"
    target_org_air: float = 75.0

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
    """Trigger agentic due diligence workflow."""
    try:
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
        config = {"configurable": {"thread_id": f"dd-{request.company_id}-{datetime.utcnow().isoformat()}"}}
        result = await dd_graph.ainvoke(initial_state, config)
        return result
    except Exception as e:
        logger.error("workflow_trigger_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{company_id}")
async def get_company_history(company_id: str):
    """Fetch assessment history."""
    try:
        return await history_service.get_history(company_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
