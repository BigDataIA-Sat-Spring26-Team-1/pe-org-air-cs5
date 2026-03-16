from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class PositionFactorCalculator:
    """
    Determines a company's market position factor based on market capitalization
    relative to a peer group or general market thresholds.
    """
    
    # Thresholds for market cap in billions (Simplified for POC)
    # Mega Cap: > $200B -> 0.9 - 1.0
    # Large Cap: $10B - $200B -> 0.5 - 0.9
    # Mid Cap: $2B - $10B -> 0.3 - 0.5
    # Small Cap: < $2B -> 0.1 - 0.3
    
    def calculate_position_factor(self, market_cap_usd: Decimal) -> Decimal:
        """
        Calculates the PositionFactor used in the HR calculation:
        HR = HR_base * (1 + 0.15 * PositionFactor)
        
        PositionFactor range: [0.0, 1.0]
        """
        # Convert to billions for easier thresholding
        cap_billions = market_cap_usd / Decimal("1000000000")
        
        if cap_billions >= Decimal("200"): # Mega Cap (NVIDIA, Apple, etc)
            factor = Decimal("0.9") + (min(Decimal("1.0"), cap_billions / Decimal("3000")) * Decimal("0.1"))
        elif cap_billions >= Decimal("10"): # Large Cap
            # Linear map $10B -> 0.5, $200B -> 0.9
            factor = Decimal("0.5") + ((cap_billions - Decimal("10")) / Decimal("190")) * Decimal("0.4")
        elif cap_billions >= Decimal("2"): # Mid Cap
            # Linear map $2B -> 0.3, $10B -> 0.5
            factor = Decimal("0.3") + ((cap_billions - Decimal("2")) / Decimal("8")) * Decimal("0.2")
        else: # Small Cap
            # Linear map $0 -> 0.1, $2B -> 0.3
            factor = Decimal("0.1") + (cap_billions / Decimal("2")) * Decimal("0.2")
            
        return round(max(Decimal("0.0"), min(Decimal("1.0"), factor)), 2)

    def get_market_rank_label(self, factor: Decimal) -> str:
        if factor >= Decimal("0.9"): return "Dominant (Mega Cap)"
        if factor >= Decimal("0.5"): return "Strong (Large Cap)"
        if factor >= Decimal("0.3"): return "Established (Mid Cap)"
        return "Emerging (Small Cap)"
