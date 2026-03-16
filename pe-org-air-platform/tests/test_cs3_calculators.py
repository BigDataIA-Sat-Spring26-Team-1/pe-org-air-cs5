
import pytest
from decimal import Decimal
from app.scoring.calculators import VRCalculator, HRCalculator, SynergyCalculator, OrgAIRCalculator

def test_vr_calculation():
    calc = VRCalculator()
    scores = {
        "talent": Decimal("80.0"),
        "leadership": Decimal("70.0"),
        "culture": Decimal("60.0")
    }
    # Weighted mean + CV penalty
    vr = calc.calculate_vr(scores)
    assert vr > 0
    assert vr <= 100

def test_hr_calculation():
    calc = HRCalculator(alpha=Decimal("0.15"))
    hr_base = Decimal("70.0")
    pf = Decimal("0.5")
    # HR = HR_base * (1 + alpha * PF)
    hr = calc.calculate_hr(hr_base, pf)
    assert hr == hr_base * (Decimal("1") + Decimal("0.15") * pf)

def test_synergy_calculation():
    calc = SynergyCalculator()
    vr = Decimal("80.0")
    hr = Decimal("70.0")
    # Synergy = (VR * HR / 100) * Alignment * Timing
    syn = calc.calculate_synergy(vr, hr)
    assert syn == (vr * hr / Decimal("100"))

def test_org_air_aggregator():
    calc = OrgAIRCalculator()
    dims = {
        "talent": Decimal("80.0"), "leadership": Decimal("80.0"),
        "culture": Decimal("80.0"), "data_infrastructure": Decimal("80.0"),
        "ai_governance": Decimal("80.0"), "technology_stack": Decimal("80.0"),
        "use_case_portfolio": Decimal("80.0")
    }
    confs = [Decimal("0.8")] * 7
    
    res = calc.calculate_org_air(
        dimension_scores=dims,
        dimension_confidences=confs,
        position_factor=Decimal("0.5"),
        hr_base=Decimal("70.0"),
        alpha=Decimal("0.6"),
        beta=Decimal("0.12")
    )
    
    assert "org_air_score" in res
    assert res["org_air_score"] > 0
