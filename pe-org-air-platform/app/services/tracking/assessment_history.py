"""Assessment History Tracking — stores score snapshots and computes trends."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from decimal import Decimal
import uuid
import structlog

from app.services.integration.cs1_client import CS1Client
from app.services.integration.cs2_client import CS2Client
from app.services.integration.cs3_client import CS3Client

logger = structlog.get_logger()

# Resolved lazily to avoid circular imports at module load time.
_db = None


def _get_db():
    global _db
    if _db is None:
        from app.services.snowflake import db as _snowflake_db
        _db = _snowflake_db
    return _db


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AssessmentSnapshot:
    """Point-in-time assessment record."""
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
    """Trend summary derived from a series of snapshots."""
    company_id: str
    current_org_air: float
    entry_org_air: float
    delta_since_entry: float
    delta_30d: Optional[float]
    delta_90d: Optional[float]
    trend_direction: str  # "improving", "stable", "declining"
    snapshot_count: int


class AssessmentHistoryService:
    """Pulls scores from CS3 and persists snapshots to Snowflake."""

    def __init__(self, cs1_client: CS1Client, cs3_client: CS3Client, cs2_client: Optional[CS2Client] = None):
        self.cs1 = cs1_client
        self.cs2 = cs2_client
        self.cs3 = cs3_client
        self._cache: Dict[str, List[AssessmentSnapshot]] = {}

    async def record_assessment(
        self,
        company_id: str,
        assessor_id: str,
        assessment_type: str = "full",
    ) -> AssessmentSnapshot:
        """
        Grab the latest CS3 assessment for a company, wrap it in a snapshot,
        persist it, and return it.
        """
        assessment = await self.cs3.list_assessments(company_id=company_id)
        items = assessment.get("items", [])

        if not items:
            snapshot = AssessmentSnapshot(
                company_id=company_id,
                timestamp=_now_utc(),
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
            self._cache.setdefault(company_id, []).append(snapshot)
            logger.info("assessment_recorded_empty", company_id=company_id)
            return snapshot

        latest = items[0]
        ci_lower = latest.get("confidence_lower")
        ci_upper = latest.get("confidence_upper")
        if ci_lower is not None and ci_upper is not None:
            ci = (float(ci_lower), float(ci_upper))
        else:
            ci = (0.0, 0.0)

        snapshot = AssessmentSnapshot(
            company_id=company_id,
            timestamp=_now_utc(),
            org_air=Decimal(str(latest.get("org_air_score") or 0)),
            vr_score=Decimal(str(latest.get("v_r_score") or 0)),
            hr_score=Decimal(str(latest.get("h_r_score") or 0)),
            synergy_score=Decimal(str(latest.get("synergy_score") or 0)),
            dimension_scores={
                d.get("dimension", d.get("name", "unknown")): Decimal(str(d.get("score", 0)))
                for d in latest.get("dimension_scores", [])
                if isinstance(d, dict)
            },
            confidence_interval=ci,
            evidence_count=latest.get("evidence_count", 0),
            assessor_id=assessor_id,
            assessment_type=assessment_type,
        )

        await self._store_snapshot(snapshot)
        self._cache.setdefault(company_id, []).append(snapshot)

        logger.info("assessment_recorded",
                    company_id=company_id,
                    org_air=float(snapshot.org_air))
        return snapshot

    async def _store_snapshot(self, snapshot: AssessmentSnapshot) -> None:
        """
        Write the snapshot to the assessments table in Snowflake.

        Each call inserts a new row, so the table doubles as a history log.
        Failures are logged and swallowed so a DB hiccup never kills the
        agentic workflow.
        """
        try:
            db = _get_db()
            record = {
                "id": uuid.uuid4(),
                "company_id": snapshot.company_id,
                "assessment_type": snapshot.assessment_type,
                "assessment_date": snapshot.timestamp.date(),
                "status": "completed",
                "primary_assessor": snapshot.assessor_id,
                "secondary_assessor": None,
                "v_r_score": float(snapshot.vr_score),
                "h_r_score": float(snapshot.hr_score),
                "synergy_score": float(snapshot.synergy_score),
                "org_air_score": float(snapshot.org_air),
                "confidence_score": None,
                "confidence_lower": snapshot.confidence_interval[0],
                "confidence_upper": snapshot.confidence_interval[1],
            }
            await db.create_assessment(record)
            logger.info("snapshot_persisted",
                        company_id=snapshot.company_id,
                        org_air=float(snapshot.org_air))
        except Exception as exc:
            logger.warning("snapshot_persist_failed",
                           company_id=snapshot.company_id,
                           error=str(exc))

    async def get_history(
        self,
        company_id: str,
        days: int = 365,
    ) -> List[AssessmentSnapshot]:
        """
        Return snapshots for the given window. Hits the in-memory cache first;
        falls back to querying CS3 / Snowflake if the cache is cold.
        """
        if company_id in self._cache:
            cutoff = _now_utc() - timedelta(days=days)
            return [s for s in self._cache[company_id] if s.timestamp >= cutoff]

        try:
            data = await self.cs3.list_assessments(
                company_id=company_id,
                page_size=100,
            )
            items = data.get("items", [])
            cutoff = _now_utc() - timedelta(days=days)
            snapshots: List[AssessmentSnapshot] = []
            for item in items:
                raw_ts = item.get("created_at") or item.get("assessment_date")
                try:
                    ts = datetime.fromisoformat(str(raw_ts)).replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    ts = _now_utc()
                if ts < cutoff:
                    continue
                ci_lower = item.get("confidence_lower")
                ci_upper = item.get("confidence_upper")
                if ci_lower is not None and ci_upper is not None:
                    ci = (float(ci_lower), float(ci_upper))
                else:
                    ci = (0.0, 0.0)
                snapshots.append(AssessmentSnapshot(
                    company_id=company_id,
                    timestamp=ts,
                    org_air=Decimal(str(item.get("org_air_score") or 0)),
                    vr_score=Decimal(str(item.get("v_r_score") or 0)),
                    hr_score=Decimal(str(item.get("h_r_score") or 0)),
                    synergy_score=Decimal(str(item.get("synergy_score") or 0)),
                    dimension_scores={},
                    confidence_interval=ci,
                    evidence_count=0,
                    assessor_id=item.get("primary_assessor", "system"),
                    assessment_type=item.get("assessment_type", "full"),
                ))
            # Fetch total evidence count via COUNT(*) — no row data transferred.
            # SIGNAL_EVIDENCE has no per-date count; current total is the best proxy.
            actual_evidence_count = 0
            if self.cs2:
                try:
                    actual_evidence_count = await self.cs2.count_evidence(ticker=company_id)
                except Exception:
                    pass
            for snap in snapshots:
                snap.evidence_count = actual_evidence_count

            self._cache[company_id] = snapshots
            return snapshots
        except Exception as exc:
            logger.warning("get_history_failed", company_id=company_id, error=str(exc))
            return []

    async def calculate_trend(self, company_id: str, days: int = 365) -> AssessmentTrend:
        """Compute trend direction and deltas from available snapshot history."""
        history = await self.get_history(company_id, days=days)

        if not history:
            current_data = await self.cs3.list_assessments(company_id=company_id)
            items = current_data.get("items", [])
            score = float(items[0].get("org_air_score", 0.0)) if items else 0.0
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

        history.sort(key=lambda s: s.timestamp)

        current = float(history[-1].org_air)
        entry = float(history[0].org_air)

        now = _now_utc()
        delta_30d: Optional[float] = None
        delta_90d: Optional[float] = None

        for snap in reversed(history):
            age_days = (now - snap.timestamp).days
            if age_days >= 30 and delta_30d is None:
                delta_30d = current - float(snap.org_air)
            if age_days >= 90 and delta_90d is None:
                delta_90d = current - float(snap.org_air)
                break

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


def create_history_service(cs1: CS1Client, cs3: CS3Client, cs2: Optional[CS2Client] = None) -> AssessmentHistoryService:
    return AssessmentHistoryService(cs1, cs3, cs2_client=cs2)
