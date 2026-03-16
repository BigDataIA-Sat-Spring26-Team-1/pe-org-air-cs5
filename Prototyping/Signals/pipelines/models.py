from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Any, Optional
from datetime import datetime, date, timezone
from enum import Enum
from uuid import UUID, uuid4

class SignalCategory(str, Enum):
    TECHNOLOGY_HIRING = "technology_hiring"
    INNOVATION_ACTIVITY = "innovation_activity"
    DIGITAL_PRESENCE = "digital_presence"
    LEADERSHIP_SIGNALS = "leadership_signals"

class CollectorResult(BaseModel):
    """Internal validation model for collector outputs."""
    normalized_score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    raw_value: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ExternalSignal(BaseModel):
    """
    Validation model for the 'external_signals' Snowflake table.
    """
    id: UUID = Field(default_factory=uuid4)
    company_id: UUID
    category: SignalCategory
    source: str
    signal_date: date
    raw_value: str = Field(max_length=500)
    normalized_score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator('signal_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v).date()
        return v

class CompanySignalSummary(BaseModel):
    """
    Validation model for the 'company_signal_summaries' Snowflake table.
    """
    company_id: UUID
    ticker: str = Field(max_length=10)
    technology_hiring_score: float = Field(ge=0, le=100)
    innovation_activity_score: float = Field(ge=0, le=100)
    digital_presence_score: float = Field(ge=0, le=100)
    leadership_signals_score: float = Field(ge=0, le=100)
    composite_score: float = Field(ge=0, le=100)
    signal_count: int = Field(ge=0)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
