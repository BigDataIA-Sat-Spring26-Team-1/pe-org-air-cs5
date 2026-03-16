
import json
from decimal import Decimal

class EnhancedPFCalculator:
    def __init__(self):
        self.sector_avg_vr = {
            "technology": 65.0,
            "financial_services": 55.0,
            "healthcare": 52.0,
            "business_services": 50.0,
            "retail": 48.0,
            "manufacturing": 45.0,
        }

    def calculate_pf(self, vr_score, sector, mcap_percentile, signal_count):
        # 1. VR Component (Relative to peer average)
        avg_vr = self.sector_avg_vr.get(sector.lower(), 50.0)
        vr_norm = (vr_score - avg_vr) / 50.0
        vr_component = max(-1.0, min(1.0, vr_norm))

        # 2. Market Cap Component (Normalized to [-1, 1])
        mcap_component = (mcap_percentile - 0.5) * 2.0

        # 3. ENHANCEMENT: Signal Intensity Factor
        # High signal counts indicate high activity/visibility in the domain
        # Let's assume a "baseline" activity of 5 unique signals for a major corp
        intensity = min(1.0, (signal_count - 2) / 10.0) if signal_count > 2 else -0.5
        
        # 4. ENHANCEMENT: Leadership Bonus
        # If you are in the top 5% of your sector and have high VR
        leadership_bonus = 0.0
        if mcap_percentile > 0.95 and vr_score > avg_vr:
            leadership_bonus = 0.5
        elif mcap_percentile < 0.2:
            leadership_bonus = -0.3

        # New Formula: 0.4 * VR + 0.3 * MCap + 0.3 * Intensity + Bonus
        pf = (0.4 * vr_component) + (0.3 * mcap_component) + (0.3 * intensity) + leadership_bonus
        
        # Clamp to [-1, 1]
        final_pf = max(-1.0, min(1.0, pf))
        return round(final_pf, 2)

def run_test():
    calc = EnhancedPFCalculator()
    # Mock data based on audit results
    companies = [
        {"ticker": "NVDA", "vr": 85.0, "sector": "technology", "mcap_p": 0.99, "signals": 15},
        {"ticker": "JPM",  "vr": 70.0, "sector": "financial_services", "mcap_p": 0.95, "signals": 10},
        {"ticker": "WMT",  "vr": 65.0, "sector": "retail", "mcap_p": 0.90, "signals": 8},
        {"ticker": "GE",   "vr": 50.0, "sector": "manufacturing", "mcap_p": 0.60, "signals": 5},
        {"ticker": "DG",   "vr": 30.0, "sector": "retail", "mcap_p": 0.40, "signals": 2} # Low signals
    ]

    print(f"{'Ticker':<8} | {'VR':<5} | {'MCap%':<6} | {'Sig':<3} | {'Enhanced PF':<12}")
    print("-" * 45)
    for c in companies:
        pf = calc.calculate_pf(c['vr'], c['sector'], c['mcap_p'], c['signals'])
        print(f"{c['ticker']:<8} | {c['vr']:<5} | {c['mcap_p']:<6} | {c['signals']:<3} | {pf:<12}")

if __name__ == "__main__":
    run_test()
