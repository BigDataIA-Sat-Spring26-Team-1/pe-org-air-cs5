"""
CS2 Client — Signals & Evidence SDK.

Wraps ``/api/v1/signals`` and ``/api/v1/evidence`` REST endpoints so the
RAG engine can fetch raw intelligence data without importing backend internals.
"""

from typing import Any, Dict, List, Optional

from app.services.integration import BaseSDKClient


class CS2Client(BaseSDKClient):
    """Thin async wrapper around CS2 (Signals/Evidence) endpoints."""

    # -- Signal collection --------------------------------------------------

    async def get_signals(
        self,
        ticker: Optional[str] = None,
        company_name: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """``GET /api/v1/signals``"""
        return await self._get(
            "/api/v1/signals",
            ticker=ticker,
            company_name=company_name,
            category=category,
            limit=limit,
            offset=offset,
        )

    async def get_signal_summary(
        self,
        ticker: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """``GET /api/v1/signals/summary``"""
        return await self._get(
            "/api/v1/signals/summary",
            ticker=ticker,
            company_name=company_name,
        )

    async def get_signal_details(
        self,
        category: str,
        ticker: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """``GET /api/v1/signals/details/{category}``"""
        return await self._get(
            f"/api/v1/signals/details/{category}",
            ticker=ticker,
            company_name=company_name,
        )

    # -- Culture / Glassdoor ------------------------------------------------

    async def get_culture_scores(self, ticker: str) -> Dict[str, Any]:
        """``GET /api/v1/signals/culture/{ticker}``"""
        return await self._get(f"/api/v1/signals/culture/{ticker}")

    async def get_glassdoor_reviews(
        self,
        ticker: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """``GET /api/v1/signals/culture/reviews/{ticker}``"""
        return await self._get(
            f"/api/v1/signals/culture/reviews/{ticker}",
            limit=limit,
            offset=offset,
        )

    # -- Evidence -----------------------------------------------------------

    async def get_evidence(
        self,
        ticker: Optional[str] = None,
        company_name: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """``GET /api/v1/signals/evidence`` (evidence list on signals router)."""
        return await self._get(
            "/api/v1/signals/evidence",
            ticker=ticker,
            company_name=company_name,
            category=category,
            limit=limit,
            offset=offset,
        )

    async def get_evidence_stats(self) -> Dict[str, Any]:
        """``GET /api/v1/evidence/stats``"""
        return await self._get("/api/v1/evidence/stats")
