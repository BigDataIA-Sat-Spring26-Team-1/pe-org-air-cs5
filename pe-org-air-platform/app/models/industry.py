from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional

class IndustryBase(BaseModel):
    name: str = Field(..., max_length=255)
    sector: str = Field(..., max_length=100)
    h_r_base: float = Field(..., ge=0, le=100)

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Manufacturing",
                "sector": "Industrial",
                "h_r_base": 0.5
            }
        }
    }

class IndustryCreate(IndustryBase):
    pass

class IndustryResponse(IndustryBase):
    id: UUID
    created_at: datetime
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "name": "Manufacturing",
                "sector": "Industrial",
                "h_r_base": 0.5,
                "created_at": "2026-02-06T00:00:00"
            }
        }
    }
