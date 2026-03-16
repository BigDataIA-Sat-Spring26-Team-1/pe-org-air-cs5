from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, Dict, List
from decimal import Decimal

@dataclass
class GlassdoorReview:
    id: str
    company_id: str
    ticker: str
    review_date: datetime
    rating: float
    title: Optional[str] = None
    pros: Optional[str] = None
    cons: Optional[str] = None
    advice_to_management: Optional[str] = None
    is_current_employee: bool = False
    job_title: Optional[str] = None
    location: Optional[str] = None
    culture_rating: float = 0.0
    diversity_rating: float = 0.0
    work_life_rating: float = 0.0
    senior_management_rating: float = 0.0
    comp_benefits_rating: float = 0.0
    career_opp_rating: float = 0.0
    recommend_to_friend: Optional[str] = None
    ceo_rating: Optional[str] = None
    business_outlook: Optional[str] = None
    raw_json: Optional[Dict] = None

@dataclass
class CultureSignal:
    company_id: str
    ticker: str
    batch_date: date
    innovation_score: Decimal
    data_driven_score: Decimal
    ai_awareness_score: Decimal
    change_readiness_score: Decimal
    overall_sentiment: Decimal
    review_count: int
    avg_rating: Decimal
    current_employee_ratio: Decimal
    positive_keywords_found: List[str] = field(default_factory=list)
    negative_keywords_found: List[str] = field(default_factory=list)
    confidence: Decimal = Decimal(0)