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
        
        # We need to map enterprise values. In a real app, this comes from CS1.
        # Here we use a stable mock mapping for the 5-6 companies in the DB.
        ev_mapping = {
            "NVDA": 2200000.0,
            "JPM": 550000.0,
            "WMT": 480000.0,
            "GE": 120000.0,
            "DG": 25000.0,
            "CAT": 135000.0
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
        initial_state = {
            "company_id": request.company_id,
            "target_org_air": request.target_org_air,
            "messages": [],
            "sec_analysis": {},
            "scoring_data": {},
            "evidence_data": {},
            "value_creation": {},
            "final_score": 0.0,
            "ebitda_impact": 0.0,
            "requires_approval": False,
            "hitl_approved": False,
            "next_node": "supervisor"
        }
        # Using the compiled graph
        result = await dd_graph.ainvoke(initial_state)
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
