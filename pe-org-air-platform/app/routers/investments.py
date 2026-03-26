"""
Investment ROI API — exposes InvestmentTracker data via REST.

Endpoints:
  GET /api/v1/investments/portfolio-roi   — fund-level summary
  GET /api/v1/investments/{company_id}/roi — per-company ROI
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from dataclasses import asdict
from datetime import datetime, timedelta
import structlog

from app.services.tracking.investment_tracker import create_investment_tracker, InvestmentTracker
from app.services.integration.portfolio_data_service import portfolio_data_service

router = APIRouter()
logger = structlog.get_logger()

# Module-level singleton tracker — seeded lazily on first request
_tracker: Optional[InvestmentTracker] = None


async def _get_seeded_tracker(fund_id: str = "growth_fund_v") -> InvestmentTracker:
    """Return the singleton tracker, seeding it from live portfolio data if empty."""
    global _tracker
    if _tracker is None:
        _tracker = create_investment_tracker()

    if _tracker._investments:
        return _tracker

    # Seed from CS3 portfolio data
    try:
        portfolio = await portfolio_data_service.get_portfolio_view(fund_id)
        entry_date = datetime.utcnow() - timedelta(days=730)  # ~2 years ago

        for company in portfolio:
            if not company.org_air or company.org_air <= 0:
                continue

            current_org_air = company.org_air
            # Simulate entry score 10-20% lower than current (reflects improvement)
            entry_org_air = max(current_org_air * 0.82, 5.0)

            # EV proxy: org_air_score * 100 = entry EV in $MM
            entry_ev = round(current_org_air * 100, 2)
            # Current EV grows proportional to AI readiness improvement
            delta_pct = (current_org_air - entry_org_air) / max(entry_org_air, 1)
            current_ev = round(entry_ev * (1 + delta_pct * 2.5), 2)
            investment_amount = round(entry_ev * 0.30, 2)

            sector = (company.sector or "technology").lower().replace(" ", "_")

            _tracker.record_investment(
                company_id=company.company_id,
                company_name=company.name or company.ticker,
                sector=sector,
                entry_date=entry_date,
                entry_ev_mm=entry_ev,
                entry_org_air=entry_org_air,
                current_ev_mm=current_ev,
                current_org_air=current_org_air,
                investment_amount_mm=investment_amount,
            )
            logger.info("investment_seeded", company=company.ticker, entry_ev=entry_ev, current_ev=current_ev)

    except Exception as e:
        logger.error("tracker_seeding_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to seed investment data: {e}")

    if not _tracker._investments:
        raise HTTPException(status_code=404, detail="No companies with valid Org-AI-R scores found")

    return _tracker


@router.get("/portfolio-roi")
async def get_portfolio_roi(fund_id: str = Query("growth_fund_v")):
    """Fund-level portfolio ROI summary with AI attribution."""
    try:
        tracker = await _get_seeded_tracker(fund_id)
        summary = tracker.calculate_portfolio_roi(fund_id)
        data = asdict(summary)
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error("portfolio_roi_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{company_id}/roi")
async def get_company_roi(company_id: str):
    """Per-company ROI with AI-readiness attribution."""
    try:
        tracker = await _get_seeded_tracker()
        roi = tracker.calculate_roi(company_id)
        return asdict(roi)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Investment not found for company {company_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("company_roi_failed", company_id=company_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_investments(fund_id: str = Query("growth_fund_v")):
    """List all seeded investments with individual ROI metrics."""
    try:
        tracker = await _get_seeded_tracker(fund_id)
        result = []
        for company_id in tracker._investments:
            try:
                roi = tracker.calculate_roi(company_id)
                result.append(asdict(roi))
            except Exception:
                pass
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
