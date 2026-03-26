"""
CS4 Client — RAG & Justification SDK.
"""
from typing import Any, Dict, List, Optional
from app.services.integration import BaseSDKClient
from app.models.rag import ScoreJustification, Dimension

class CS4Client(BaseSDKClient):
    """Thin async wrapper around CS4 RAG endpoints."""
    def __init__(self, base_url: str = "http://api:8000"):
        super().__init__(base_url=base_url)

    async def generate_justification(
        self, company_id: str, dimension: Dimension
    ) -> ScoreJustification:
        """``POST /api/v1/justify``"""
        # /api/v1/rag/justify expects {"ticker": ..., "top_k": ...}
        # company_id is used as ticker throughout this codebase (e.g. "NVDA")
        payload = {"ticker": company_id, "top_k": 5}
        data = await self._post("/api/v1/rag/justify", payload)
        # Parse output to return the ScoreJustification matching the dimension
        # Normally this returns an ICMeetingPackage.
        # So we'll fetch just what we need.
        justifications = data.get("dimension_justifications", {})
        dim_str = dimension.value if hasattr(dimension, 'value') else str(dimension)
        found = justifications.get(dim_str, {})
        
        return ScoreJustification(
            company_id=company_id,
            dimension=dimension,
            score=found.get("score", 0.0),
            level=found.get("level", 1),
            level_name=found.get("level_name", "Nascent"),
            confidence_interval=tuple(found.get("confidence_interval", [0.0, 100.0])[:2]),
            rubric_criteria=found.get("rubric_criteria", ""),
            rubric_keywords=found.get("rubric_keywords", []),
            supporting_evidence=found.get("supporting_evidence", []),
            gaps_identified=found.get("gaps_identified", []),
            generated_summary=found.get("generated_summary", ""),
            evidence_strength=found.get("evidence_strength", "moderate"),
        )
