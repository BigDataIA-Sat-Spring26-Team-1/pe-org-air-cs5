import asyncio
import httpx
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum

# --- CS1 Interfaces ---
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

class CS1Client:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    async def get_portfolio_companies(self, fund_id: str) -> List[Company]:
        async with httpx.AsyncClient() as client:
            # We fetch all companies for this prototype
            resp = await client.get(f"{self.base_url}/api/v1/companies/")
            if resp.status_code != 200:
                print(f"CS1 Error: {resp.text}")
                return []
            
            data = resp.json().get("items", [])
            companies = []
            for c in data:
                # Map standard API fields to Company dataclass
                # Fallbacks for missing data
                sec_str = Sector.TECHNOLOGY
                companies.append(Company(
                    company_id=c.get("id", c["ticker"]),
                    ticker=c["ticker"],
                    name=c["name"],
                    sector=sec_str,
                    employee_count=1000,   # placeholder if missing
                    revenue_mm=100.0       # placeholder if missing
                ))
            return companies

# --- CS2 Interfaces ---
class SourceType(Enum):
    SEC_FILING = "sec_filing"
    PATENT = "patent"
    JOB_POSTING = "job_posting"
    GLASSDOOR = "glassdoor"
    NEWS = "news"
    EXPERT_CALL = "expert_call"
    NOTES = "notes"

@dataclass
class Evidence:
    evidence_id: str
    company_id: str
    source_type: SourceType
    content: str
    confidence: float
    signal_category: str
    dimension: Optional[str] = None
    source_url: Optional[str] = None

class CS2Client:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    async def get_evidence(self, company_id: str) -> List[Evidence]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/api/v1/companies/{company_id}/evidence")
            if resp.status_code != 200:
                return []
            data = resp.json()
            # Map API dict to Evidence dataclasses
            result = []
            for item in data:
                result.append(Evidence(
                    evidence_id=item.get("id", ""),
                    company_id=item.get("company_id", company_id),
                    source_type=SourceType.SEC_FILING, # mapping simple for now
                    content=item.get("chunk_text", item.get("content", ""))[:200],
                    confidence=0.8,
                    signal_category="tech"
                ))
            return result

# --- CS3 Interfaces ---
class Dimension(Enum):
    DATA_INFRASTRUCTURE = "data_infrastructure"
    AI_GOVERNANCE = "ai_governance"
    TECHNOLOGY_STACK = "technology_stack"
    TALENT = "talent"
    LEADERSHIP = "leadership"
    USE_CASE_PORTFOLIO = "use_case_portfolio"
    CULTURE = "culture"

@dataclass
class DimensionScore:
    dimension: Dimension
    score: float
    level: int
    evidence_count: int

@dataclass
class CompanyAssessment:
    company_id: str
    org_air_score: float
    vr_score: float
    hr_score: float
    synergy_score: float
    dimension_scores: Dict[Dimension, DimensionScore]
    confidence_interval: tuple
    evidence_count: int

class CS3Client:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    async def get_assessment(self, company_id: str) -> CompanyAssessment:
        async with httpx.AsyncClient() as client:
            # Note: The api takes company_id in the query params.
            resp = await client.get(f"{self.base_url}/api/v1/assessments?company_id={company_id}")
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items", [])
                if items:
                    assess = items[0]
                    dims = {}
                    scores = assess.get("dimension_scores", [])
                    for s in scores:
                        dim_name = s["dimension"].lower()
                        try:
                            dim_enum = Dimension(dim_name)
                        except:
                            continue
                        dims[dim_enum] = DimensionScore(dim_enum, s.get("score", 0), 1, 0)
                    
                    return CompanyAssessment(
                        company_id=company_id,
                        org_air_score=assess.get("org_air_score", 0.0),
                        vr_score=assess.get("v_r_score", 0.0),
                        hr_score=assess.get("h_r_score", 0.0),
                        synergy_score=assess.get("synergy_score", 1.0),
                        dimension_scores=dims,
                        confidence_interval=(0.0, 100.0),
                        evidence_count=0
                    )
                    
        # Fallback empty if not found
        return CompanyAssessment(
            company_id=company_id,
            org_air_score=0.0, vr_score=0.0, hr_score=0.0, synergy_score=1.0,
            dimension_scores={}, confidence_interval=(0.0, 100.0), evidence_count=0
        )

# --- CS4 Interfaces ---
class CS4Client:
    def __init__(self, base_url: str = "http://localhost:8000"):
        pass


# --- Portfolio Service ---
@dataclass
class PortfolioCompanyView:
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
    def __init__(self, base_url: str = "http://localhost:8000"):
        # Initializing the actual backend URLs
        self.cs1 = CS1Client(base_url=base_url)
        self.cs2 = CS2Client(base_url=base_url)
        self.cs3 = CS3Client(base_url=base_url)
        self.cs4 = CS4Client()

    async def get_portfolio_view(self, fund_id: str) -> List[PortfolioCompanyView]:
        companies = await self.cs1.get_portfolio_companies(fund_id)
        views = []
        for company in companies:
            assessment = await self.cs3.get_assessment(company.ticker)
            evidence = await self.cs2.get_evidence(company.ticker)
            entry_score = await self._get_entry_score(company.company_id)
            
            views.append(PortfolioCompanyView(
                company_id=company.company_id,
                ticker=company.ticker,
                name=company.name,
                sector=company.sector.value,
                org_air=assessment.org_air_score,
                vr_score=assessment.vr_score,
                hr_score=assessment.hr_score,
                synergy_score=assessment.synergy_score,
                dimension_scores={d.value: s.score for d, s in assessment.dimension_scores.items()},
                confidence_interval=assessment.confidence_interval,
                entry_org_air=entry_score,
                delta_since_entry=assessment.org_air_score - entry_score,
                evidence_count=len(evidence),
            ))
        return views

    async def _get_entry_score(self, company_id: str) -> float:
        return 45.0

async def main():
    service = PortfolioDataService(base_url="http://localhost")
    print("Testing PortfolioDataService against localhost...")
    views = await service.get_portfolio_view("growth_fund_v")
    print(f"Found {len(views)} companies.")
    for v in views:
        print(f"Company: {v.name} ({v.ticker})")
        print(f"  Sector: {v.sector}")
        print(f"  Org-AI-R: {v.org_air}")
        print(f"  Evidence items: {v.evidence_count}")
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(main())
