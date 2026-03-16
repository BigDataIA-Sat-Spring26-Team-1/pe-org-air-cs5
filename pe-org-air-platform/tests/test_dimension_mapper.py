"""
Tests for DimensionMapper — Teammate B Task 2.

Validates the CS3 Signal-to-Dimension mapping matrix ensuring every
signal category resolves to a correct OrgAIR scoring dimension.
"""

import pytest
from app.services.retrieval.dimension_mapper import DimensionMapper
from app.models.enums import Dimension
from app.models.rag import SignalCategory, SourceType


@pytest.fixture
def mapper():
    return DimensionMapper()


# ---- Category-level mappings ----

def test_job_posting_maps_to_talent(mapper):
    """technology_hiring signals → TALENT dimension."""
    assert mapper.get_primary_dimension(SignalCategory.TECHNOLOGY_HIRING) == Dimension.TALENT
    assert mapper.get_primary_dimension(SignalCategory.TALENT) == Dimension.TALENT


def test_patent_maps_to_use_case_portfolio(mapper):
    """innovation_activity signals → USE_CASE_PORTFOLIO dimension."""
    assert mapper.get_primary_dimension(SignalCategory.INNOVATION_ACTIVITY) == Dimension.USE_CASE_PORTFOLIO
    assert mapper.get_primary_dimension(SignalCategory.INNOVATION) == Dimension.USE_CASE_PORTFOLIO


def test_digital_presence_maps_to_tech_stack(mapper):
    """digital_presence signals → TECHNOLOGY_STACK."""
    assert mapper.get_primary_dimension(SignalCategory.DIGITAL_PRESENCE) == Dimension.TECHNOLOGY_STACK
    assert mapper.get_primary_dimension(SignalCategory.TECHNOLOGY_STACK) == Dimension.TECHNOLOGY_STACK


def test_leadership_maps_to_leadership(mapper):
    """leadership signals → LEADERSHIP dimension."""
    assert mapper.get_primary_dimension(SignalCategory.LEADERSHIP_SIGNALS) == Dimension.LEADERSHIP
    assert mapper.get_primary_dimension(SignalCategory.LEADERSHIP) == Dimension.LEADERSHIP


def test_culture_maps_to_culture(mapper):
    """culture_signals → CULTURE dimension."""
    assert mapper.get_primary_dimension(SignalCategory.CULTURE_SIGNALS) == Dimension.CULTURE


def test_governance_maps_to_ai_governance(mapper):
    """governance_signals → AI_GOVERNANCE dimension."""
    assert mapper.get_primary_dimension(SignalCategory.GOVERNANCE_SIGNALS) == Dimension.AI_GOVERNANCE


def test_sec_filing_maps_to_data_infrastructure(mapper):
    """sec_filing category → DATA_INFRASTRUCTURE."""
    assert mapper.get_primary_dimension(SignalCategory.SEC_FILING) == Dimension.DATA_INFRASTRUCTURE


def test_unknown_defaults_to_data_infrastructure(mapper):
    """Unknown/unrecognised categories fall back to DATA_INFRASTRUCTURE."""
    assert mapper.get_primary_dimension("completely_unknown_category") == Dimension.DATA_INFRASTRUCTURE
    assert mapper.get_primary_dimension(SignalCategory.GENERAL) == Dimension.DATA_INFRASTRUCTURE


# ---- Source-type overrides ----

def test_source_override_patent(mapper):
    """Patent source type overrides any category."""
    dim = mapper.get_primary_dimension(
        SignalCategory.GENERAL,
        source_type=SourceType.PATENT_USPTO,
    )
    assert dim == Dimension.USE_CASE_PORTFOLIO


def test_source_override_job_posting(mapper):
    """Job posting source type overrides to TALENT."""
    dim = mapper.get_primary_dimension(
        SignalCategory.GENERAL,
        source_type=SourceType.JOB_POSTING_LINKEDIN,
    )
    assert dim == Dimension.TALENT


def test_source_override_glassdoor(mapper):
    """Glassdoor source type overrides to CULTURE."""
    dim = mapper.get_primary_dimension(
        SignalCategory.GENERAL,
        source_type=SourceType.GLASSDOOR_REVIEW,
    )
    assert dim == Dimension.CULTURE


def test_source_override_board_proxy(mapper):
    """Board proxy source type overrides to AI_GOVERNANCE."""
    dim = mapper.get_primary_dimension(
        SignalCategory.GENERAL,
        source_type=SourceType.BOARD_PROXY_DEF14A,
    )
    assert dim == Dimension.AI_GOVERNANCE


# ---- Confidence boosts ----

def test_confidence_boost_is_positive(mapper):
    """All mapped categories have a non-negative boost."""
    for cat in SignalCategory:
        boost = mapper.get_confidence_boost(cat)
        assert boost >= 0.0, f"Negative boost for {cat}: {boost}"


def test_talent_boost_is_010(mapper):
    """Technology hiring gives a +0.10 confidence boost."""
    assert mapper.get_confidence_boost(SignalCategory.TECHNOLOGY_HIRING) == 0.10


def test_unknown_boost_is_zero(mapper):
    """Unknown categories should have zero boost."""
    assert mapper.get_confidence_boost("unknown_signal") == 0.0


# ---- get_all_mappings ----

def test_get_all_mappings_returns_list(mapper):
    """get_all_mappings returns a non-empty list of dicts."""
    mappings = mapper.get_all_mappings()
    assert isinstance(mappings, list)
    assert len(mappings) > 0
    for row in mappings:
        assert "primary_dimension" in row
        assert "confidence_boost" in row
        assert "mapping_source" in row


def test_string_signal_category_also_works(mapper):
    """Passing a plain string instead of an enum still resolves correctly."""
    assert mapper.get_primary_dimension("technology_hiring") == Dimension.TALENT
    assert mapper.get_confidence_boost("innovation_activity") == 0.05
