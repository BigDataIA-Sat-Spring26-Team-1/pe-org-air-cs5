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
        market_cap_percentile: float,  # 0.0 = smallest, 1.0 = largest in sector
    ) -> Decimal:
        """
        Calculate position factor from V^R and market cap.

        Args:
            vr_score: Company's V^R score (0-100)
            sector: Company sector
            market_cap_percentile: Position in sector by market cap (0-1)

        Returns:
            Position factor in [-1, 1]
        """
        # Get sector average V^R
        sector_avg = self.SECTOR_AVG_VR.get(sector.lower(), 50.0)

        # Calculate VR component
        vr_diff = vr_score - sector_avg
        vr_component = max(-1, min(1, vr_diff / 50))

        # Calculate market cap component
        mcap_component = (market_cap_percentile - 0.5) * 2

        # Weighted combination
        pf = 0.6 * vr_component + 0.4 * mcap_component

        # Bound to [-1, 1] and return as Decimal
        pf_bounded = max(-1, min(1, pf))
        return Decimal(str(round(pf_bounded, 2)))
