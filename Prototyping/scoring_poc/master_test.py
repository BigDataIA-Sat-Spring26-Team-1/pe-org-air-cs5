from decimal import Decimal
from evidence_mapper import EvidenceMapper, EvidenceScore, SignalSource, Dimension
from market_analyzer import PositionFactorCalculator
from talent_analyzer import TalentConcentrationCalculator
from final_calculators import VRCalculator, HRCalculator, SynergyCalculator, ConfidenceCalculator

def run_e2e_scoring():
    print("=== ORG-AI-R End-to-End Scoring Engine Prototype ===\n")

    # --- 1. DATA INPUTS (SIMULATED) ---
    market_cap = Decimal("2500000000000") # $2.5T (e.g. NVIDIA)
    hr_base = Decimal("75.0")            # Market capability base score
    alignment = Decimal("0.9")           # Product-Market alignment
    timing = Decimal("1.1")               # Early mover advantage
    
    # Raw evidence from signals pipeline
    evidence = [
        EvidenceScore(SignalSource.TECHNOLOGY_HIRING, Decimal("90"), Decimal("0.9"), 100),
        EvidenceScore(SignalSource.INNOVATION_ACTIVITY, Decimal("85"), Decimal("0.8"), 10),
        EvidenceScore(SignalSource.DIGITAL_PRESENCE, Decimal("95"), Decimal("0.9"), 1),
        EvidenceScore(SignalSource.GLASSDOOR_REVIEWS, Decimal("70"), Decimal("0.7"), 50),
        EvidenceScore(SignalSource.SEC_ITEM_1A, Decimal("80"), Decimal("0.95"), 1)
    ]
    
    # Job posts for talent risk
    jobs = [{"metadata": {"ai_keyword_count": 5}}, {"metadata": {"ai_keyword_count": 2}}]

    # --- 2. EXECUTE PIPELINE ---
    
    # Task 3: Mapping
    mapper = EvidenceMapper()
    dim_scores_obj = mapper.map_evidence_to_dimensions(evidence)
    
    # Convert to simple dict for VR calc
    raw_dim_scores = {d.value: s.score for d, s in dim_scores_obj.items()}
    
    # Task 2: Analyzers
    market_calc = PositionFactorCalculator()
    pos_factor = market_calc.calculate_position_factor(market_cap)
    
    talent_calc = TalentConcentrationCalculator()
    talent_risk = talent_calc.calculate_concentration_score(jobs, 5, 50)
    
    # Task 1: Final Math
    vr_calc = VRCalculator()
    vr_score = vr_calc.calculate_vr(raw_dim_scores)
    
    # Adjust VR if talent risk is high (Optional strategy)
    if talent_risk > Decimal("0.7"):
        print(f"⚠️ High Talent Risk ({talent_risk}) detected! Penalizing Talent score.")
        raw_dim_scores["talent"] *= (Decimal("1.0") - (talent_risk / Decimal("2")))
        vr_score = vr_calc.calculate_vr(raw_dim_scores)

    hr_calc = HRCalculator()
    hr_score = hr_calc.calculate_hr(hr_base, pos_factor)
    
    synergy_calc = SynergyCalculator()
    final_synergy = synergy_calc.calculate_synergy(vr_score, hr_score, alignment, timing)
    
    conf_calc = ConfidenceCalculator()
    overall_conf = conf_calc.calculate_overall_confidence([s.confidence for s in dim_scores_obj.values()])

    # --- 3. REPORT ---
    print(f"Company Profile:")
    cap_val = market_cap / Decimal("1000000000")
    print(f" - Market Cap: ${cap_val}B (Factor: {pos_factor})")
    print(f" - Talent Risk: {talent_risk}")
    print("-" * 30)
    print(f"DIMENSION SCORES:")
    for d, s in sorted(raw_dim_scores.items()):
        print(f" - {d:<20}: {s}")
    print("-" * 30)
    print(f"FINAL METRICS:")
    print(f" - Vertical Readiness (VR): {vr_score}")
    print(f" - Horizontal Readiness (HR): {hr_score}")
    print(f" - Synergy Score:            {final_synergy}")
    print(f" - Confidence:                {overall_conf}")
    print("=" * 50)

if __name__ == "__main__":
    run_e2e_scoring()
