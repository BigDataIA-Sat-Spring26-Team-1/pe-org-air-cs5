from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
from decimal import Decimal
from pydantic import BaseModel, Field

class Dimension(str, Enum):
    """The 7 standard V^R dimensions."""
    DATA_INFRASTRUCTURE = "data_infrastructure"
    AI_GOVERNANCE = "ai_governance"
    TECHNOLOGY_STACK = "technology_stack"
    TALENT = "talent"
    LEADERSHIP = "leadership"
    USE_CASE_PORTFOLIO = "use_case_portfolio"
    CULTURE = "culture"

class SignalSource(str, Enum):
    """Signal source categories that map to dimensions."""
    # CS2 External Signals
    TECHNOLOGY_HIRING = "technology_hiring"
    INNOVATION_ACTIVITY = "innovation_activity"
    DIGITAL_PRESENCE = "digital_presence"
    LEADERSHIP_SIGNALS = "leadership_signals"
    # CS2 SEC Sections
    SEC_ITEM_1 = "sec_item_1"
    SEC_ITEM_1A = "sec_item_1a"
    SEC_ITEM_7 = "sec_item_7"
    # CS3 New Sources
    GLASSDOOR_REVIEWS = "glassdoor_reviews"
    BOARD_COMPOSITION = "board_composition"

@dataclass
class DimensionMapping:
    """Maps a signal source to dimensions with contribution weights."""
    source: SignalSource
    primary_dimension: Dimension
    primary_weight: Decimal
    secondary_mappings: Dict[Dimension, Decimal] = field(default_factory=dict)
    reliability: Decimal = Decimal("0.8")

@dataclass
class EvidenceScore:
    """A score from a single evidence source (input to mapper)."""
    source: SignalSource
    raw_score: Decimal      # 0-100
    confidence: Decimal     # 0-1
    evidence_count: int
    metadata: Dict = field(default_factory=dict)

@dataclass
class DimensionScore:
    """Aggregated score for one dimension (output from mapper)."""
    dimension: Dimension
    score: Decimal
    contributing_sources: List[SignalSource]
    total_weight: Decimal
    confidence: Decimal

class ReadinessScores(BaseModel):
    """Final readiness metrics for a company."""
    company_id: str
    company_name: str
    ticker: str
    
    # Dimension Scores (0-100)
    data_infrastructure: float = Field(ge=0, le=100)
    ai_governance: float = Field(ge=0, le=100)
    technology_stack: float = Field(ge=0, le=100)
    talent: float = Field(ge=0, le=100)
    leadership: float = Field(ge=0, le=100)
    use_case_portfolio: float = Field(ge=0, le=100)
    culture: float = Field(ge=0, le=100)
    
    # Aggregate Metrics (0-100)
    vertical_readiness: float = Field(ge=0, le=100)
    horizontal_readiness: float = Field(ge=0, le=100)
    synergy_score: float = Field(ge=0, le=100)
    
    # Metadata
    overall_confidence: float = Field(ge=0, le=1)
    position_factor: float = Field(ge=0, le=1)
    market_cap_usd: Optional[float] = None
    calculated_at: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_id": "123e4567-e89b-12d3-a456-426614174000",
                "company_name": "JPMorgan Chase",
                "ticker": "JPM",
                "data_infrastructure": 27.83,
                "ai_governance": 68.00,
                "technology_stack": 59.80,
                "talent": 83.16,
                "leadership": 68.00,
                "use_case_portfolio": 80.00,
                "culture": 74.65,
                "vertical_readiness": 65.83,
                "horizontal_readiness": 79.66,
                "synergy_score": 44.57,
                "overall_confidence": 0.36,
                "position_factor": 0.92,
                "market_cap_usd": 550000000000,
                "calculated_at": "2026-02-11T01:53:00Z"
            }
        }
