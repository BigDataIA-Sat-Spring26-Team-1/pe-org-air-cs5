
import pytest
from hypothesis import given, strategies as st, settings
from decimal import Decimal
from typing import Dict

from app.scoring import (
    VRCalculator,
    HRCalculator,
    SynergyCalculator,
    ConfidenceCalculator,
    EvidenceMapper,
    PositionFactorCalculator,
    TalentConcentrationCalculator
)
from app.models.scoring import Dimension, SignalSource, EvidenceScore

@st.composite
def dimension_scores(draw):
    return {
        "data_infrastructure": Decimal(str(draw(st.floats(min_value=0, max_value=100)))),
        "ai_governance": Decimal(str(draw(st.floats(min_value=0, max_value=100)))),
        "technology_stack": Decimal(str(draw(st.floats(min_value=0, max_value=100)))),
        "talent": Decimal(str(draw(st.floats(min_value=0, max_value=100)))),
        "leadership": Decimal(str(draw(st.floats(min_value=0, max_value=100)))),
        "use_case_portfolio": Decimal(str(draw(st.floats(min_value=0, max_value=100)))),
        "culture": Decimal(str(draw(st.floats(min_value=0, max_value=100)))),
    }

@st.composite
def evidence_scores_list(draw, min_size=0, max_size=10):
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    sources = draw(st.lists(
        st.sampled_from(list(SignalSource)),
        min_size=min(size, len(list(SignalSource))),
        max_size=min(size, len(list(SignalSource))),
        unique=True
    ))
    
    return [
        EvidenceScore(
            source=source,
            raw_score=Decimal(str(draw(st.floats(min_value=0, max_value=100)))),
            confidence=Decimal(str(draw(st.floats(min_value=0, max_value=1)))),
            evidence_count=draw(st.integers(min_value=1, max_value=100)),
            metadata={}
        )
        for source in sources
    ]

class TestVRCalculatorProperties:
    @settings(max_examples=100)
    @given(dimension_scores())
    def test_vr_bounds(self, scores: Dict[str, Decimal]):
        calc = VRCalculator()
        vr = calc.calculate_vr(scores)
        assert Decimal("0") <= vr <= Decimal("100")
    
    @settings(max_examples=100)
    @given(dimension_scores())
    def test_vr_monotonicity(self, scores: Dict[str, Decimal]):
        calc = VRCalculator()
        vr_orig = calc.calculate_vr(scores)
        inc_scores = {d: min(Decimal("100"), s + Decimal("10")) for d, s in scores.items()}
        vr_inc = calc.calculate_vr(inc_scores)
        assert vr_inc >= vr_orig

class TestEvidenceMapperProperties:
    @settings(max_examples=100)
    @given(evidence_scores_list(min_size=0, max_size=10))
    def test_mapper_completeness(self, evidence):
        mapper = EvidenceMapper()
        res = mapper.map_evidence_to_dimensions(evidence)
        assert len(res) == 7

class TestHRCalculatorProperties:
    @settings(max_examples=100)
    @given(st.floats(min_value=0, max_value=100), st.floats(min_value=-1, max_value=1))
    def test_hr_bounds(self, hr_base, pf):
        calc = HRCalculator()
        hr = calc.calculate_hr(Decimal(str(hr_base)), Decimal(str(pf)))
        assert Decimal("0") <= hr <= Decimal("100")

class TestSynergyCalculatorProperties:
    @settings(max_examples=100)
    @given(st.floats(min_value=0, max_value=100), st.floats(min_value=0, max_value=100))
    def test_synergy_bounds(self, vr, hr):
        calc = SynergyCalculator()
        syn = calc.calculate_synergy(Decimal(str(vr)), Decimal(str(hr)))
        assert Decimal("0") <= syn <= Decimal("100")
