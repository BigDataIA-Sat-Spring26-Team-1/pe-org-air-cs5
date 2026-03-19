# Mock EBITDA Calculator for Case Study 5 compatibility

class Projection:
    def __init__(self, e, x, h):
        self.delta_air = x - e
        self.base_pct = 3.5
        self.conservative_pct = 2.0
        self.optimistic_pct = 5.0
        self.risk_adjusted_pct = 3.0
        self.requires_approval = False

class EBITDAProjector:
    def project(self, company_id: str, entry_score: float, exit_score: float, h_r_score: float):
        return Projection(entry_score, exit_score, h_r_score)

ebitda_calculator = EBITDAProjector()
