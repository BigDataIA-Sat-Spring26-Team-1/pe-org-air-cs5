import os
import sys
from decimal import Decimal
from typing import List, Dict

# Local imports
from snowflake_client import SnowflakeClient
from evidence_mapper import EvidenceMapper, EvidenceScore, SignalSource, Dimension
from market_analyzer import PositionFactorCalculator
from talent_analyzer import TalentConcentrationCalculator
from final_calculators import VRCalculator, HRCalculator, SynergyCalculator, ConfidenceCalculator

def run_full_verification(ticker: str = "JPM"):
    print(f"=== FULL E2E SCORING VERIFICATION: {ticker} ===\n")
    
    client = SnowflakeClient()
    
    # 1. Fetch Company Data
    company = client.fetch_company_by_ticker(ticker)
    if not company:
        print(f"❌ Company {ticker} not found!")
        return
    
    company_id = company['ID'] if 'ID' in company else company.get('id')
    company_name = company['NAME'] if 'NAME' in company else company.get('name')
    # Defaulting market cap if 0 recorded in this view
    market_cap_raw = company['MARKET_CAP'] if 'MARKET_CAP' in company else company.get('market_cap', 0)
    
    # Simple lookup for testing cap if missing
    caps = {"JPM": 550_000_000_000, "WMT": 500_000_000_000}
    market_cap = Decimal(str(market_cap_raw if market_cap_raw > 0 else caps.get(ticker, 100_000_000)))

    # 2. Fetch Signals from Snowflake
    signals = client.fetch_external_signals(company_id)
    
    # 3. Map to Evidence
    category_map = {
        "technology_hiring": SignalSource.TECHNOLOGY_HIRING,
        "innovation_activity": SignalSource.INNOVATION_ACTIVITY,
        "digital_presence": SignalSource.DIGITAL_PRESENCE,
        "leadership_signals": SignalSource.LEADERSHIP_SIGNALS,
        "sec_item_1": SignalSource.SEC_ITEM_1,
        "sec_item_1a": SignalSource.SEC_ITEM_1A,
        "sec_item_7": SignalSource.SEC_ITEM_7
    }

    evidence = []
    for s in signals:
        cat_key = (s['CATEGORY'] if 'CATEGORY' in s else s.get('category', '')).lower()
        enum_src = category_map.get(cat_key)
        norm_score = s['NORMALIZED_SCORE'] if 'NORMALIZED_SCORE' in s else s.get('normalized_score', 0)
        confidence = s['CONFIDENCE'] if 'CONFIDENCE' in s else s.get('confidence', 0.5)
        
        if enum_src:
            evidence.append(EvidenceScore(
                source=enum_src,
                raw_score=Decimal(str(norm_score)),
                confidence=Decimal(str(confidence)),
                evidence_count=1
            ))

    # 4. RUN PIPELINE
    
    # Task 3: Mapping
    mapper = EvidenceMapper()
    dim_scores_obj = mapper.map_evidence_to_dimensions(evidence)
    raw_dim_scores = {d.value: s.score for d, s in dim_scores_obj.items()}
    
    # Task 2: Analyzers
    market_calc = PositionFactorCalculator()
    pos_factor = market_calc.calculate_position_factor(market_cap)
    
    # Task 1: Final Calculations
    vr_calc = VRCalculator()
    vr_score = vr_calc.calculate_vr(raw_dim_scores)
    
    hr_calc = HRCalculator()
    hr_base = Decimal("70.0") # Baseline for HR
    hr_score = hr_calc.calculate_hr(hr_base, pos_factor)
    
    synergy_calc = SynergyCalculator()
    # Assuming alignment factor of 0.85 and timing of 1.0 for verification
    final_synergy = synergy_calc.calculate_synergy(vr_score, hr_score, Decimal("0.85"), Decimal("1.0"))
    
    conf_calc = ConfidenceCalculator()
    overall_conf = conf_calc.calculate_overall_confidence([s.confidence for s in dim_scores_obj.values()])

    # 5. FINAL REPORT
    print(f"REPORT FOR {company_name}:")
    cap_billions = market_cap / Decimal("1000000000")
    print(f" - Market Cap: ${cap_billions}B (Position Factor: {pos_factor})")
    print("-" * 40)
    print(f"{'DIMENSION':<25} | {'SCORE'}")
    print("-" * 40)
    for d, s in sorted(raw_dim_scores.items()):
        print(f" - {d:<20} | {s}")
    print("-" * 40)
    print(f"FINAL METRICS:")
    print(f" - Vertical Readiness (VR): {vr_score}")
    print(f" - Horizontal Readiness (HR): {hr_score}")
    print(f" - Synergy Score:            {final_synergy}")
    print(f" - Overall Confidence:       {overall_conf}")
    print("=" * 60)

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "JPM"
    run_full_verification(target)
