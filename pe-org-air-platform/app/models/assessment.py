from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from datetime import timezone
from typing import Optional
from uuid import UUID
from .enums import AssessmentType, AssessmentStatus

class AssessmentBase(BaseModel):
    company_id: UUID
    assessment_type: AssessmentType
    assessment_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    primary_assessor: Optional[str] = None
    secondary_assessor: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "company_id": "1dec222c-6aaa-484c-8a68-6ed9ccce0685",
                "assessment_type": "due_diligence",
                "primary_assessor": "Jane Doe",
                "secondary_assessor": "John Smith"
            }
        }
    }

class AssessmentCreate(AssessmentBase):
    pass

class AssessmentResponse(AssessmentBase):
    id: UUID
    status: AssessmentStatus = AssessmentStatus.DRAFT
    v_r_score: Optional[float] = Field(None, ge=0, le=100)
    h_r_score: Optional[float] = Field(None, ge=0, le=100)
    synergy_score: Optional[float] = Field(None, ge=0, le=100)
    org_air_score: Optional[float] = Field(None, ge=0, le=100)
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
    confidence_lower: Optional[float] = Field(None, ge=0, le=100)
    confidence_upper: Optional[float] = Field(None, ge=0, le=100)
    created_at: datetime

    @model_validator(mode='after')
    def validate_confidence_interval(self) -> 'AssessmentResponse':
        if (self.confidence_upper is not None and 
            self.confidence_lower is not None and 
            self.confidence_upper < self.confidence_lower):
            raise ValueError('confidence_upper must be >= confidence_lower')
        return self

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "company_id": "1dec222c-6aaa-484c-8a68-6ed9ccce0685",
                "assessment_type": "due_diligence",
                "assessment_date": "2026-02-06T00:00:00",
                "primary_assessor": "Jane Doe",
                "secondary_assessor": "John Smith",
                "status": "draft",
                "v_r_score": 75.0,
                "confidence_lower": 70.0,
                "confidence_upper": 80.0,
                "created_at": "2026-02-06T00:00:00"
            }
        }
    }
