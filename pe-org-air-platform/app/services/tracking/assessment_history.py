"""Assessment History Tracking — Stores score history for trend analysis."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from decimal import Decimal
import structlog

from app.services.integration.cs1_client import CS1Client
from app.services.integration.cs3_client import CS3Client

logger = structlog.get_logger()


@dataclass
class AssessmentSnapshot:
    """Single point-in-time assessment."""
    company_id: str
    timestamp: datetime
    org_air: Decimal
    vr_score: Decimal
    hr_score: Decimal
    synergy_score: Decimal
    dimension_scores: Dict[str, Decimal]
    confidence_interval: tuple
    evidence_count: int
    assessor_id: str
    assessment_type: str  # "screening", "limited", "full"


@dataclass
class AssessmentTrend:
    """Trend analysis for a company."""
    company_id: str
    current_org_air: float
    entry_org_air: float
    delta_since_entry: float
    delta_30d: Optional[float]
    delta_90d: Optional[float]
    trend_direction: str  # "improving", "stable", "declining"
    snapshot_count: int


class AssessmentHistoryService:
    """
    Tracks assessment history using CS1 for storage, CS3 for calculations.
    """

    def __init__(self, cs1_client: CS1Client, cs3_client: CS3Client):
        self.cs1 = cs1_client
        self.cs3 = cs3_client
        self._cache: Dict[str, List[AssessmentSnapshot]] = {}

    async def record_assessment(
        self,
        company_id: str,
        assessor_id: str,
        assessment_type: str = "full",
    ) -> AssessmentSnapshot:
        """
        Record current assessment as a snapshot.

        Flow:
        1. Call CS3 get_assessment() for current scores
        2. Create snapshot with timestamp
        3. Store in history (via CS1/Snowflake)
        4. Return snapshot
        """
        # Get current assessment from scoring client
        assessment = await self.cs3.list_assessments(company_id=company_id)
        items = assessment.get("items", [])

        if not items:
            # No assessment found — return a default snapshot
            snapshot = AssessmentSnapshot(
                company_id=company_id,
                timestamp=datetime.utcnow(),
                org_air=Decimal("0"),
                vr_score=Decimal("0"),
                hr_score=Decimal("0"),
                synergy_score=Decimal("0"),
                dimension_scores={},
                confidence_interval=(0.0, 0.0),
                evidence_count=0,
                assessor_id=assessor_id,
                assessment_type=assessment_type,
            )
            # Update cache
            if company_id not in self._cache:
                self._cache[company_id] = []
            self._cache[company_id].append(snapshot)

            logger.info("assessment_recorded",
                        company_id=company_id,
                        org_air=float(snapshot.org_air))
            return snapshot

        latest = items[0]

        snapshot = AssessmentSnapshot(
            company_id=company_id,
            timestamp=datetime.utcnow(),
            org_air=Decimal(str(latest.get("org_air_score", 0))),
            vr_score=Decimal(str(latest.get("v_r_score", 0))),
            hr_score=Decimal(str(latest.get("h_r_score", 0))),
            synergy_score=Decimal(str(latest.get("synergy_score", 0))),
            dimension_scores={
                d.get("dimension", d.get("name", "unknown")): Decimal(str(d.get("score", 0)))
                for d in latest.get("dimension_scores", [])
                if isinstance(d, dict)
            },
            confidence_interval=(
                latest.get("confidence_interval", [0, 0])[0] if isinstance(latest.get("confidence_interval"), (list, tuple)) and len(latest.get("confidence_interval", [])) >= 2 else 0.0,
                latest.get("confidence_interval", [0, 0])[1] if isinstance(latest.get("confidence_interval"), (list, tuple)) and len(latest.get("confidence_interval", [])) >= 2 else 0.0,
            ),
            evidence_count=latest.get("evidence_count", 0),
            assessor_id=assessor_id,
            assessment_type=assessment_type,
        )

        # Store via CS1/Snowflake
        await self._store_snapshot(snapshot)

        # Update cache
        if company_id not in self._cache:
            self._cache[company_id] = []
        self._cache[company_id].append(snapshot)

        logger.info("assessment_recorded",
                    company_id=company_id,
                    org_air=float(snapshot.org_air))
        return snapshot

    async def _store_snapshot(self, snapshot: AssessmentSnapshot) -> None:
        """Store snapshot in Snowflake via CS1."""
        # In production: INSERT INTO assessment_history ...
        pass

    async def get_history(
        self,
        company_id: str,
        days: int = 365,
    ) -> List[AssessmentSnapshot]:
        """Retrieve assessment history from CS1/Snowflake."""
        # Check cache first
        if company_id in self._cache:
            cutoff = datetime.utcnow() - timedelta(days=days)
            return [s for s in self._cache[company_id] if s.timestamp >= cutoff]

        # Query CS1/Snowflake
        # SELECT * FROM assessment_history WHERE company_id = ? AND timestamp >= ?
        return []

    async def calculate_trend(self, company_id: str, days: int = 365) -> AssessmentTrend:
        """Calculate trend metrics from history."""
        history = await self.get_history(company_id, days=days)

        if not history:
            # No history, get current assessment
            current = await self.cs3.list_assessments(company_id=company_id)
            items = current.get("items", [])
            if not items:
                return AssessmentTrend(
                    company_id=company_id,
                    current_org_air=0.0,
                    entry_org_air=0.0,
                    delta_since_entry=0.0,
                    delta_30d=None,
                    delta_90d=None,
                    trend_direction="stable",
                    snapshot_count=0,
                )
            latest = items[0]
            score = latest.get("org_air_score", 0.0)
            return AssessmentTrend(
                company_id=company_id,
                current_org_air=score,
                entry_org_air=score,
                delta_since_entry=0.0,
                delta_30d=None,
                delta_90d=None,
                trend_direction="stable",
                snapshot_count=0,
            )

        # Sort by timestamp
        history.sort(key=lambda s: s.timestamp)

        current = float(history[-1].org_air)
        entry = float(history[0].org_air)

        # Calculate deltas
        now = datetime.utcnow()
        delta_30d = None
        delta_90d = None

        for snapshot in reversed(history):
            age_days = (now - snapshot.timestamp).days
            if age_days >= 30 and delta_30d is None:
                delta_30d = current - float(snapshot.org_air)
            if age_days >= 90 and delta_90d is None:
                delta_90d = current - float(snapshot.org_air)
                break

        # Determine trend direction
        delta = current - entry
        if delta > 5:
            direction = "improving"
        elif delta < -5:
            direction = "declining"
        else:
            direction = "stable"

        return AssessmentTrend(
            company_id=company_id,
            current_org_air=current,
            entry_org_air=entry,
            delta_since_entry=round(delta, 1),
            delta_30d=round(delta_30d, 1) if delta_30d is not None else None,
            delta_90d=round(delta_90d, 1) if delta_90d is not None else None,
            trend_direction=direction,
            snapshot_count=len(history),
        )


# Factory function
def create_history_service(cs1: CS1Client, cs3: CS3Client) -> AssessmentHistoryService:
    return AssessmentHistoryService(cs1, cs3)
