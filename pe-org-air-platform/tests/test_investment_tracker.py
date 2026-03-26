"""
Tests for Investment Tracker with ROI — Bonus 2.

Verifies investment recording, ROI/MOIC/IRR calculations,
AI-readiness value attribution, portfolio aggregation, and edge cases.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal

from app.services.tracking.investment_tracker import (
    Investment,
    InvestmentROI,
    InvestmentTracker,
    PortfolioROISummary,
    SECTOR_AI_COEFFICIENTS,
    AI_ATTRIBUTION_CAP,
    create_investment_tracker,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime.utcnow()
TWO_YEARS_AGO = NOW - timedelta(days=730)
ONE_YEAR_AGO = NOW - timedelta(days=365)
SIX_MONTHS_AGO = NOW - timedelta(days=183)


def _make_tracker() -> InvestmentTracker:
    return InvestmentTracker()


def _seed_investment(
    tracker: InvestmentTracker,
    company_id: str = "c-001",
    company_name: str = "NVIDIA",
    sector: str = "technology",
    entry_ev: float = 500.0,
    current_ev: float = 750.0,
    entry_org_air: float = 55.0,
    current_org_air: float = 80.0,
    entry_date: datetime = ONE_YEAR_AGO,
    exit_date: datetime = None,
) -> Investment:
    return tracker.record_investment(
        company_id=company_id,
        company_name=company_name,
        sector=sector,
        entry_date=entry_date,
        entry_ev_mm=entry_ev,
        entry_org_air=entry_org_air,
        current_ev_mm=current_ev,
        current_org_air=current_org_air,
        exit_date=exit_date,
    )


# ---------------------------------------------------------------------------
# Record Investment
# ---------------------------------------------------------------------------

class TestRecordInvestment:

    def test_basic_record(self):
        tracker = _make_tracker()
        inv = _seed_investment(tracker)

        assert inv.company_id == "c-001"
        assert inv.company_name == "NVIDIA"
        assert inv.sector == "technology"
        assert inv.entry_ev_mm == 500.0
        assert inv.current_ev_mm == 750.0
        assert inv.entry_org_air == 55.0
        assert inv.current_org_air == 80.0

    def test_investment_stored(self):
        tracker = _make_tracker()
        _seed_investment(tracker)
        assert "c-001" in tracker._investments

    def test_negative_entry_ev_raises(self):
        tracker = _make_tracker()
        with pytest.raises(ValueError, match="Entry enterprise value cannot be negative"):
            _seed_investment(tracker, entry_ev=-100.0)

    def test_negative_current_ev_raises(self):
        tracker = _make_tracker()
        with pytest.raises(ValueError, match="Current enterprise value cannot be negative"):
            _seed_investment(tracker, current_ev=-50.0)

    def test_default_investment_amount(self):
        tracker = _make_tracker()
        inv = _seed_investment(tracker)
        # Default investment_amount_mm should equal entry_ev_mm
        assert inv.investment_amount_mm == inv.entry_ev_mm

    def test_overwrites_existing_investment(self):
        tracker = _make_tracker()
        _seed_investment(tracker, current_ev=500.0)
        _seed_investment(tracker, current_ev=900.0)
        assert tracker._investments["c-001"].current_ev_mm == 900.0


# ---------------------------------------------------------------------------
# Update Current Value
# ---------------------------------------------------------------------------

class TestUpdateCurrentValue:

    def test_update_ev(self):
        tracker = _make_tracker()
        _seed_investment(tracker)
        tracker.update_current_value("c-001", 1000.0)

        assert tracker._investments["c-001"].current_ev_mm == 1000.0

    def test_update_ev_and_org_air(self):
        tracker = _make_tracker()
        _seed_investment(tracker)
        tracker.update_current_value("c-001", 900.0, current_org_air=85.0)

        inv = tracker._investments["c-001"]
        assert inv.current_ev_mm == 900.0
        assert inv.current_org_air == 85.0

    def test_update_with_exit_date(self):
        tracker = _make_tracker()
        _seed_investment(tracker)
        exit_dt = datetime.utcnow()
        tracker.update_current_value("c-001", 800.0, exit_date=exit_dt)

        assert tracker._investments["c-001"].exit_date == exit_dt

    def test_update_unknown_company_raises(self):
        tracker = _make_tracker()
        with pytest.raises(KeyError, match="Investment not found"):
            tracker.update_current_value("unknown", 100.0)

    def test_update_negative_ev_raises(self):
        tracker = _make_tracker()
        _seed_investment(tracker)
        with pytest.raises(ValueError, match="Current enterprise value cannot be negative"):
            tracker.update_current_value("c-001", -50.0)


# ---------------------------------------------------------------------------
# Calculate ROI
# ---------------------------------------------------------------------------

class TestCalculateROI:

    def test_basic_roi(self):
        tracker = _make_tracker()
        _seed_investment(tracker, entry_ev=500.0, current_ev=750.0)
        roi = tracker.calculate_roi("c-001")

        assert roi.simple_roi_pct == 50.0
        assert roi.moic == 1.5
        assert roi.status == "active"

    def test_realized_investment(self):
        tracker = _make_tracker()
        _seed_investment(tracker, entry_ev=500.0, current_ev=1000.0,
                        exit_date=datetime.utcnow())
        roi = tracker.calculate_roi("c-001")

        assert roi.status == "realized"
        assert roi.simple_roi_pct == 100.0
        assert roi.moic == 2.0

    def test_loss_investment(self):
        tracker = _make_tracker()
        _seed_investment(tracker, entry_ev=500.0, current_ev=300.0)
        roi = tracker.calculate_roi("c-001")

        assert roi.status == "loss"
        assert roi.simple_roi_pct == -40.0
        assert roi.moic == 0.6

    def test_zero_entry_ev(self):
        tracker = _make_tracker()
        _seed_investment(tracker, entry_ev=0.0, current_ev=100.0)
        roi = tracker.calculate_roi("c-001")

        assert roi.simple_roi_pct == 0.0
        assert roi.moic == 0.0

    def test_annualized_roi_positive(self):
        tracker = _make_tracker()
        _seed_investment(tracker, entry_ev=500.0, current_ev=750.0,
                        entry_date=TWO_YEARS_AGO)
        roi = tracker.calculate_roi("c-001")

        # MOIC=1.5 over ~2 years → annualized ~ 22.5%
        assert 20 < roi.annualized_roi_pct < 25

    def test_annualized_roi_loss(self):
        tracker = _make_tracker()
        _seed_investment(tracker, entry_ev=500.0, current_ev=0.0,
                        entry_date=ONE_YEAR_AGO)
        roi = tracker.calculate_roi("c-001")

        assert roi.annualized_roi_pct == -100.0

    def test_holding_period_calculated(self):
        tracker = _make_tracker()
        _seed_investment(tracker, entry_date=ONE_YEAR_AGO)
        roi = tracker.calculate_roi("c-001")

        assert 0.9 < roi.holding_period_years < 1.1

    def test_unknown_company_raises(self):
        tracker = _make_tracker()
        with pytest.raises(KeyError, match="Investment not found"):
            tracker.calculate_roi("unknown")

    def test_org_air_delta_tracked(self):
        tracker = _make_tracker()
        _seed_investment(tracker, entry_org_air=55.0, current_org_air=80.0)
        roi = tracker.calculate_roi("c-001")

        assert roi.org_air_delta == 25.0

    def test_irr_estimate(self):
        tracker = _make_tracker()
        _seed_investment(tracker, entry_ev=500.0, current_ev=750.0,
                        entry_date=TWO_YEARS_AGO)
        roi = tracker.calculate_roi("c-001")

        # IRR ≈ annualized ROI for single cash flow
        assert roi.irr_estimate_pct > 0


# ---------------------------------------------------------------------------
# AI Attribution
# ---------------------------------------------------------------------------

class TestAIAttribution:

    def test_positive_attribution_technology(self):
        tracker = _make_tracker()
        _seed_investment(tracker, sector="technology",
                        entry_org_air=55.0, current_org_air=80.0,
                        entry_ev=500.0, current_ev=750.0)
        roi = tracker.calculate_roi("c-001")

        assert roi.ai_attributed_value_pct > 0
        assert roi.ai_attributed_value_mm > 0

    def test_no_attribution_when_score_declined(self):
        tracker = _make_tracker()
        _seed_investment(tracker, entry_org_air=80.0, current_org_air=60.0,
                        entry_ev=500.0, current_ev=750.0)
        roi = tracker.calculate_roi("c-001")

        assert roi.ai_attributed_value_pct == 0.0
        assert roi.ai_attributed_value_mm == 0.0

    def test_no_attribution_when_value_lost(self):
        tracker = _make_tracker()
        _seed_investment(tracker, entry_org_air=55.0, current_org_air=80.0,
                        entry_ev=500.0, current_ev=400.0)
        roi = tracker.calculate_roi("c-001")

        assert roi.ai_attributed_value_pct == 0.0
        assert roi.ai_attributed_value_mm == 0.0

    def test_attribution_capped(self):
        """AI attribution should never exceed AI_ATTRIBUTION_CAP (40%)."""
        tracker = _make_tracker()
        # Massive org_air improvement to trigger cap
        _seed_investment(tracker, sector="technology",
                        entry_org_air=10.0, current_org_air=99.0,
                        entry_ev=100.0, current_ev=1000.0)
        roi = tracker.calculate_roi("c-001")

        assert roi.ai_attributed_value_pct <= AI_ATTRIBUTION_CAP * 100

    def test_sector_coefficient_matters(self):
        tracker1 = _make_tracker()
        tracker2 = _make_tracker()

        _seed_investment(tracker1, company_id="tech", sector="technology",
                        entry_org_air=50.0, current_org_air=80.0,
                        entry_ev=500.0, current_ev=750.0)
        _seed_investment(tracker2, company_id="energy", sector="energy",
                        entry_org_air=50.0, current_org_air=80.0,
                        entry_ev=500.0, current_ev=750.0)

        roi_tech = tracker1.calculate_roi("tech")
        roi_energy = tracker2.calculate_roi("energy")

        # Tech has higher AI coefficient than energy
        assert roi_tech.ai_attributed_value_pct > roi_energy.ai_attributed_value_pct

    def test_entry_org_air_at_100(self):
        """Edge case: entry score already at max."""
        tracker = _make_tracker()
        _seed_investment(tracker, entry_org_air=100.0, current_org_air=100.0,
                        entry_ev=500.0, current_ev=700.0)
        roi = tracker.calculate_roi("c-001")

        # No AI improvement possible
        assert roi.ai_attributed_value_pct == 0.0


# ---------------------------------------------------------------------------
# Portfolio ROI
# ---------------------------------------------------------------------------

class TestPortfolioROI:

    def test_basic_portfolio(self):
        tracker = _make_tracker()
        _seed_investment(tracker, company_id="c-001", entry_ev=500.0,
                        current_ev=750.0, entry_date=ONE_YEAR_AGO)
        _seed_investment(tracker, company_id="c-002", company_name="Microsoft",
                        sector="technology", entry_ev=300.0, current_ev=420.0,
                        entry_org_air=60.0, current_org_air=75.0,
                        entry_date=SIX_MONTHS_AGO)

        summary = tracker.calculate_portfolio_roi("fund-1")

        assert summary.fund_id == "fund-1"
        assert summary.investment_count == 2
        assert summary.total_invested_mm == 800.0
        assert summary.total_current_value_mm == 1170.0
        assert summary.portfolio_moic > 1.0
        assert summary.portfolio_roi_pct > 0

    def test_portfolio_best_worst(self):
        tracker = _make_tracker()
        _seed_investment(tracker, company_id="winner", company_name="Winner",
                        entry_ev=100.0, current_ev=300.0, entry_date=ONE_YEAR_AGO)
        _seed_investment(tracker, company_id="loser", company_name="Loser",
                        entry_ev=100.0, current_ev=50.0, entry_date=ONE_YEAR_AGO)

        summary = tracker.calculate_portfolio_roi("fund-1")

        assert summary.best_performer.company_id == "winner"
        assert summary.worst_performer.company_id == "loser"

    def test_empty_portfolio_raises(self):
        tracker = _make_tracker()
        with pytest.raises(ValueError, match="No investments recorded"):
            tracker.calculate_portfolio_roi("fund-1")

    def test_portfolio_counts(self):
        tracker = _make_tracker()
        # Active (current > entry, no exit)
        _seed_investment(tracker, company_id="active", entry_ev=100.0,
                        current_ev=150.0, entry_date=ONE_YEAR_AGO)
        # Realized (has exit, profit)
        _seed_investment(tracker, company_id="realized", entry_ev=100.0,
                        current_ev=200.0, entry_date=TWO_YEARS_AGO,
                        exit_date=NOW)
        # Loss (current < entry)
        _seed_investment(tracker, company_id="loss", entry_ev=100.0,
                        current_ev=60.0, entry_date=ONE_YEAR_AGO)

        summary = tracker.calculate_portfolio_roi("fund-1")

        assert summary.active_count == 1
        assert summary.realized_count == 1
        assert summary.loss_count == 1

    def test_portfolio_moic(self):
        tracker = _make_tracker()
        _seed_investment(tracker, company_id="c-001", entry_ev=500.0,
                        current_ev=1000.0, entry_date=ONE_YEAR_AGO)
        _seed_investment(tracker, company_id="c-002", company_name="CompB",
                        entry_ev=500.0, current_ev=500.0,
                        entry_date=ONE_YEAR_AGO)

        summary = tracker.calculate_portfolio_roi("fund-1")

        # Total invested 1000, total current 1500 → MOIC = 1.5
        assert summary.portfolio_moic == 1.5

    def test_portfolio_ai_attribution(self):
        tracker = _make_tracker()
        _seed_investment(tracker, company_id="c-001", sector="technology",
                        entry_ev=500.0, current_ev=750.0,
                        entry_org_air=55.0, current_org_air=80.0,
                        entry_date=ONE_YEAR_AGO)

        summary = tracker.calculate_portfolio_roi("fund-1")

        assert summary.total_ai_attributed_value_mm > 0
        assert summary.avg_ai_attribution_pct > 0


# ---------------------------------------------------------------------------
# AI Value Attribution (async, with history service)
# ---------------------------------------------------------------------------

class TestGetAIValueAttribution:

    @pytest.mark.asyncio
    async def test_basic_attribution(self):
        tracker = _make_tracker()
        _seed_investment(tracker, entry_ev=500.0, current_ev=750.0,
                        entry_org_air=55.0, current_org_air=80.0)

        result = await tracker.get_ai_value_attribution("c-001")

        assert result["org_air_delta"] == 25.0
        assert result["total_value_created_mm"] == 250.0
        assert result["ai_attributed_pct"] > 0
        assert result["ai_attributed_value_mm"] > 0

    @pytest.mark.asyncio
    async def test_with_history_service(self):
        # Mock the history service
        mock_history = MagicMock()
        mock_trend = MagicMock()
        mock_trend.trend_direction = "improving"
        mock_trend.delta_30d = 5.0
        mock_trend.delta_90d = 12.0
        mock_trend.snapshot_count = 8
        mock_history.calculate_trend = AsyncMock(return_value=mock_trend)

        tracker = InvestmentTracker(history_service=mock_history)
        _seed_investment(tracker, entry_ev=500.0, current_ev=750.0)

        result = await tracker.get_ai_value_attribution("c-001")

        assert result["trend_direction"] == "improving"
        assert result["delta_30d"] == 5.0
        assert result["delta_90d"] == 12.0
        assert result["snapshot_count"] == 8

    @pytest.mark.asyncio
    async def test_unknown_company_raises(self):
        tracker = _make_tracker()
        with pytest.raises(KeyError, match="Investment not found"):
            await tracker.get_ai_value_attribution("unknown")

    @pytest.mark.asyncio
    async def test_no_value_created(self):
        tracker = _make_tracker()
        _seed_investment(tracker, entry_ev=500.0, current_ev=500.0,
                        entry_org_air=55.0, current_org_air=80.0)

        result = await tracker.get_ai_value_attribution("c-001")

        assert result["total_value_created_mm"] == 0.0
        assert result["ai_attributed_value_mm"] == 0.0


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class TestFactory:

    def test_create_without_history(self):
        tracker = create_investment_tracker()
        assert isinstance(tracker, InvestmentTracker)
        assert tracker.history_service is None

    def test_create_with_history(self):
        mock_history = MagicMock()
        tracker = create_investment_tracker(history_service=mock_history)
        assert tracker.history_service is mock_history
