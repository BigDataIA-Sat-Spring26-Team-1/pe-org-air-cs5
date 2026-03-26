"""
EBITDA impact projector using Org-AI-R v2.0 scoring parameters.

The model translates a change in Org-AI-R score into projected EBITDA margin
improvement across three scenarios. Human Readiness (H^R) acts as an execution
confidence modifier — higher H^R means the organisation is better positioned to
capture the projected upside.

v2.0 parameters (from orgair://parameters/v2.0):
    gamma_0 = 0.0025   per-point base uplift from data/infra improvements
    gamma_1 = 0.05     base-case EBITDA multiplier per Org-AI-R point
    gamma_2 = 0.025    conservative multiplier
    gamma_3 = 0.01     execution risk discount factor

Approval gate: flag for HITL when optimistic projection exceeds 5 %.
"""

# v2.0 scoring parameters
_GAMMA_0 = 0.0025
_GAMMA_1 = 0.05
_GAMMA_2 = 0.025
_GAMMA_3 = 0.01

_HITL_THRESHOLD_PCT = 5.0


class Projection:
    def __init__(
        self,
        entry_score: float,
        target_score: float,
        h_r_score: float,
    ):
        self.delta_air = target_score - entry_score

        # Human Readiness modifier: normalise to [0, 1] range
        hr_factor = max(0.0, min(h_r_score, 100.0)) / 100.0

        # Base case: standard per-point uplift
        self.base_pct = round(_GAMMA_1 * self.delta_air, 2)

        # Conservative: reduced multiplier, no HR uplift
        self.conservative_pct = round(_GAMMA_2 * self.delta_air, 2)

        # Optimistic: base uplift augmented by HR-driven execution confidence
        hr_uplift = _GAMMA_0 * self.delta_air * hr_factor * 100
        self.optimistic_pct = round(self.base_pct + hr_uplift, 2)

        # Risk-adjusted: base case discounted by execution risk
        execution_risk = _GAMMA_3 * (1.0 - hr_factor)
        self.risk_adjusted_pct = round(self.base_pct * (1.0 - execution_risk), 2)

        # Flag for HITL when projected upside is material
        self.requires_approval = self.optimistic_pct > _HITL_THRESHOLD_PCT


class EBITDAProjector:
    def project(
        self,
        company_id: str,
        entry_score: float,
        target_score: float,
        h_r_score: float,
    ) -> Projection:
        return Projection(entry_score, target_score, h_r_score)


ebitda_calculator = EBITDAProjector()
