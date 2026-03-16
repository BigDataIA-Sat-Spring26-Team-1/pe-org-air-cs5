from decimal import Decimal
from typing import Dict, List, Optional, Any
import structlog
from .utils import weighted_mean, clamp, to_decimal, coefficient_of_variation, weighted_std_dev
from app.services.sector_config import sector_config

logger = structlog.get_logger(__name__)


class VRCalculator:
    """Calculates Vertical Readiness (V^R) from dimension scores with CV penalty."""

    def calculate_vr(self, dimension_scores: Dict[str, Decimal], sector: str = "default") -> Decimal:
        """
        Calculate V^R as weighted average of dimension scores, adjusted by CV penalty.
        
        V^R_base = Σ(dimension_score × weight)
        CV_penalty = 1 - 0.25 × CV(scores)
        V^R_final = V^R_base × CV_penalty
        """
        weights = sector_config.get_weights(sector)
        
        values = []
        w_list = []
        
        DIMENSION_FLOOR = Decimal("30.0")
        
        for dim, weight in weights.items():
            # Get score, default to 50 if missing entirely from dict,
            # but apply a floor if it was explicitly scored as 0 (no signals)
            score = dimension_scores.get(dim, Decimal("50.0"))
            score = max(score, DIMENSION_FLOOR)
            
            values.append(score)
            w_list.append(weight)
        
        # 1. Calculate Base VR (Weighted Mean)
        vr_base = weighted_mean(values, w_list)
        
        # 2. Calculate CV Penalty
        # Note: We use unweighted CV for consistency across dimensions
        mean_score = sum(values) / len(values) if values else Decimal("0")
        if mean_score > 0:
            std_dev = (sum((s - mean_score)**2 for s in values) / len(values)).sqrt()
            cv = std_dev / mean_score
        else:
            cv = Decimal("1.0")
            
        cv_penalty = Decimal("1.0") - (Decimal("0.25") * cv)
        vr_final = vr_base * cv_penalty
        vr_final = clamp(vr_final, Decimal("0"), Decimal("100"))
        
        # Audit Trail
        logger.info(
            "vr_calculated",
            vr_base=float(vr_base),
            cv=float(cv),
            cv_penalty=float(cv_penalty),
            vr_final=float(vr_final),
            sector=sector,
            dimension_breakdown={k: float(v) for k, v in dimension_scores.items()}
        )
        
        return to_decimal(float(vr_final), places=2)


class HRCalculator:
    """Calculates Horizontal Readiness (H^R) from market position."""
    
    def __init__(self, alpha: Decimal = Decimal("0.15")):
        self.alpha = alpha

    def calculate_hr(
        self, 
        hr_base: Decimal, 
        position_factor: Decimal
    ) -> Decimal:
        """
        Calculate H^R incorporating market position.
        H^R = H^R_base × (1 + α × PositionFactor)
        """
        hr = hr_base * (Decimal("1") + self.alpha * position_factor)
        hr = clamp(hr, Decimal("0"), Decimal("100"))
        
        logger.info(
            "hr_calculated",
            hr_base=float(hr_base),
            position_factor=float(position_factor),
            alpha=float(self.alpha),
            hr_final=float(hr)
        )
        
        return to_decimal(float(hr), places=2)


class SynergyCalculator:
    """Calculates final Synergy Score from V^R and H^R."""

    def calculate_synergy(
        self,
        vr_score: Decimal,
        hr_score: Decimal,
        alignment_factor: Decimal = Decimal("1.0"),
        timing_factor: Decimal = Decimal("1.0")
    ) -> Decimal:
        """
        Calculate Synergy Score.
        Synergy = (V^R × H^R / 100) × Alignment × Timing
        """
        base_synergy = (vr_score * hr_score) / Decimal("100")
        synergy = base_synergy * alignment_factor * timing_factor
        synergy = clamp(synergy, Decimal("0"), Decimal("100"))
        
        logger.info(
            "synergy_calculated",
            vr_score=float(vr_score),
            hr_score=float(hr_score),
            alignment=float(alignment_factor),
            timing=float(timing_factor),
            synergy_final=float(synergy)
        )
        
        return to_decimal(float(synergy), places=2)


class ConfidenceCalculator:
    """Calculates overall confidence using SEM (Standard Error of Measurement)."""

    def calculate_sem(
        self, 
        values: List[Decimal], 
        reliability_r: Decimal = Decimal("0.7")
    ) -> Dict[str, Decimal]:
        """
        Calculate SEM using Spearman-Brown Prophecy Formula.
        
        ρ = (n * r) / (1 + (n - 1) * r)
        SEM = σ * sqrt(1 - ρ)
        
        Args:
            values: List of confidence values or scores
            reliability_r: Inter-item correlation (Default 0.7 for high quality inputs)
        """
        if not values or len(values) < 2:
            return {"sem": Decimal("0"), "rho": Decimal("1.0"), "sigma": Decimal("0")}

        n = Decimal(str(len(values)))
        
        # 1. Calculate Rho (Spearman-Brown)
        rho_numerator = n * reliability_r
        rho_denominator = Decimal("1") + (n - Decimal("1")) * reliability_r
        rho = rho_numerator / rho_denominator
        
        # 2. Calculate Sigma (Standard Deviation)
        mean = sum(values) / n
        variance = sum((x - mean)**2 for x in values) / (n - Decimal("1"))
        sigma = variance.sqrt()
        
        # 3. Calculate SEM
        sem = sigma * (Decimal("1") - rho).sqrt()
        
        return {
            "sem": sem,
            "rho": rho,
            "sigma": sigma,
            "n": n
        }

    def calculate_overall_confidence(
        self, 
        dimension_confidences: List[Decimal]
    ) -> Decimal:
        """
        Final confidence score adjusted for measurement error.
        Confidence = Mean_Conf * (1 - SEM)
        """
        if not dimension_confidences:
            return Decimal("0.0")
        
        stats = self.calculate_sem(dimension_confidences)
        mean_conf = sum(dimension_confidences) / Decimal(str(len(dimension_confidences)))
        
        # Penalty increases as SEM increases (meaning low consensus/high variance)
        final_conf = mean_conf * (Decimal("1.0") - stats["sem"])
        
        return clamp(final_conf, Decimal("0"), Decimal("1"))


class OrgAIRCalculator:
    """Final aggregator for the PE Org-AI-R System (Lab 6)."""

    def __init__(self):
        self.vr_calc = VRCalculator()
        self.hr_calc = HRCalculator()
        self.synergy_calc = SynergyCalculator()
        self.conf_calc = ConfidenceCalculator()

    def calculate_org_air(
        self,
        dimension_scores: Dict[str, Decimal],
        dimension_confidences: List[Decimal],
        position_factor: Decimal,
        hr_base: Decimal = Decimal("70.0"),
        sector: str = "default",
        alignment: Decimal = Decimal("1.0"),
        timing: Decimal = Decimal("1.0"),
        alpha: Decimal = Decimal("0.6"), # V^R vs H^R weight
        beta: Decimal = Decimal("0.4"),  # Base Readiness vs Synergy weight
        z_score: Decimal = Decimal("1.96"), # 95% Confidence Interval
        company_id: Optional[str] = None,
        assessment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate final Org-AI-R score using weighted composite formula.
        
        Org-AI-R = (1 - β) * [α * V^R + (1 - α) * H^R] + β * Synergy
        CI = score ± z * SEM
        """
        # Bind context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            company_id=company_id,
            assessment_id=assessment_id,
            sector=sector
        )
        
        # 1. Component Scores
        vr_score = self.vr_calc.calculate_vr(dimension_scores, sector=sector)
        hr_score = self.hr_calc.calculate_hr(hr_base, position_factor)
        synergy_score = self.synergy_calc.calculate_synergy(vr_score, hr_score, alignment, timing)
        
        # 2. Base Readiness (Composite of V and H)
        # Base = α * V^R + (1 - α) * H^R
        base_readiness = (alpha * vr_score) + (Decimal("1") - alpha) * hr_score
        
        # 3. Final Org-AI-R
        # Score = (1 - β) * Base + β * Synergy
        final_score = (Decimal("1") - beta) * base_readiness + (beta * synergy_score)
        
        # 4. Stat Precision (SEM & CI)
        # We calculate SEM based on the input dimension scores to see variance across the framework
        sem_stats = self.conf_calc.calculate_sem(list(dimension_scores.values()))
        sem = sem_stats["sem"]
        ci_margin = z_score * sem
        
        # 5. Final Confidence Adjustment
        confidence = self.conf_calc.calculate_overall_confidence(dimension_confidences)
        
        import uuid
        audit_id = str(uuid.uuid4())
        
        result = {
            "org_air_score": float(to_decimal(float(final_score), 2)),
            "v_r": float(vr_score),
            "h_r": float(hr_score),
            "synergy": float(synergy_score),
            "confidence": float(confidence),
            "ci_lower": float(max(Decimal("0"), final_score - ci_margin)),
            "ci_upper": float(min(Decimal("100"), final_score + ci_margin)),
            "sem": float(sem),
            "reliability_rho": float(sem_stats["rho"]),
            "audit_log_id": audit_id
        }
        
        logger.info(
            "org_air_calculation_complete",
            company_score=result["org_air_score"],
            weights={"alpha": float(alpha), "beta": float(beta)},
            precision={
                "sem": result["sem"],
                "rho": result["reliability_rho"],
                "ci": [result["ci_lower"], result["ci_upper"]]
            },
            audit_id=audit_id
        )
        
        return result
