from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional

class CompanyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    ticker: Optional[str] = Field(None, max_length=10)
    industry_id: Optional[UUID] = None
    position_factor: float = Field(default=0.0, ge=-1.0, le=1.0)
    cik: Optional[str] = Field(None, max_length=20)
    name_norm: Optional[str] = Field(None, max_length=255)

    @field_validator('ticker')
    @classmethod
    def uppercase_ticker(cls, v: Optional[str]) -> Optional[str]:
        return v.upper() if v else None

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Caterpillar Inc.",
                "ticker": "CAT",
                "industry_id": "550e8400-e29b-41d4-a716-446655440001",
                "position_factor": 0.5,
                "cik": "0000018492",
                "name_norm": "caterpillar inc"
            }
        }
    }

class CompanyCreate(CompanyBase):
    pass

class CompanyResponse(CompanyBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "1dec222c-6aaa-484c-8a68-6ed9ccce0685",
                "name": "Caterpillar Inc.",
                "ticker": "CAT",
                "industry_id": "550e8400-e29b-41d4-a716-446655440001",
                "position_factor": 0.5,
                "cik": "0000018492",
                "name_norm": "caterpillar inc",
                "created_at": "2026-02-06T00:00:00",
                "updated_at": "2026-02-06T00:00:00"
            }
        }
    }