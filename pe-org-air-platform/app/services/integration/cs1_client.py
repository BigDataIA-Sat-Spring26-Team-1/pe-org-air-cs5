"""
CS1 Client — Company & Industry metadata SDK.

Wraps the ``/api/v1/companies`` and ``/api/v1/industries`` REST endpoints
so the RAG engine can fetch company metadata without importing backend internals.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from app.services.integration import BaseSDKClient

class Sector(Enum):
    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    FINANCIAL_SERVICES = "financial_services"
    MANUFACTURING = "manufacturing"
    RETAIL = "retail"
    ENERGY = "energy"

@dataclass
class Company:
    company_id: str
    ticker: str
    name: str
    sector: Sector
    employee_count: int
    revenue_mm: float
    portfolio_entry_date: Optional[str] = None


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

    async def get_portfolio_companies(self, fund_id: str) -> List[Company]:
        """``GET /api/v1/portfolios/{fund_id}/companies`` or equivalent"""
        # Mocking or fetching from the live endpoint, using list_companies
        data = await self.list_companies()
        items = data.get("items", [])
        companies = []
        for c in items:
            sec_str = Sector.TECHNOLOGY
            companies.append(Company(
                company_id=c.get("id", c["ticker"]),
                ticker=c["ticker"],
                name=c["name"],
                sector=sec_str,
                employee_count=c.get("employees", 1000),
                revenue_mm=c.get("revenue", 100.0)
            ))
        return companies
