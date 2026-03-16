"""
CS3 Client — Assessments & Metrics SDK.

Wraps ``/api/v1/assessments`` and ``/api/v1/metrics`` REST endpoints so the
RAG engine can fetch scoring data and leaderboard reports without
importing backend internals.
"""

from typing import Any, Dict, List, Optional

from app.services.integration import BaseSDKClient


class CS3Client(BaseSDKClient):
    """Thin async wrapper around CS3 (Assessment/Scoring/Metrics) endpoints."""

    # -- Assessments --------------------------------------------------------

    async def list_assessments(
        self,
        page: int = 1,
        page_size: int = 100,
        company_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """``GET /api/v1/assessments``"""
        return await self._get(
            "/api/v1/assessments",
            page=page,
            page_size=page_size,
            company_id=company_id,
        )

    async def get_assessment(self, assessment_id: str) -> Dict[str, Any]:
        """``GET /api/v1/assessments/{assessment_id}``"""
        return await self._get(f"/api/v1/assessments/{assessment_id}")

    async def get_dimension_score(self, ticker: str, dimension: Any) -> Any:
        """``GET /api/v1/assessments/latest/{ticker}/score/{dimension}``"""
        dim_val = dimension.value if hasattr(dimension, 'value') else str(dimension)
        data = await self._get(f"/api/v1/assessments/latest/{ticker}/score/{dim_val}")
        
        # Map to the DimensionScore model used by the RAG pipeline
        # Using a DotDict-like wrapper or the actual model if imported
        from app.models.rag import DimensionScore, ScoreLevel, Dimension
        
        # Derive level and CI if missing
        score = data.get('score', 0.0)
        evidence_count = data.get('evidence_count', 0)
        
        # Simple level mapping
        if score >= 80: level = ScoreLevel.LEVEL_5
        elif score >= 60: level = ScoreLevel.LEVEL_4
        elif score >= 40: level = ScoreLevel.LEVEL_3
        elif score >= 20: level = ScoreLevel.LEVEL_2
        else: level = ScoreLevel.LEVEL_1
        
        # Simple CI calculation (±10 as placeholder if evidence count is low)
        margin = 15.0 / (max(1, evidence_count) ** 0.5)
        ci = (max(0.0, score - margin), min(100.0, score + margin))
        
        return DimensionScore(
            dimension=Dimension(dim_val),
            score=score,
            level=level,
            confidence_interval=ci,
            evidence_count=evidence_count,
            last_updated=data.get('created_at', "2024-01-01T00:00:00Z")
        )

    async def get_dimension_scores(self, assessment_id: str) -> List[Dict[str, Any]]:
        """``GET /api/v1/assessments/{assessment_id}/scores``"""
        return await self._get(f"/api/v1/assessments/{assessment_id}/scores")

    # -- Metrics ------------------------------------------------------------

    async def get_readiness_report(self) -> Dict[str, Any]:
        """``GET /api/v1/metrics/readiness-report``"""
        return await self._get("/api/v1/metrics/readiness-report")

    async def get_company_stats(
        self, company_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """``GET /api/v1/metrics/company-stats``"""
        return await self._get(
            "/api/v1/metrics/company-stats",
            company_id=company_id,
        )

    async def get_industry_distribution(self) -> List[Dict[str, Any]]:
        """``GET /api/v1/metrics/industry-distribution``"""
        return await self._get("/api/v1/metrics/industry-distribution")

    async def get_signal_distribution(
        self, company_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """``GET /api/v1/metrics/signal-distribution``"""
        return await self._get(
            "/api/v1/metrics/signal-distribution",
            company_id=company_id,
        )

    async def get_global_summary(self) -> Dict[str, Any]:
        """``GET /api/v1/metrics/summary``"""
        return await self._get("/api/v1/metrics/summary")
