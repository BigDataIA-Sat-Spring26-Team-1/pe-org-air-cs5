from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from uuid import UUID
from typing import Optional
from .enums import Dimension

DIMENSION_WEIGHTS = {
    Dimension.DATA_INFRASTRUCTURE: 0.25,
    Dimension.AI_GOVERNANCE: 0.20,
    Dimension.TECHNOLOGY_STACK: 0.15,
    Dimension.TALENT: 0.15,
    Dimension.LEADERSHIP: 0.10,
    Dimension.USE_CASE_PORTFOLIO: 0.10,
    Dimension.CULTURE: 0.05
}

class DimensionScoreBase(BaseModel):
    assessment_id: UUID
    dimension: Dimension
    score: float = Field(..., ge=0, le=100)
    weight: Optional[float] = Field(default=None, ge=0, le=1)
    confidence: float = Field(default=0.8, ge=0, le=1)
    evidence_count: int = Field(default=0, ge=0)

    model_config = {
        "json_schema_extra": {
            "example": {
                "assessment_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "dimension": "data_infrastructure",
                "score": 85.5,
                "confidence": 0.9,
                "evidence_count": 12
            }
        }
    }

    @model_validator(mode='after')
    def set_default_weight(self) -> 'DimensionScoreBase':
        if self.weight is None:
            self.weight = DIMENSION_WEIGHTS.get(self.dimension, 0.1)
        return self

class DimensionScoreCreate(DimensionScoreBase):
    pass

class DimensionScoreResponse(DimensionScoreBase):
    id: UUID
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "assessment_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "dimension": "data_infrastructure",
                "score": 85.5,
                "weight": 0.25,
                "confidence": 0.9,
                "evidence_count": 12,
                "created_at": "2026-02-06T00:00:00"
            }
        }
    }
