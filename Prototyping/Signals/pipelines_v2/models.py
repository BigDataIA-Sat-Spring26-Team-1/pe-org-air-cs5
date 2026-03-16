from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import uuid

class SignalCategory(str, Enum):
    TECHNOLOGY_HIRING = "technology_hiring"
    INNOVATION_ACTIVITY = "innovation_activity"
    DIGITAL_PRESENCE = "digital_presence"
    LEADERSHIP_SIGNALS = "leadership_signals"

class CollectorResult(BaseModel):
    category: SignalCategory
    normalized_score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    raw_value: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    signal_date: str = Field(default_factory=lambda: datetime.now().date().isoformat())
    source: str

class CompanySignalSummary(BaseModel):
    company_id: str
    ticker: str
    technology_hiring_score: float = 0.0
    innovation_activity_score: float = 0.0
    digital_presence_score: float = 0.0
    leadership_signals_score: float = 0.0
    composite_score: float = 0.0
    signal_count: int = 0
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class ExternalSignal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_id: str
    category: SignalCategory
    source: str
    signal_date: str
    raw_value: str
    normalized_score: float
    confidence: float
    metadata: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)
