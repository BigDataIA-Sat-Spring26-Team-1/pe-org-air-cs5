from decimal import Decimal
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class VRCalculator:
    """
    Vertical Readiness (VR) Aggregator.
    Takes 7 dimension scores and produces a final VR score.
    """
    
    # Standard weights for dimensions (Sum = 1.0)
    # Adjust based on importance
    WEIGHTS = {
        "data_infrastructure": Decimal("0.15"),
        "technology_stack": Decimal("0.20"),
        "talent": Decimal("0.20"),
        "use_case_portfolio": Decimal("0.15"),
        "ai_governance": Decimal("0.10"),
        "leadership": Decimal("0.10"),
        "culture": Decimal("0.10")
    }
    
    def calculate_vr(self, dimension_scores: Dict[str, Decimal]) -> Decimal:
        vr = Decimal("0.0")
        for dim, weight in self.WEIGHTS.items():
            score = dimension_scores.get(dim, Decimal("50.0"))
            vr += score * weight
        return round(vr, 2)

class HRCalculator:
    """
    Horizontal Readiness (HR) Calculator.
    Accounts for market dominance and position factor.
    """
    
    def calculate_hr(self, hr_base: Decimal, position_factor: Decimal) -> Decimal:
        """
        Formula: HR = HR_base * (1 + 0.15 * PositionFactor)
        """
        hr = hr_base * (Decimal("1.0") + Decimal("0.15") * position_factor)
        return round(max(Decimal("0.0"), min(Decimal("100.0"), hr)), 2)

class SynergyCalculator:
    """
    Calculates final Synergy score.
    """
    
    def calculate_synergy(
        self, 
        vr: Decimal, 
        hr: Decimal, 
        alignment: Decimal, 
        timing_factor: Decimal = Decimal("1.0")
    ) -> Decimal:
        """
        Formula: Synergy = (VR * HR / 100) * Alignment * TimingFactor
        Alignment range: [0.0, 1.0]
        TimingFactor range: [0.8, 1.2]
        """
        synergy = (vr * hr / Decimal("100")) * alignment * timing_factor
        return round(max(Decimal("0.0"), min(Decimal("100.0"), synergy)), 2)

class ConfidenceCalculator:
    """
    Implements Standard Error of Measurement (SEM) to derive confidence.
    """
    
    def calculate_overall_confidence(self, dimension_confidences: List[Decimal]) -> Decimal:
        if not dimension_confidences:
            return Decimal("0.0")
        
        # Simple aggregation for POC: Mean of confidences
        avg_conf = sum(dimension_confidences) / Decimal(str(len(dimension_confidences)))
        return round(avg_conf, 2)
