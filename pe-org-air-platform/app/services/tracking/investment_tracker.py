"""
Investment Tracker with ROI.

Tracks PE portfolio investments, calculates financial returns (ROI, MOIC, IRR),
and attributes value creation to AI-readiness improvements using assessment
history from AssessmentHistoryService.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from decimal import Decimal
import math
import structlog

from app.services.tracking.assessment_history import (
    AssessmentHistoryService,
    AssessmentSnapshot,
    AssessmentTrend,
)

logger = structlog.get_logger()

# Sector-specific AI value multipliers — higher for tech-heavy sectors
SECTOR_AI_COEFFICIENTS = {
    "technology": 0.35,
    "financial_services": 0.30,
    "healthcare": 0.25,
    "manufacturing": 0.20,
    "retail": 0.20,
    "energy": 0.15,
}

AI_ATTRIBUTION_CAP = 0.40  # Max 40% of value creation attributed to AI


@dataclass
class Investment:
    """A PE investment position in a portfolio company."""
    company_id: str
    company_name: str
    sector: str
    entry_date: datetime
    entry_ev_mm: float        # Entry enterprise value ($MM)
    entry_org_air: float      # Org-AI-R score at entry
    current_ev_mm: float      # Current / exit enterprise value ($MM)
    current_org_air: float    # Current Org-AI-R score
    exit_date: Optional[datetime] = None  # None = still held
    investment_amount_mm: float = 0.0     # Equity invested ($MM)


@dataclass
class InvestmentROI:
    """ROI metrics for a single investment."""
    company_id: str
    company_name: str
    entry_ev_mm: float
    current_ev_mm: float
    simple_roi_pct: float            # (current - entry) / entry × 100
    annualized_roi_pct: float        # Annualized return
    moic: float                      # Multiple on Invested Capital
    holding_period_years: float
    org_air_delta: float             # Change in Org-AI-R score
    ai_attributed_value_pct: float   # % of return attributable to AI improvement
    ai_attributed_value_mm: float    # $ value of AI attribution ($MM)
    irr_estimate_pct: float          # Simplified IRR approximation
    status: str                      # "active", "realized", "loss"


@dataclass
class PortfolioROISummary:
    """Fund-level portfolio ROI summary."""
    fund_id: str
    total_invested_mm: float
    total_current_value_mm: float
    portfolio_moic: float
    portfolio_roi_pct: float
    weighted_avg_annualized_roi_pct: float
    total_ai_attributed_value_mm: float
    avg_ai_attribution_pct: float
    investment_count: int
    active_count: int
    realized_count: int
    loss_count: int
    best_performer: Optional[InvestmentROI] = None
    worst_performer: Optional[InvestmentROI] = None
    avg_holding_period_years: float = 0.0
    avg_org_air_delta: float = 0.0


class InvestmentTracker:
    """Tracks PE investments and calculates ROI with AI-readiness attribution.

    Integrates with AssessmentHistoryService for score trends.
    """

    def __init__(self, history_service: Optional[AssessmentHistoryService] = None):
        self.history_service = history_service
        self._investments: Dict[str, Investment] = {}

    def record_investment(
        self,
        company_id: str,
        company_name: str,
        sector: str,
        entry_date: datetime,
        entry_ev_mm: float,
        entry_org_air: float,
        current_ev_mm: float,
        current_org_air: float,
        exit_date: Optional[datetime] = None,
        investment_amount_mm: float = 0.0,
    ) -> Investment:
        """Record a new investment position."""
        if entry_ev_mm < 0:
            raise ValueError("Entry enterprise value cannot be negative")
        if current_ev_mm < 0:
            raise ValueError("Current enterprise value cannot be negative")

        inv = Investment(
            company_id=company_id,
            company_name=company_name,
            sector=sector,
            entry_date=entry_date,
            entry_ev_mm=entry_ev_mm,
            entry_org_air=entry_org_air,
            current_ev_mm=current_ev_mm,
            current_org_air=current_org_air,
            exit_date=exit_date,
            investment_amount_mm=investment_amount_mm or entry_ev_mm,
        )
        self._investments[company_id] = inv

        logger.info(
            "investment_recorded",
            company_id=company_id,
            entry_ev=entry_ev_mm,
            current_ev=current_ev_mm,
        )
        return inv

    def update_current_value(
        self,
        company_id: str,
        current_ev_mm: float,
        current_org_air: Optional[float] = None,
        exit_date: Optional[datetime] = None,
    ) -> Investment:
        """Update mark-to-market value for an existing investment."""
        if company_id not in self._investments:
            raise KeyError(f"Investment not found: {company_id}")
        if current_ev_mm < 0:
            raise ValueError("Current enterprise value cannot be negative")

        inv = self._investments[company_id]
        inv.current_ev_mm = current_ev_mm
        if current_org_air is not None:
            inv.current_org_air = current_org_air
        if exit_date is not None:
            inv.exit_date = exit_date

        logger.info("investment_updated", company_id=company_id, current_ev=current_ev_mm)
        return inv

    def calculate_roi(self, company_id: str) -> InvestmentROI:
        """Calculate comprehensive ROI for a single investment."""
        if company_id not in self._investments:
            raise KeyError(f"Investment not found: {company_id}")

        inv = self._investments[company_id]
        entry_ev = inv.entry_ev_mm
        current_ev = inv.current_ev_mm

        # Holding period
        end_date = inv.exit_date or datetime.utcnow()
        holding_days = max((end_date - inv.entry_date).days, 1)  # min 1 day
        holding_years = holding_days / 365.25

        # Simple ROI
        if entry_ev > 0:
            simple_roi = ((current_ev - entry_ev) / entry_ev) * 100
            moic = current_ev / entry_ev
        else:
            simple_roi = 0.0
            moic = 0.0

        # Annualized ROI (CAGR)
        annualized_roi = self._calculate_annualized_roi(moic, holding_years)

        # IRR estimate
        irr = self._estimate_irr(moic, holding_years)

        # AI-Readiness attribution
        org_air_delta = inv.current_org_air - inv.entry_org_air
        ai_pct, ai_value = self._calculate_ai_attribution(
            inv.sector, org_air_delta, inv.entry_org_air,
            entry_ev, current_ev,
        )

        # Status
        if inv.exit_date:
            status = "loss" if current_ev < entry_ev else "realized"
        else:
            status = "loss" if current_ev < entry_ev else "active"

        roi = InvestmentROI(
            company_id=inv.company_id,
            company_name=inv.company_name,
            entry_ev_mm=entry_ev,
            current_ev_mm=current_ev,
            simple_roi_pct=round(simple_roi, 2),
            annualized_roi_pct=round(annualized_roi, 2),
            moic=round(moic, 2),
            holding_period_years=round(holding_years, 2),
            org_air_delta=round(org_air_delta, 1),
            ai_attributed_value_pct=round(ai_pct, 2),
            ai_attributed_value_mm=round(ai_value, 2),
            irr_estimate_pct=round(irr, 2),
            status=status,
        )

        logger.info(
            "roi_calculated",
            company_id=company_id,
            simple_roi=roi.simple_roi_pct,
            moic=roi.moic,
            ai_attribution=roi.ai_attributed_value_pct,
        )
        return roi

    def calculate_portfolio_roi(self, fund_id: str) -> PortfolioROISummary:
        """Calculate aggregated portfolio-level ROI."""
        if not self._investments:
            raise ValueError("No investments recorded")

        rois: List[InvestmentROI] = []
        for company_id in self._investments:
            rois.append(self.calculate_roi(company_id))

        total_invested = sum(r.entry_ev_mm for r in rois)
        total_current = sum(r.current_ev_mm for r in rois)

        # Portfolio MOIC
        portfolio_moic = total_current / total_invested if total_invested > 0 else 0.0

        # Portfolio ROI %
        portfolio_roi = ((total_current - total_invested) / total_invested * 100
                         if total_invested > 0 else 0.0)

        # EV-weighted average annualized ROI
        if total_invested > 0:
            weighted_ann_roi = sum(
                r.annualized_roi_pct * r.entry_ev_mm for r in rois
            ) / total_invested
        else:
            weighted_ann_roi = 0.0

        # AI attribution
        total_ai_value = sum(r.ai_attributed_value_mm for r in rois)
        avg_ai_pct = (sum(r.ai_attributed_value_pct for r in rois) / len(rois)
                      if rois else 0.0)

        # Counts
        active = sum(1 for r in rois if r.status == "active")
        realized = sum(1 for r in rois if r.status == "realized")
        loss = sum(1 for r in rois if r.status == "loss")

        # Best / worst
        best = max(rois, key=lambda r: r.simple_roi_pct) if rois else None
        worst = min(rois, key=lambda r: r.simple_roi_pct) if rois else None

        # Averages
        avg_holding = sum(r.holding_period_years for r in rois) / len(rois) if rois else 0.0
        avg_delta = sum(r.org_air_delta for r in rois) / len(rois) if rois else 0.0

        summary = PortfolioROISummary(
            fund_id=fund_id,
            total_invested_mm=round(total_invested, 2),
            total_current_value_mm=round(total_current, 2),
            portfolio_moic=round(portfolio_moic, 2),
            portfolio_roi_pct=round(portfolio_roi, 2),
            weighted_avg_annualized_roi_pct=round(weighted_ann_roi, 2),
            total_ai_attributed_value_mm=round(total_ai_value, 2),
            avg_ai_attribution_pct=round(avg_ai_pct, 2),
            investment_count=len(rois),
            active_count=active,
            realized_count=realized,
            loss_count=loss,
            best_performer=best,
            worst_performer=worst,
            avg_holding_period_years=round(avg_holding, 2),
            avg_org_air_delta=round(avg_delta, 1),
        )

        logger.info(
            "portfolio_roi_calculated",
            fund_id=fund_id,
            moic=summary.portfolio_moic,
            investment_count=summary.investment_count,
        )
        return summary

    async def get_ai_value_attribution(
        self, company_id: str
    ) -> Dict[str, float]:
        """Get detailed AI-readiness value attribution for a company."""
        if company_id not in self._investments:
            raise KeyError(f"Investment not found: {company_id}")

        inv = self._investments[company_id]
        org_air_delta = inv.current_org_air - inv.entry_org_air
        value_created = inv.current_ev_mm - inv.entry_ev_mm

        # Base AI attribution
        ai_pct, ai_value = self._calculate_ai_attribution(
            inv.sector, org_air_delta, inv.entry_org_air,
            inv.entry_ev_mm, inv.current_ev_mm,
        )

        result = {
            "company_id": company_id,
            "org_air_entry": inv.entry_org_air,
            "org_air_current": inv.current_org_air,
            "org_air_delta": round(org_air_delta, 1),
            "total_value_created_mm": round(value_created, 2),
            "ai_attributed_pct": round(ai_pct, 2),
            "ai_attributed_value_mm": round(ai_value, 2),
            "non_ai_value_mm": round(value_created - ai_value, 2),
            "sector_coefficient": SECTOR_AI_COEFFICIENTS.get(inv.sector, 0.15),
        }

        # Enrich with trend data if history service available
        if self.history_service:
            try:
                trend = await self.history_service.calculate_trend(company_id)
                result["trend_direction"] = trend.trend_direction
                result["delta_30d"] = trend.delta_30d
                result["delta_90d"] = trend.delta_90d
                result["snapshot_count"] = trend.snapshot_count
            except Exception as e:
                logger.warning("trend_enrichment_failed", error=str(e))

        return result

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _calculate_ai_attribution(
        sector: str,
        org_air_delta: float,
        entry_org_air: float,
        entry_ev: float,
        current_ev: float,
    ) -> tuple:
        """Calculate AI-attributed value creation."""
        value_created = current_ev - entry_ev

        # No value created or AI scores declined → no AI attribution
        if value_created <= 0 or org_air_delta <= 0:
            return (0.0, 0.0)

        # Sector-specific base coefficient
        base_coeff = SECTOR_AI_COEFFICIENTS.get(sector, 0.15)

        # Normalized delta
        max_possible = 100.0 - entry_org_air
        if max_possible <= 0:
            normalized_delta = 1.0
        else:
            normalized_delta = min(org_air_delta / max_possible, 1.0)

        # AI attribution percentage (capped)
        ai_pct = min(normalized_delta * base_coeff, AI_ATTRIBUTION_CAP) * 100

        # Dollar value of AI attribution
        ai_value = value_created * (ai_pct / 100.0)

        return (ai_pct, ai_value)

    @staticmethod
    def _calculate_annualized_roi(moic: float, years: float) -> float:
        """Calculate annualized ROI (CAGR) from MOIC and holding period."""
        if moic <= 0 or years <= 0:
            return -100.0 if moic <= 0 and years > 0 else 0.0
        try:
            return (moic ** (1.0 / years) - 1) * 100
        except (OverflowError, ZeroDivisionError):
            return 0.0

    @staticmethod
    def _estimate_irr(moic: float, years: float) -> float:
        """Estimate IRR using simplified MOIC-based approximation."""
        if moic <= 0 or years <= 0:
            return -100.0 if moic <= 0 and years > 0 else 0.0
        try:
            return (moic ** (1.0 / years) - 1) * 100
        except (OverflowError, ZeroDivisionError):
            return 0.0


# Factory function
def create_investment_tracker(
    history_service: Optional[AssessmentHistoryService] = None,
) -> InvestmentTracker:
    """Create an InvestmentTracker, optionally with history integration."""
    return InvestmentTracker(history_service=history_service)
