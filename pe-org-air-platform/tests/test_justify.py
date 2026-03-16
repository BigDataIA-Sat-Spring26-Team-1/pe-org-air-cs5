"""
Tests for the /justify endpoint and underlying services.

Follows the project's httpx + pytest-asyncio pattern (see conftest.py and
test_api.py).  All external dependencies (LLM router, Snowflake, retriever)
are mocked so the suite runs fully offline.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.rag import (
    CitedEvidence,
    Dimension,
    ICMeetingPackage,
    RetrievedDocument,
    ScoreJustification,
    ScoreLevel,
)
from app.services.justification.generator import (
    DIMENSION_QUERIES,
    JustificationGenerator,
    approximate_confidence_interval,
    build_cited_evidence,
    derive_evidence_strength,
    score_to_level,
)
from app.services.workflows.ic_prep import (
    ICPrepWorkflow,
    _build_company_model,
    _estimate_dimension_score,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_doc(doc_id: str = "doc1", score: float = 0.8) -> RetrievedDocument:
    return RetrievedDocument(
        doc_id=doc_id,
        content="The company deployed an enterprise data lake on AWS S3 and Databricks.",
        metadata={
            "company_id": "AAPL",
            "source_type": "sec_filing",
            "confidence": 0.9,
        },
        score=score,
        retrieval_method="hybrid",
    )


def _make_justification(
    dimension: Dimension = Dimension.TALENT,
    score: float = 72.5,
) -> ScoreJustification:
    return ScoreJustification(
        company_id="AAPL",
        dimension=dimension,
        score=score,
        level=ScoreLevel.LEVEL_4,
        level_name="Good",
        confidence_interval=(67.0, 78.0),
        rubric_criteria="AI/ML hiring velocity and engineering density.",
        rubric_keywords=["hiring", "talent"],
        supporting_evidence=[],
        gaps_identified=["Senior ML leadership bench remains thin."],
        generated_summary="AAPL demonstrates strong AI talent acquisition signals.",
        evidence_strength="strong",
    )


# ---------------------------------------------------------------------------
# Unit tests — pure helpers
# ---------------------------------------------------------------------------

class TestScoreToLevel:
    def test_excellent(self):
        assert score_to_level(85.0) == (ScoreLevel.LEVEL_5, "Excellent")

    def test_good(self):
        assert score_to_level(65.0) == (ScoreLevel.LEVEL_4, "Good")

    def test_adequate(self):
        assert score_to_level(50.0) == (ScoreLevel.LEVEL_3, "Adequate")

    def test_developing(self):
        assert score_to_level(30.0) == (ScoreLevel.LEVEL_2, "Developing")

    def test_nascent(self):
        assert score_to_level(10.0) == (ScoreLevel.LEVEL_1, "Nascent")

    def test_boundary_80(self):
        assert score_to_level(80.0)[1] == "Excellent"

    def test_boundary_60(self):
        assert score_to_level(60.0)[1] == "Good"


class TestDeriveEvidenceStrength:
    def test_strong(self):
        docs = [_make_doc(f"d{i}") for i in range(4)]
        assert derive_evidence_strength(docs) == "strong"

    def test_moderate(self):
        docs = [_make_doc(f"d{i}") for i in range(2)]
        assert derive_evidence_strength(docs) == "moderate"

    def test_weak(self):
        assert derive_evidence_strength([_make_doc()]) == "weak"

    def test_empty(self):
        assert derive_evidence_strength([]) == "weak"


class TestApproximateCI:
    def test_narrows_with_more_evidence(self):
        lo_ci = approximate_confidence_interval(50.0, 1)
        hi_ci = approximate_confidence_interval(50.0, 25)
        lo_width = lo_ci[1] - lo_ci[0]
        hi_width = hi_ci[1] - hi_ci[0]
        assert lo_width > hi_width

    def test_clamps_to_valid_range(self):
        lo, hi = approximate_confidence_interval(0.0, 1)
        assert lo >= 0.0
        lo, hi = approximate_confidence_interval(100.0, 1)
        assert hi <= 100.0


class TestBuildCitedEvidence:
    def test_converts_docs(self):
        docs = [_make_doc("d1"), _make_doc("d2")]
        cited = build_cited_evidence(docs)
        assert len(cited) == 2
        assert all(isinstance(c, CitedEvidence) for c in cited)

    def test_content_capped_at_500(self):
        doc = _make_doc()
        doc.content = "x" * 600
        cited = build_cited_evidence([doc])
        assert len(cited[0].content) == 500


class TestBuildCompanyModel:
    def test_builds_from_row(self):
        row = {
            "id": "uuid-123",
            "name": "Apple Inc.",
            "sector": "technology",
            "sub_sector": "Consumer Electronics",
            "market_cap_percentile": 0.95,
            "revenue_millions": 394000.0,
            "employee_count": 160000,
            "fiscal_year_end": "09/30",
        }
        company = _build_company_model("AAPL", row)
        assert company.ticker == "AAPL"
        assert company.name == "Apple Inc."
        assert company.employee_count == 160000

    def test_defaults_on_missing_row(self):
        company = _build_company_model("AAPL", None)
        assert company.ticker == "AAPL"
        assert company.revenue_millions == 0.0

    def test_unknown_sector_falls_back(self):
        row = {"sector": "nonexistent_sector_xyz"}
        company = _build_company_model("XYZ", row)
        assert company.sector.value == "business_services"


class TestEstimateDimensionScore:
    def test_zero_evidence(self):
        assert _estimate_dimension_score(0, 0.0) == 0.0

    def test_high_count_high_relevance(self):
        score = _estimate_dimension_score(5, 0.9)
        assert score > 50.0

    def test_caps_at_100(self):
        score = _estimate_dimension_score(100, 1.0)
        assert score <= 100.0


class TestDimensionQueriesComplete:
    def test_all_7_dimensions_have_queries(self):
        for dim in Dimension:
            assert dim in DIMENSION_QUERIES, f"Missing query for {dim}"
            assert len(DIMENSION_QUERIES[dim]) > 10


# ---------------------------------------------------------------------------
# Unit tests — JustificationGenerator (mocked LLM)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_justification_generator_success():
    """Generator returns a ScoreJustification with LLM content."""
    mock_router = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = (
        "AAPL demonstrates robust AI talent acquisition with 500+ ML job postings [1]. "
        "The data science org has grown 40% YoY [2]. "
        "Senior ML leadership bench remains thin."
    )
    mock_router.complete.return_value = mock_response

    gen = JustificationGenerator(llm_router=mock_router)
    docs = [_make_doc("d1"), _make_doc("d2")]
    result = await gen.generate(
        company_id="AAPL",
        dimension=Dimension.TALENT,
        score=72.5,
        evidence=docs,
    )

    assert isinstance(result, ScoreJustification)
    assert result.company_id == "AAPL"
    assert result.dimension == Dimension.TALENT
    assert result.score == 72.5
    assert result.level_name == "Good"
    assert len(result.supporting_evidence) == 2
    assert result.evidence_strength == "moderate"
    assert len(result.gaps_identified) == 1
    assert "thin" in result.gaps_identified[0]


@pytest.mark.asyncio
async def test_justification_generator_llm_failure_fallback():
    """Generator returns a graceful fallback when LLM fails."""
    mock_router = AsyncMock()
    mock_router.complete.side_effect = RuntimeError("LLM unavailable")

    gen = JustificationGenerator(llm_router=mock_router)
    result = await gen.generate(
        company_id="AAPL",
        dimension=Dimension.CULTURE,
        score=45.0,
        evidence=[],
    )

    assert isinstance(result, ScoreJustification)
    assert "Manual review required" in result.generated_summary
    assert result.evidence_strength == "weak"


@pytest.mark.asyncio
async def test_justification_generator_all_dimensions():
    """Generator can be called for all 7 dimensions without error."""
    mock_router = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Strong signals. Gap: governance."
    mock_router.complete.return_value = mock_response

    gen = JustificationGenerator(llm_router=mock_router)

    for dim in Dimension:
        result = await gen.generate(
            company_id="TEST",
            dimension=dim,
            score=55.0,
            evidence=[_make_doc()],
        )
        assert result.dimension == dim


# ---------------------------------------------------------------------------
# Unit tests — ICPrepWorkflow (mocked retriever + generator + LLM)
# ---------------------------------------------------------------------------

def _mock_workflow() -> tuple[ICPrepWorkflow, AsyncMock, AsyncMock, AsyncMock]:
    """Build an ICPrepWorkflow with all dependencies mocked."""
    mock_retriever = AsyncMock()
    mock_retriever.retrieve.return_value = [_make_doc("d1"), _make_doc("d2")]

    mock_gen = AsyncMock()
    mock_gen.generate = AsyncMock(side_effect=lambda **kw: _make_justification(
        dimension=kw["dimension"], score=kw["score"]
    ))

    mock_router = AsyncMock()
    mock_llm_response = MagicMock()
    mock_llm_response.choices[0].message.content = (
        '{"executive_summary": "AAPL is a strong AI candidate.", '
        '"key_strengths": ["Talent", "Stack", "Data"], '
        '"key_gaps": ["Governance", "Culture", "Leadership"], '
        '"risk_factors": ["Risk A", "Risk B", "Risk C"], '
        '"recommendation": "Buy — strong AI maturity signals."}'
    )
    mock_router.complete.return_value = mock_llm_response

    workflow = ICPrepWorkflow(
        retriever=mock_retriever,
        justification_generator=mock_gen,
        llm_router=mock_router,
    )
    return workflow, mock_retriever, mock_gen, mock_router


@pytest.mark.asyncio
async def test_ic_workflow_generates_all_dimensions():
    """Workflow produces justifications for all 7 dimensions."""
    workflow, _, mock_gen, _ = _mock_workflow()

    with patch("app.services.workflows.ic_prep.db") as mock_db:
        mock_db.fetch_company_by_ticker = AsyncMock(return_value={
            "id": "uuid-123",
            "name": "Apple Inc.",
            "sector": "technology",
            "sub_sector": "Consumer Electronics",
            "market_cap_percentile": 0.95,
            "revenue_millions": 394000.0,
            "employee_count": 160000,
            "fiscal_year_end": "09/30",
        })
        mock_db.fetch_all = AsyncMock(return_value=[])
        mock_db.fetch_dimension_scores = AsyncMock(return_value=[])

        package = await workflow.generate_meeting_package("AAPL", top_k=5)

    assert isinstance(package, ICMeetingPackage)
    assert len(package.dimension_justifications) == 7
    assert all(dim in package.dimension_justifications for dim in Dimension)


@pytest.mark.asyncio
async def test_ic_workflow_assessment_scores():
    """OrgAIR and V^R scores are computed and within valid ranges."""
    workflow, _, _, _ = _mock_workflow()

    with patch("app.services.workflows.ic_prep.db") as mock_db:
        mock_db.fetch_company_by_ticker = AsyncMock(return_value=None)
        mock_db.fetch_all = AsyncMock(return_value=[])
        mock_db.fetch_dimension_scores = AsyncMock(return_value=[])

        package = await workflow.generate_meeting_package("TEST", top_k=3)

    assert 0.0 <= package.assessment.vr_score <= 100.0
    assert 0.0 <= package.assessment.hr_score <= 100.0
    assert 0.0 <= package.assessment.synergy_score <= 100.0
    assert 0.0 <= package.assessment.org_air_score <= 100.0


@pytest.mark.asyncio
async def test_ic_workflow_raises_on_no_evidence():
    """Workflow raises ValueError when the retriever returns nothing."""
    mock_retriever = AsyncMock()
    mock_retriever.retrieve.return_value = []

    mock_gen = AsyncMock()
    mock_router = AsyncMock()

    workflow = ICPrepWorkflow(
        retriever=mock_retriever,
        justification_generator=mock_gen,
        llm_router=mock_router,
    )

    with patch("app.services.workflows.ic_prep.db") as mock_db:
        mock_db.fetch_company_by_ticker = AsyncMock(return_value=None)
        mock_db.fetch_all = AsyncMock(return_value=[])
        mock_db.fetch_dimension_scores = AsyncMock(return_value=[])

        with pytest.raises(ValueError, match="No indexed data found"):
            await workflow.generate_meeting_package("EMPTY", top_k=5)


@pytest.mark.asyncio
async def test_ic_workflow_executive_memo_fallback():
    """Workflow gracefully handles LLM failure in executive synthesis."""
    mock_retriever = AsyncMock()
    mock_retriever.retrieve.return_value = [_make_doc()]

    mock_gen = AsyncMock()
    mock_gen.generate = AsyncMock(side_effect=lambda **kw: _make_justification(
        dimension=kw["dimension"], score=kw["score"]
    ))

    mock_router = AsyncMock()
    mock_router.complete.side_effect = RuntimeError("LLM down")

    workflow = ICPrepWorkflow(
        retriever=mock_retriever,
        justification_generator=mock_gen,
        llm_router=mock_router,
    )

    with patch("app.services.workflows.ic_prep.db") as mock_db:
        mock_db.fetch_company_by_ticker = AsyncMock(return_value=None)
        mock_db.fetch_all = AsyncMock(return_value=[])
        mock_db.fetch_dimension_scores = AsyncMock(return_value=[])

        package = await workflow.generate_meeting_package("FAIL", top_k=2)

    # Fallback recommendation is used
    assert "Hold" in package.recommendation
    assert len(package.key_strengths) == 3
    assert len(package.key_gaps) == 3


# ---------------------------------------------------------------------------
# Integration-style tests — /justify endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_justify_endpoint_health(client):
    """Health sub-endpoint returns 200."""
    res = await client.get("/api/v1/rag/justify/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "active"
    assert "ic_prep_workflow" in data["services"]


@pytest.mark.asyncio
async def test_justify_endpoint_returns_400_on_no_evidence(client):
    """
    /justify returns 400 when the ticker has no indexed evidence.
    Mocks the IC workflow to raise ValueError (simulating missing /ingest).
    """
    with patch(
        "app.routers.justify._ic_workflow.generate_meeting_package",
        new_callable=AsyncMock,
        side_effect=ValueError("No indexed data found for NOTREAL."),
    ):
        res = await client.post(
            "/api/v1/rag/justify",
            json={"ticker": "NOTREAL", "top_k": 5},
        )
    assert res.status_code == 400
    assert "No indexed data found" in res.json()["detail"]


@pytest.mark.asyncio
async def test_justify_endpoint_success(client):
    """
    /justify returns 200 with an ICMeetingPackage when workflow succeeds.
    """
    from app.models.rag import (
        Company, CompanyAssessment, DimensionScore, ScoreLevel, Sector,
    )
    from datetime import datetime, timezone

    mock_assessment = CompanyAssessment(
        company_id="AAPL",
        assessment_date="2026-03-07",
        vr_score=68.5,
        hr_score=72.0,
        synergy_score=70.2,
        org_air_score=69.4,
        confidence_interval=(64.0, 75.0),
        dimension_scores={
            dim: DimensionScore(
                dimension=dim,
                score=65.0,
                level=ScoreLevel.LEVEL_4,
                confidence_interval=(60.0, 70.0),
                evidence_count=3,
                last_updated=datetime.now(timezone.utc).isoformat(),
            )
            for dim in Dimension
        },
        talent_concentration=0.65,
        position_factor=0.98,
    )

    mock_package = ICMeetingPackage(
        company=Company(
            company_id="uuid-aapl",
            ticker="AAPL",
            name="Apple Inc.",
            sector=Sector.TECHNOLOGY,
            sub_sector="Consumer Electronics",
            market_cap_percentile=0.95,
            revenue_millions=394000.0,
            employee_count=160000,
            fiscal_year_end="09/30",
        ),
        assessment=mock_assessment,
        dimension_justifications={
            dim: _make_justification(dim, 65.0) for dim in Dimension
        },
        executive_summary="Apple Inc. is a top-tier AI candidate.",
        key_strengths=["Talent", "Technology Stack", "Data Infrastructure"],
        key_gaps=["AI Governance", "Culture", "Leadership"],
        risk_factors=["Regulatory risk", "Talent retention", "Competition"],
        recommendation="Buy — exceptional AI maturity across key dimensions.",
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_evidence_count=21,
        avg_evidence_strength="strong",
    )

    with patch(
        "app.routers.justify._ic_workflow.generate_meeting_package",
        new_callable=AsyncMock,
        return_value=mock_package,
    ):
        res = await client.post(
            "/api/v1/rag/justify",
            json={"ticker": "AAPL", "top_k": 5},
        )

    assert res.status_code == 200
    data = res.json()
    assert data["company"]["ticker"] == "AAPL"
    assert "dimension_justifications" in data
    assert len(data["dimension_justifications"]) == 7
    assert data["assessment"]["org_air_score"] == 69.4
    assert "Buy" in data["recommendation"]


@pytest.mark.asyncio
async def test_justify_endpoint_validates_top_k(client):
    """top_k must be between 1 and 20; out-of-range values return 422."""
    res = await client.post(
        "/api/v1/rag/justify",
        json={"ticker": "AAPL", "top_k": 0},
    )
    assert res.status_code == 422

    res = await client.post(
        "/api/v1/rag/justify",
        json={"ticker": "AAPL", "top_k": 21},
    )
    assert res.status_code == 422
