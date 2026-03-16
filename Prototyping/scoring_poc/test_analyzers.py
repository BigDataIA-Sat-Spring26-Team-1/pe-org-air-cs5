from decimal import Decimal
from market_analyzer import PositionFactorCalculator
from talent_analyzer import TalentConcentrationCalculator

def test_market():
    print("--- Testing Market Position Factor ---")
    calc = PositionFactorCalculator()
    
    # Test cases: Case, Market Cap
    cases = [
        ("NVIDIA (Mega)", Decimal("3000000000000")), # $3T
        ("Mid Tier", Decimal("100000000000")),      # $100B
        ("Small established", Decimal("5000000000")), # $5B
        ("Startup/Laggard", Decimal("500000000"))   # $500M
    ]
    
    for name, cap in cases:
        factor = calc.calculate_position_factor(cap)
        label = calc.get_market_rank_label(factor)
        cap_val = cap / Decimal("1000000000")
        print(f"{name:<20} | Cap: ${cap_val:>7}B | Factor: {factor:<4} | Rank: {label}")

def test_talent():
    print("\n--- Testing Talent Concentration Risk ---")
    calc = TalentConcentrationCalculator()
    
    # Case 1: Distributed
    jobs_dist = [
        {"metadata": {"ai_keyword_count": 2}},
        {"metadata": {"ai_keyword_count": 3}},
        {"metadata": {"ai_keyword_count": 2}},
        {"metadata": {"ai_keyword_count": 3}},
    ]
    # Total kws = 10, max = 3. Ratio = 0.3. 
    
    # Case 2: Concentrated
    jobs_conc = [
        {"metadata": {"ai_keyword_count": 10}},
        {"metadata": {"ai_keyword_count": 1}},
        {"metadata": {"ai_keyword_count": 0}},
    ]
    # Total kws = 11, max = 10. Ratio = 0.9.
    
    risk_low = calc.calculate_concentration_score(jobs_dist, 1, 100) # 1% mentions
    risk_high = calc.calculate_concentration_score(jobs_conc, 15, 100) # 15% mentions (huge key person risk)
    
    print(f"Distributed Talent Risk: {risk_low}")
    print(f"Concentrated Talent Risk: {risk_high}")

if __name__ == "__main__":
    test_market()
    test_talent()
