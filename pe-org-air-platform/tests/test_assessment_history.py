"""
Tests for Assessment History Tracking — Task 9.4.

Mocks CS3Client.list_assessments to verify snapshot recording,
history retrieval, and trend calculation logic.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal

from app.services.tracking.assessment_history import (
    AssessmentHistoryService,
    AssessmentSnapshot,
    AssessmentTrend,
    create_history_service,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_cs_clients(assessment_items=None):
    """Create mock CS1 and CS3 clients."""
    cs1 = MagicMock()
    cs3 = MagicMock()
    cs3.list_assessments = AsyncMock(return_value={
        "items": assessment_items or [],
        "total": len(assessment_items or []),
        "page": 1,
    })
    return cs1, cs3


SAMPLE_ASSESSMENT = {
    "id": "a-001",
    "company_id": "c-001",
    "org_air_score": 72.5,
    "v_r_score": 68.0,
    "h_r_score": 75.0,
    "synergy_score": 1.1,
    "dimension_scores": [
        {"dimension": "talent", "score": 70.0},
        {"dimension": "leadership", "score": 80.0},
    ],
    "confidence_interval": [65.0, 80.0],
    "evidence_count": 42,
}


# ---------------------------------------------------------------------------
# record_assessment
# ---------------------------------------------------------------------------

class TestRecordAssessment:

    @pytest.mark.asyncio
    async def test_record_creates_snapshot(self):
        cs1, cs3 = _make_cs_clients([SAMPLE_ASSESSMENT])
        svc = AssessmentHistoryService(cs1, cs3)

        snap = await svc.record_assessment("c-001", "analyst-1", "full")

        assert snap.company_id == "c-001"
        assert snap.org_air == Decimal("72.5")
        assert snap.vr_score == Decimal("68.0")
        assert snap.hr_score == Decimal("75.0")
        assert snap.synergy_score == Decimal("1.1")
        assert snap.assessor_id == "analyst-1"
        assert snap.assessment_type == "full"
        assert snap.evidence_count == 42
        assert snap.confidence_interval == (65.0, 80.0)
        assert "talent" in snap.dimension_scores

    @pytest.mark.asyncio
    async def test_record_caches_snapshot(self):
        cs1, cs3 = _make_cs_clients([SAMPLE_ASSESSMENT])
        svc = AssessmentHistoryService(cs1, cs3)

        await svc.record_assessment("c-001", "analyst-1")
        assert len(svc._cache["c-001"]) == 1

        await svc.record_assessment("c-001", "analyst-2")
        assert len(svc._cache["c-001"]) == 2

    @pytest.mark.asyncio
    async def test_record_empty_assessment(self):
        cs1, cs3 = _make_cs_clients([])
        svc = AssessmentHistoryService(cs1, cs3)

        snap = await svc.record_assessment("c-empty", "analyst-1")
        assert snap.org_air == Decimal("0")
        assert snap.evidence_count == 0


# ---------------------------------------------------------------------------
# get_history
# ---------------------------------------------------------------------------

class TestGetHistory:

    @pytest.mark.asyncio
    async def test_returns_cached_snapshots(self):
        cs1, cs3 = _make_cs_clients([SAMPLE_ASSESSMENT])
        svc = AssessmentHistoryService(cs1, cs3)

        await svc.record_assessment("c-001", "analyst-1")
        history = await svc.get_history("c-001")

        assert len(history) == 1
        assert history[0].company_id == "c-001"

    @pytest.mark.asyncio
    async def test_filters_by_date_range(self):
        cs1, cs3 = _make_cs_clients([SAMPLE_ASSESSMENT])
        svc = AssessmentHistoryService(cs1, cs3)

        # Add an old snapshot manually
        old_snap = AssessmentSnapshot(
            company_id="c-001",
            timestamp=datetime.utcnow() - timedelta(days=400),
            org_air=Decimal("50.0"),
            vr_score=Decimal("45.0"),
            hr_score=Decimal("55.0"),
            synergy_score=Decimal("1.0"),
            dimension_scores={},
            confidence_interval=(40.0, 60.0),
            evidence_count=10,
            assessor_id="old-analyst",
            assessment_type="screening",
        )
        svc._cache["c-001"] = [old_snap]

        await svc.record_assessment("c-001", "analyst-1")

        # Default 365 days should exclude the old snapshot
        history = await svc.get_history("c-001", days=365)
        assert len(history) == 1
        assert history[0].assessor_id == "analyst-1"

    @pytest.mark.asyncio
    async def test_empty_history_for_unknown_company(self):
        cs1, cs3 = _make_cs_clients([])
        svc = AssessmentHistoryService(cs1, cs3)

        history = await svc.get_history("unknown-company")
        assert history == []


# ---------------------------------------------------------------------------
# calculate_trend
# ---------------------------------------------------------------------------

class TestCalculateTrend:

    @pytest.mark.asyncio
    async def test_no_history_returns_stable(self):
        cs1, cs3 = _make_cs_clients([])
        svc = AssessmentHistoryService(cs1, cs3)

        trend = await svc.calculate_trend("c-empty")

        assert trend.trend_direction == "stable"
        assert trend.snapshot_count == 0
        assert trend.delta_since_entry == 0.0
        assert trend.delta_30d is None
        assert trend.delta_90d is None

    @pytest.mark.asyncio
    async def test_improving_trend(self):
        cs1, cs3 = _make_cs_clients([SAMPLE_ASSESSMENT])
        svc = AssessmentHistoryService(cs1, cs3)

        # Seed with a low entry snapshot
        entry_snap = AssessmentSnapshot(
            company_id="c-001",
            timestamp=datetime.utcnow() - timedelta(days=100),
            org_air=Decimal("50.0"),
            vr_score=Decimal("45.0"),
            hr_score=Decimal("55.0"),
            synergy_score=Decimal("1.0"),
            dimension_scores={},
            confidence_interval=(40.0, 60.0),
            evidence_count=10,
            assessor_id="analyst-0",
            assessment_type="screening",
        )
        # Current snapshot (higher score)
        current_snap = AssessmentSnapshot(
            company_id="c-001",
            timestamp=datetime.utcnow(),
            org_air=Decimal("72.5"),
            vr_score=Decimal("68.0"),
            hr_score=Decimal("75.0"),
            synergy_score=Decimal("1.1"),
            dimension_scores={},
            confidence_interval=(65.0, 80.0),
            evidence_count=42,
            assessor_id="analyst-1",
            assessment_type="full",
        )
        svc._cache["c-001"] = [entry_snap, current_snap]

        trend = await svc.calculate_trend("c-001")

        assert trend.trend_direction == "improving"
        assert trend.delta_since_entry == 22.5
        assert trend.snapshot_count == 2

    @pytest.mark.asyncio
    async def test_declining_trend(self):
        cs1, cs3 = _make_cs_clients([SAMPLE_ASSESSMENT])
        svc = AssessmentHistoryService(cs1, cs3)

        entry_snap = AssessmentSnapshot(
            company_id="c-001",
            timestamp=datetime.utcnow() - timedelta(days=60),
            org_air=Decimal("85.0"),
            vr_score=Decimal("80.0"),
            hr_score=Decimal("90.0"),
            synergy_score=Decimal("1.2"),
            dimension_scores={},
            confidence_interval=(80.0, 90.0),
            evidence_count=50,
            assessor_id="analyst-0",
            assessment_type="full",
        )
        current_snap = AssessmentSnapshot(
            company_id="c-001",
            timestamp=datetime.utcnow(),
            org_air=Decimal("60.0"),
            vr_score=Decimal("55.0"),
            hr_score=Decimal("65.0"),
            synergy_score=Decimal("1.0"),
            dimension_scores={},
            confidence_interval=(55.0, 65.0),
            evidence_count=30,
            assessor_id="analyst-1",
            assessment_type="full",
        )
        svc._cache["c-001"] = [entry_snap, current_snap]

        trend = await svc.calculate_trend("c-001")

        assert trend.trend_direction == "declining"
        assert trend.delta_since_entry == -25.0

    @pytest.mark.asyncio
    async def test_stable_trend(self):
        cs1, cs3 = _make_cs_clients([SAMPLE_ASSESSMENT])
        svc = AssessmentHistoryService(cs1, cs3)

        snap1 = AssessmentSnapshot(
            company_id="c-001",
            timestamp=datetime.utcnow() - timedelta(days=30),
            org_air=Decimal("70.0"),
            vr_score=Decimal("65.0"),
            hr_score=Decimal("75.0"),
            synergy_score=Decimal("1.0"),
            dimension_scores={},
            confidence_interval=(65.0, 75.0),
            evidence_count=20,
            assessor_id="analyst-0",
            assessment_type="full",
        )
        snap2 = AssessmentSnapshot(
            company_id="c-001",
            timestamp=datetime.utcnow(),
            org_air=Decimal("72.0"),
            vr_score=Decimal("67.0"),
            hr_score=Decimal("77.0"),
            synergy_score=Decimal("1.0"),
            dimension_scores={},
            confidence_interval=(67.0, 77.0),
            evidence_count=25,
            assessor_id="analyst-1",
            assessment_type="full",
        )
        svc._cache["c-001"] = [snap1, snap2]

        trend = await svc.calculate_trend("c-001")

        assert trend.trend_direction == "stable"
        assert -5 <= trend.delta_since_entry <= 5


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------

class TestFactory:

    def test_create_history_service(self):
        cs1 = MagicMock()
        cs3 = MagicMock()
        svc = create_history_service(cs1, cs3)

        assert isinstance(svc, AssessmentHistoryService)
        assert svc.cs1 is cs1
        assert svc.cs3 is cs3
