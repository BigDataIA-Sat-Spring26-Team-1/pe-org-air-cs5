from pydantic import BaseModel, Field, validator, root_validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import uuid

class SignalCategory(str, Enum):
    TECHNOLOGY_HIRING = "technology_hiring"
    INNOVATION_ACTIVITY = "innovation_activity"
    DIGITAL_PRESENCE = "digital_presence"
    LEADERSHIP_SIGNALS = "leadership_signals"
    # SEC Items
    SEC_ITEM_1 = "sec_item_1"
    SEC_ITEM_1A = "sec_item_1a"
    SEC_ITEM_7 = "sec_item_7"
    # New Sources
    GLASSDOOR_REVIEWS = "glassdoor_reviews"
    BOARD_COMPOSITION = "board_composition"
    TALENT_CONCENTRATION = "talent_concentration"

class SignalCollectionRequest(BaseModel):
    ticker: Optional[str] = Field(None, description="Company ticker symbol")
    company_name: Optional[str] = Field(None, description="Full company name")
    company_id: Optional[str] = None

    job_days: int = Field(7, ge=1, le=90, description="Lookback period for job postings in days")
    patent_years: int = Field(5, ge=1, le=20, description="Lookback period for patents in years")
    force_refresh: bool = Field(False, description="Whether to bypass cache and force a new run")

    @root_validator(pre=True)
    def check_identity(cls, values):
        ticker = values.get('ticker')
        company_name = values.get('company_name')
        if not ticker and not company_name:
            raise ValueError("Either 'ticker' or 'company_name' must be provided.")
        return values

    model_config = {
        "json_schema_extra": {
            "example": {
                "ticker": "CAT",
                "company_name": "Caterpillar Inc.",
                "job_days": 30,
                "patent_years": 5,
                "force_refresh": False
            }
        }
    }


class SignalEvidenceItem(BaseModel):
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    date: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CollectorResult(BaseModel):
    category: SignalCategory
    normalized_score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    raw_value: str
    evidence: List[SignalEvidenceItem] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict) # High-level pulse metadata only
    signal_date: str = Field(default_factory=lambda: datetime.now().date().isoformat())
    source: str

class ExternalSignal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    signal_hash: Optional[str] = None # SHA256(company_id + source + raw_identifier) for deduplication
    company_id: str
    category: SignalCategory
    source: str
    signal_date: str
    raw_value: str
    normalized_score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    metadata: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "signal_hash": "a1b2c3d4...",
                "company_id": "1dec222c-6aaa-484c-8a68-6ed9ccce0685",
                "category": "technology_hiring",
                "source": "LinkedIn",
                "signal_date": "2026-02-06",
                "raw_value": "15 open positions for Software Engineer",
                "normalized_score": 85.5,
                "confidence": 0.9,
                "metadata": {"job_title": "Software Engineer", "count": 15},
                "created_at": "2026-02-06T00:00:00"
            }
        }
    }

class SignalEvidence(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    signal_id: str
    company_id: str
    category: SignalCategory
    source: str
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    evidence_date: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "signal_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "company_id": "1dec222c-6aaa-484c-8a68-6ed9ccce0685",
                "category": "technology_hiring",
                "source": "LinkedIn",
                "title": "Software Engineer @ Caterpillar",
                "description": "Caterpillar is looking for a Software Engineer...",
                "url": "https://linkedin.com/jobs/...",
                "tags": ["java", "python"],
                "evidence_date": "2026-02-06",
                "metadata": {},
                "created_at": "2026-02-06T00:00:00"
            }
        }
    }

class CompanySignalSummary(BaseModel):
    company_id: str
    ticker: str
    technology_hiring_score: float = Field(default=0.0, ge=0, le=100)
    innovation_activity_score: float = Field(default=0.0, ge=0, le=100)
    digital_presence_score: float = Field(default=0.0, ge=0, le=100)
    leadership_signals_score: float = Field(default=0.0, ge=0, le=100)
    composite_score: float = Field(default=0.0, ge=0, le=100)
    signal_count: int = 0
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "json_schema_extra": {
            "example": {
                "company_id": "1dec222c-6aaa-484c-8a68-6ed9ccce0685",
                "ticker": "CAT",
                "technology_hiring_score": 85.5,
                "innovation_activity_score": 72.0,
                "digital_presence_score": 65.0,
                "leadership_signals_score": 90.0,
                "composite_score": 78.1,
                "signal_count": 150,
                "last_updated": "2026-02-06T00:00:00"
            }
        }
    }