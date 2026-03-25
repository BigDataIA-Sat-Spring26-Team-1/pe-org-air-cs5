"""
Tests for Fund-AI-R Calculator — Task 10.5.

Verifies EV-weighted aggregation, quartile distribution,
sector HHI, leader/laggard counts, and edge cases.
"""

import pytest
from app.services.analytics.fund_air import (
    FundAIRCalculator,
    FundMetrics,
    SECTOR_BENCHMARKS,
    fund_air_calculator,
)
from app.services.integration.portfolio_data_service import PortfolioCompanyView


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_company(
    company_id: str,
    ticker: str,
    name: str,
    sector: str = "technology",
    org_air: float = 60.0,
    delta_since_entry: float = 5.0,
) -> PortfolioCompanyView:
    return PortfolioCompanyView(
        company_id=company_id,
        ticker=ticker,
        name=name,
        sector=sector,
        org_air=org_air,
        vr_score=50.0,
        hr_score=50.0,
        synergy_score=1.0,
        dimension_scores={},
        confidence_interval=(40.0, 80.0),
        entry_org_air=org_air - delta_since_entry,
        delta_since_entry=delta_since_entry,
        evidence_count=10,
    )


SAMPLE_COMPANIES = [
    _make_company("c1", "NVDA", "NVIDIA", "technology", org_air=85.0, delta_since_entry=10.0),
    _make_company("c2", "MSFT", "Microsoft", "technology", org_air=78.0, delta_since_entry=8.0),
    _make_company("c3", "JNJ", "Johnson & Johnson", "healthcare", org_air=55.0, delta_since_entry=-2.0),
    _make_company("c4", "XOM", "ExxonMobil", "energy", org_air=40.0, delta_since_entry=3.0),
]

SAMPLE_EVS = {
    "c1": 500.0,
    "c2": 300.0,
    "c3": 200.0,
    "c4": 100.0,
}


# ---------------------------------------------------------------------------
# Basic calculation
# ---------------------------------------------------------------------------

class TestFundMetricsCalculation:

    def test_ev_weighted_fund_air(self):
        calc = FundAIRCalculator()
        result = calc.calculate_fund_metrics("fund-1", SAMPLE_COMPANIES, SAMPLE_EVS)

        # Manual: (500*85 + 300*78 + 200*55 + 100*40) / 1100
        # = (42500 + 23400 + 11000 + 4000) / 1100 = 80900 / 1100 = 73.545...
        assert isinstance(result, FundMetrics)
        assert result.fund_id == "fund-1"
        assert result.fund_air == 73.5  # rounded to 1 decimal
        assert result.company_count == 4

    def test_total_ev(self):
        calc = FundAIRCalculator()
        result = calc.calculate_fund_metrics("fund-1", SAMPLE_COMPANIES, SAMPLE_EVS)

        assert result.total_ev_mm == 1100.0

    def test_avg_delta_since_entry(self):
        calc = FundAIRCalculator()
        result = calc.calculate_fund_metrics("fund-1", SAMPLE_COMPANIES, SAMPLE_EVS)

        # (10 + 8 + (-2) + 3) / 4 = 19 / 4 = 4.75
        assert result.avg_delta_since_entry == 4.8  # rounded to 1 decimal


# ---------------------------------------------------------------------------
# Leader / Laggard counts
# ---------------------------------------------------------------------------

class TestLeaderLaggardCounts:

    def test_leaders_count(self):
        calc = FundAIRCalculator()
        result = calc.calculate_fund_metrics("fund-1", SAMPLE_COMPANIES, SAMPLE_EVS)

        # NVDA=85 >= 70, MSFT=78 >= 70 → 2 leaders
        assert result.ai_leaders_count == 2

    def test_laggards_count(self):
        calc = FundAIRCalculator()
        result = calc.calculate_fund_metrics("fund-1", SAMPLE_COMPANIES, SAMPLE_EVS)

        # XOM=40 < 50 → 1 laggard
        assert result.ai_laggards_count == 1


# ---------------------------------------------------------------------------
# Quartile distribution
# ---------------------------------------------------------------------------

class TestQuartileDistribution:

    def test_quartile_counts(self):
        calc = FundAIRCalculator()
        result = calc.calculate_fund_metrics("fund-1", SAMPLE_COMPANIES, SAMPLE_EVS)

        dist = result.quartile_distribution
        assert sum(dist.values()) == 4  # all companies assigned
        assert all(q in dist for q in [1, 2, 3, 4])

    def test_quartile_assignment_technology(self):
        calc = FundAIRCalculator()
        # NVDA=85 in technology: q1 threshold=75 → quartile 1
        assert calc._get_quartile(85.0, "technology") == 1
        # MSFT=78 in technology: q1=75 → quartile 1
        assert calc._get_quartile(78.0, "technology") == 1
        # Score=65 in technology: q2=65 → quartile 2
        assert calc._get_quartile(65.0, "technology") == 2
        # Score=55 in technology: q3=55 → quartile 3
        assert calc._get_quartile(55.0, "technology") == 3
        # Score=44 in technology: below q4=45 → quartile 4
        assert calc._get_quartile(44.0, "technology") == 4

    def test_quartile_unknown_sector_defaults_to_technology(self):
        calc = FundAIRCalculator()
        # Unknown sector should use technology benchmarks
        assert calc._get_quartile(80.0, "unknown_sector") == 1


# ---------------------------------------------------------------------------
# Sector HHI
# ---------------------------------------------------------------------------

class TestSectorHHI:

    def test_hhi_value(self):
        calc = FundAIRCalculator()
        result = calc.calculate_fund_metrics("fund-1", SAMPLE_COMPANIES, SAMPLE_EVS)

        # tech EV = 800, healthcare = 200, energy = 100, total = 1100
        # HHI = (800/1100)^2 + (200/1100)^2 + (100/1100)^2
        # = 0.5289... + 0.0331... + 0.0083... ≈ 0.5703
        assert 0.5 < result.sector_hhi < 0.6

    def test_single_sector_hhi_is_one(self):
        calc = FundAIRCalculator()
        companies = [
            _make_company("c1", "A", "CompA", "technology", 80.0),
            _make_company("c2", "B", "CompB", "technology", 70.0),
        ]
        evs = {"c1": 100.0, "c2": 100.0}
        result = calc.calculate_fund_metrics("fund-1", companies, evs)

        assert result.sector_hhi == 1.0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_empty_portfolio_raises(self):
        calc = FundAIRCalculator()
        with pytest.raises(ValueError, match="Cannot calculate Fund-AI-R for empty portfolio"):
            calc.calculate_fund_metrics("fund-1", [], {})

    def test_default_ev_when_missing(self):
        calc = FundAIRCalculator()
        companies = [_make_company("c1", "A", "CompA", org_air=60.0)]
        # No EV provided — defaults to 100.0
        result = calc.calculate_fund_metrics("fund-1", companies, {})
        assert result.fund_air == 60.0
        assert result.total_ev_mm == 100.0

    def test_singleton_instance(self):
        assert isinstance(fund_air_calculator, FundAIRCalculator)
