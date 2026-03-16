
import pytest
from app.models.company import CompanyCreate
from app.models.assessment import AssessmentResponse
from app.models.dimension import DimensionScoreCreate
from app.models.enums import AssessmentType, Dimension
from uuid import uuid4
from pydantic import ValidationError

def test_company_creation_validation():
    # Ticker case normalization
    c = CompanyCreate(name="Tesla", ticker="tsla", industry_id=uuid4())
    assert c.ticker == "TSLA"

    # Factor ranges
    with pytest.raises(ValidationError):
        CompanyCreate(name="T", ticker="T", industry_id=uuid4(), position_factor=1.5)

def test_assessment_schema_logic():
    # Confidence range validation
    with pytest.raises(ValidationError):
         AssessmentResponse(
            id=uuid4(), company_id=uuid4(), 
            assessment_type=AssessmentType.SCREENING, 
            confidence_lower=90, confidence_upper=10 
        )

def test_dimension_weight_defaults():
    # Default weight for core dimensions
    ds = DimensionScoreCreate(
        assessment_id=uuid4(),
        dimension=Dimension.DATA_INFRASTRUCTURE,
        score=75.0
    )
    assert ds.weight == 0.25
    
    ds2 = DimensionScoreCreate(
        assessment_id=uuid4(),
        dimension=Dimension.TALENT,
        score=50.0
    )
    assert ds2.weight == 0.15

def test_manual_weight_overrides():
    ds = DimensionScoreCreate(
        assessment_id=uuid4(),
        dimension=Dimension.CULTURE,
        score=50.0,
        weight=0.8
    )
    assert ds.weight == 0.8