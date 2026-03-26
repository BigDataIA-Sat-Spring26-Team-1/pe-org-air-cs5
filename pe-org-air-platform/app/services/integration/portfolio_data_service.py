"""
Unified Portfolio Data Service.
"""
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import structlog

from app.services.integration.cs1_client import CS1Client, Company, Sector
from app.services.integration.cs2_client import CS2Client
from app.services.integration.cs3_client import CS3Client
from app.services.integration.cs4_client import CS4Client

logger = structlog.get_logger()

@dataclass
class PortfolioCompanyView:
    """Complete view of a portfolio company from CS1-CS4."""
    company_id: str
    ticker: str
    name: str
    sector: str
    org_air: float
    vr_score: float
    hr_score: float
    synergy_score: float
    dimension_scores: Dict[str, float]
    confidence_interval: tuple
    entry_org_air: float
    delta_since_entry: float
    evidence_count: int

class PortfolioDataService:
    """Unified data service integrating CS1-CS4."""

    def __init__(
        self,
        cs1_url: str = "http://api:8000",
        cs2_url: str = "http://api:8000",
        cs3_url: str = "http://api:8000",
    ):
        # Initialize all CS clients at construction time
        self.cs1 = CS1Client(base_url=cs1_url)
        self.cs2 = CS2Client(base_url=cs2_url)
        self.cs3 = CS3Client(base_url=cs3_url)
        self.cs4 = CS4Client()
        logger.info("portfolio_data_service_initialized")

    async def get_portfolio_view(
        self,
        fund_id: str,
    ) -> List[PortfolioCompanyView]:
        """Load portfolio from CS1, scores from CS3, evidence from CS2."""
        # Fetch company profile from metadata service
        companies = await self.cs1.get_portfolio_companies(fund_id)

        views = []
        for company in companies:
            # We call the existing list endpoint because get_assessment by company is not fully standard in the api yet.
            # Usually it returns Dict, we will parse out fields.
            assessment_data = await self.cs3.list_assessments(company_id=company.company_id)
            items = assessment_data.get("items", [])
            org_air = 0.0
            vr_score = 0.0
            hr_score = 0.0
            syn_score = 1.0
            dims = {}
            ci = (0.0, 100.0)
            
            if items:
                v = items[0]
                org_air = v.get("org_air_score", 0.0)
                vr_score = v.get("v_r_score", 0.0)
                hr_score = v.get("h_r_score", 0.0)
                syn_score = v.get("synergy_score", 1.0)
                scores = v.get("dimension_scores", [])
                for s in scores:
                    dims[s["dimension"]] = s.get("score", 0.0)
                ci_list = v.get("confidence_interval")
                if ci_list and len(ci_list) >= 2:
                    ci = (ci_list[0], ci_list[1])
                    
            # Fetch specific evidence details
            evidence = await self.cs2.get_evidence(ticker=company.ticker)

            entry_score = await self._get_entry_score(company.company_id)

            views.append(PortfolioCompanyView(
                company_id=company.company_id,
                ticker=company.ticker,
                name=company.name,
                sector=company.sector.value if hasattr(company.sector, 'value') else company.sector,
                org_air=org_air,
                vr_score=vr_score,
                hr_score=hr_score,
                synergy_score=syn_score,
                dimension_scores=dims,
                confidence_interval=ci,
                entry_org_air=entry_score,
                delta_since_entry=org_air - entry_score,
                evidence_count=len(evidence),
            ))

        return views

    async def _get_entry_score(self, company_id: str) -> float:
        """
        Retrieve the entry Org-AI-R score for a company.

        Strategy: fetch all assessments from CS3 for this company, sort
        ascending by creation date, and return the org_air_score of the
        oldest record (i.e. the first assessment taken at portfolio entry).
        Returns 0.0 if no assessments exist yet.
        """
        try:
            data = await self.cs3.list_assessments(
                company_id=company_id,
                page_size=100,
            )
            items = data.get("items", [])
            if not items:
                return 0.0

            # Sort oldest-first and take the first record as the entry baseline
            def _parse_ts(item: dict) -> str:
                return item.get("created_at") or item.get("assessment_date") or ""

            sorted_items = sorted(items, key=_parse_ts)
            return float(sorted_items[0].get("org_air_score") or 0.0)

        except Exception:
            logger.warning("entry_score_unavailable", company_id=company_id)
            return 0.0

# Singleton instance
portfolio_data_service = PortfolioDataService()
