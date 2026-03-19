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
        payload = {"company_id": company_id}
        # To call justify properly, could be POST /api/v1/justify
        # Or you can do it specifically via RAG if needed.
        data = await self._post("/api/v1/justify", json=payload)
        # Parse output to return the ScoreJustification matching the dimension
        # Normally this returns an ICMeetingPackage.
        # So we'll fetch just what we need.
        justifications = data.get("dimension_justifications", {})
        dim_str = dimension.value if hasattr(dimension, 'value') else str(dimension)
        found = justifications.get(dim_str, {})
        
        # Simple instantiation logic for testing
        return ScoreJustification(
            dimension=dimension,
            score=found.get("score", 70.0),
            level=found.get("level", 3),
            level_name=found.get("level_name", "Adequate"),
            evidence_strength=found.get("evidence_strength", "moderate"),
            rubric_criteria=found.get("rubric_criteria", "Standard criteria hit"),
            supporting_evidence=found.get("supporting_evidence", []),
            gaps_identified=found.get("gaps_identified", [])
        )
