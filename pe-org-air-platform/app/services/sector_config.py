from decimal import Decimal
from typing import Dict
from app.models.enums import Dimension

class SectorConfigService:
    """
    Returns sector-specific weights for vertical readiness calculations.
    """
    
    DEFAULT_WEIGHTS = {
        "data_infrastructure": Decimal("0.15"),
        "ai_governance": Decimal("0.10"),
        "technology_stack": Decimal("0.20"),
        "talent": Decimal("0.20"),
        "leadership": Decimal("0.10"),
        "use_case_portfolio": Decimal("0.15"),
        "culture": Decimal("0.10"),
    }
    
    # Example sector-specific overlaps/overrides
    SECTOR_OVERRIDES = {
        "financial_services": {
            "ai_governance": Decimal("0.15"),
            "culture": Decimal("0.05"),
        },
        "technology": {
            "technology_stack": Decimal("0.25"),
            "leadership": Decimal("0.05"),
        }
    }

    def get_weights(self, sector: str = "default") -> Dict[str, Decimal]:
        """Get weights for a specific sector, falling back to defaults."""
        weights = self.DEFAULT_WEIGHTS.copy()
        overrides = self.SECTOR_OVERRIDES.get(sector.lower(), {})
        weights.update(overrides)
        
        # Ensure they sum to 1.0 (normalization)
        total = sum(weights.values())
        if total != Decimal("1.0"):
            return {k: (v / total).quantize(Decimal("0.01")) for k, v in weights.items()}
            
        return weights

sector_config = SectorConfigService()
