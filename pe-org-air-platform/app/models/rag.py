from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
from datetime import datetime, date
from decimal import Decimal

# --- CS1: Company & Portfolio Models ---

class Sector(str, Enum):
    TECHNOLOGY = "technology"
    FINANCIAL_SERVICES = "financial_services"
    HEALTHCARE = "healthcare"
    MANUFACTURING = "manufacturing"
    RETAIL = "retail"
    BUSINESS_SERVICES = "business_services"
    CONSUMER = "consumer"

class Company(BaseModel):
    company_id: str
    ticker: str
    name: str
    sector: Sector
    sub_sector: str
    market_cap_percentile: float
    revenue_millions: float
    employee_count: int
    fiscal_year_end: str

class Portfolio(BaseModel):
    portfolio_id: str
    name: str
    company_ids: List[str]
    fund_vintage: int

# --- CS2: Evidence & Signal Models ---

class SourceType(str, Enum):
    SEC_10K_ITEM_1 = "sec_10k_item_1"
    SEC_10K_ITEM_1A = "sec_10k_item_1a"
    SEC_10K_ITEM_7 = "sec_10k_item_7"
    SEC_FILING = "sec_filing"
    JOB_POSTING = "job_posting"
    JOB_POSTING_LINKEDIN = "job_posting_linkedin"
    JOB_POSTING_INDEED = "job_posting_indeed"
    PATENT = "patent"
    PATENT_USPTO = "patent_uspto"
    PRESS_RELEASE = "press_release"
    GLASSDOOR = "glassdoor"
    GLASSDOOR_REVIEW = "glassdoor_review"
    BOARD_PROXY_DEF14A = "board_proxy_def14a"
    ANALYST_INTERVIEW = "analyst_interview"
    DD_DATA_ROOM = "dd_data_room"
    DD_FINDING = "dd_finding"
    SOURCE_NEWS = "source_news"

class SignalCategory(str, Enum):
    TECHNOLOGY_HIRING = "technology_hiring"
    INNOVATION_ACTIVITY = "innovation_activity"
    DIGITAL_PRESENCE = "digital_presence"
    LEADERSHIP_SIGNALS = "leadership_signals"
    CULTURE_SIGNALS = "culture_signals"
    GOVERNANCE_SIGNALS = "governance_signals"
    TALENT = "talent"
    INNOVATION = "innovation"
    LEADERSHIP = "leadership"
    TECHNOLOGY_STACK = "technology_stack"
    SEC_FILING = "sec_filing"
    GENERAL = "general"

class ExtractedEntity(BaseModel):
    entity_type: str
    text: str
    char_start: int
    char_end: int
    confidence: float
    attributes: Dict[str, Any] = Field(default_factory=dict)

class CS2Evidence(BaseModel):
    evidence_id: str
    company_id: str
    source_type: SourceType
    signal_category: SignalCategory
    content: str
    extracted_at: datetime
    confidence: float
    fiscal_year: Optional[int] = None
    source_url: Optional[str] = None
    page_number: Optional[int] = None
    extracted_entities: List[ExtractedEntity] = Field(default_factory=list)
    indexed_in_cs4: bool = False
    indexed_at: Optional[datetime] = None

# --- CS3: Scoring & Rubric Models ---

class Dimension(str, Enum):
    DATA_INFRASTRUCTURE = "data_infrastructure"
    AI_GOVERNANCE = "ai_governance"
    TECHNOLOGY_STACK = "technology_stack"
    TALENT = "talent"
    LEADERSHIP = "leadership"
    USE_CASE_PORTFOLIO = "use_case_portfolio"
    CULTURE = "culture"

class ScoreLevel(int, Enum):
    LEVEL_5 = 5 # 80-100: Excellent
    LEVEL_4 = 4 # 60-79: Good
    LEVEL_3 = 3 # 40-59: Adequate
    LEVEL_2 = 2 # 20-39: Developing
    LEVEL_1 = 1 # 0-19: Nascent

    @property
    def name_label(self) -> str:
        labels = {5: "Excellent", 4: "Good", 3: "Adequate", 2: "Developing", 1: "Nascent"}
        return labels.get(self.value, "Unknown")

class DimensionScore(BaseModel):
    dimension: Dimension
    score: float
    level: ScoreLevel
    confidence_interval: Tuple[float, float]
    evidence_count: int
    last_updated: str

class RubricCriteria(BaseModel):
    dimension: Dimension
    level: ScoreLevel
    criteria_text: str
    keywords: List[str]
    quantitative_thresholds: Dict[str, float] = Field(default_factory=dict)

class CompanyAssessment(BaseModel):
    company_id: str
    assessment_date: str
    vr_score: float
    hr_score: float
    synergy_score: float
    org_air_score: float
    confidence_interval: Tuple[float, float]
    dimension_scores: Dict[Dimension, DimensionScore]
    talent_concentration: float
    position_factor: float

# --- CS4: RAG, Retrieval & Workflow Models ---

class TaskType(str, Enum):
    EVIDENCE_EXTRACTION = "evidence_extraction"
    DIMENSION_SCORING = "dimension_scoring"
    JUSTIFICATION_GENERATION = "justification_generation"
    CHAT_RESPONSE = "chat_response"

class ModelConfig(BaseModel):
    primary: str
    fallbacks: List[str]
    temperature: float
    max_tokens: int
    cost_per_1k_tokens: float

class DailyBudget(BaseModel):
    budget_date: date = Field(default_factory=date.today)
    spent_usd: Decimal = Decimal("0")
    limit_usd: Decimal = Decimal("50.00")

class SearchResult(BaseModel):
    doc_id: str
    content: str
    score: float
    metadata: Dict[str, Any]

class RetrievedDocument(BaseModel):
    doc_id: str
    content: str
    metadata: Dict[str, Any]
    score: float
    retrieval_method: str # "dense", "sparse", "hybrid"

class CitedEvidence(BaseModel):
    evidence_id: str
    content: str # Truncated to 500 chars
    source_type: str
    source_url: Optional[str] = None
    confidence: float
    matched_keywords: List[str] = []
    relevance_score: float

class ScoreJustification(BaseModel):
    company_id: str
    dimension: Dimension
    score: float
    level: int
    level_name: str
    confidence_interval: Tuple[float, float]
    rubric_criteria: str
    rubric_keywords: List[str]
    supporting_evidence: List[CitedEvidence]
    gaps_identified: List[str]
    generated_summary: str
    evidence_strength: str # "strong", "moderate", "weak"

class ICMeetingPackage(BaseModel):
    company: Company
    assessment: CompanyAssessment
    dimension_justifications: Dict[Dimension, ScoreJustification]
    executive_summary: str
    key_strengths: List[str]
    key_gaps: List[str]
    risk_factors: List[str]
    recommendation: str
    generated_at: str
    total_evidence_count: int
    avg_evidence_strength: str
