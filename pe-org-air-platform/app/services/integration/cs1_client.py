"""
CS1 Client — Company & Industry metadata SDK.

Wraps the ``/api/v1/companies`` and ``/api/v1/industries`` REST endpoints
so the RAG engine can fetch company metadata without importing backend internals.
"""

from typing import Any, Dict, List, Optional

from app.services.integration import BaseSDKClient


class CS1Client(BaseSDKClient):
    """Thin async wrapper around CS1 (Company/Industry) endpoints."""

    # -- Companies ----------------------------------------------------------

    async def get_company(self, company_id: str) -> Dict[str, Any]:
        """``GET /api/v1/companies/{company_id}``"""
        return await self._get(f"/api/v1/companies/{company_id}")

    async def list_companies(
        self,
        page: int = 1,
        page_size: int = 100,
        industry_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        ``GET /api/v1/companies``

        Returns the full paginated response (items + meta).
        """
        return await self._get(
            "/api/v1/companies",
            page=page,
            page_size=page_size,
            industry_id=industry_id,
        )

    async def get_company_signals(
        self,
        company_id: str,
        category: str,
    ) -> List[Dict[str, Any]]:
        """``GET /api/v1/companies/{company_id}/signals/{category}``"""
        return await self._get(
            f"/api/v1/companies/{company_id}/signals/{category}",
        )

    async def get_company_evidence(self, company_id: str) -> List[Dict[str, Any]]:
        """``GET /api/v1/companies/{company_id}/evidence``"""
        return await self._get(f"/api/v1/companies/{company_id}/evidence")

    # -- Industries ---------------------------------------------------------

    async def list_industries(self) -> List[Dict[str, Any]]:
        """``GET /api/v1/industries``"""
        return await self._get("/api/v1/industries")
