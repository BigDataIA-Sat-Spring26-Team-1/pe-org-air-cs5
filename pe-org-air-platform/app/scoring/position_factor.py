from decimal import Decimal
from typing import Dict


class PositionFactorCalculator:
    """
    Calculate position factor for H^R.
    
    Formula: PF = 0.6 * VR_component + 0.4 * MCap_component
    
    Where:
    - VR_component = (vr_score - sector_avg_vr) / 50, clamped to [-1, 1]
    - MCap_component = (market_cap_percentile - 0.5) * 2
    
    Bounded to [-1, 1]
    """

    # Sector average V^R scores (from framework calibration data)
    SECTOR_AVG_VR: Dict[str, float] = {
        "technology": 65.0,
        "financial_services": 55.0,
        "healthcare": 52.0,
        "business_services": 50.0,
        "retail": 48.0,
        "manufacturing": 45.0,
    }

    def calculate_position_factor(
        self,
        vr_score: float,
        sector: str,
        market_cap_percentile: float,
    ) -> Decimal:
        """
        Calculate position factor from V^R and market cap.
        PF = 0.6 * VR_component + 0.4 * MCap_component
        """
        # Get sector average V^R (Fall back to 50.0 if unknown)
        sector_avg = self.SECTOR_AVG_VR.get(sector.lower(), 50.0)

        # Calculate VR component
        vr_diff = vr_score - sector_avg
        vr_component = max(-1.0, min(1.0, vr_diff / 50.0))

        # Calculate market cap component
        # (percentile - 0.5) * 2 maps [0, 1] to [-1, 1]
        mcap_component = (market_cap_percentile - 0.5) * 2.0

        # Weighted combination
        pf = (0.6 * vr_component) + (0.4 * mcap_component)

        # Bound to [-1, 1] and return as Decimal
        pf_bounded = max(-1.0, min(1.0, pf))
        return Decimal(str(round(pf_bounded, 2)))