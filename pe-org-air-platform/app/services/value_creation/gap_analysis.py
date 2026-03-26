"""
Gap analysis engine — identifies dimension-level gaps between current scores
and a target Org-AI-R and maps each gap to actionable 100-day initiatives.
"""

from typing import Dict, List

# Recommended 100-day actions per dimension when a gap is detected
_DIMENSION_PLAYBOOK: Dict[str, List[str]] = {
    "data_infrastructure": [
        "Audit existing data pipelines and document lineage gaps",
        "Stand up a centralised feature store (e.g. Feast or Tecton)",
        "Implement data quality checks and SLA monitoring",
    ],
    "ai_governance": [
        "Draft an AI model risk policy and get board sign-off",
        "Appoint an AI governance lead or committee",
        "Deploy model cards and bias-testing for all production models",
    ],
    "talent": [
        "Map current ML/AI skills against role benchmarks",
        "Initiate targeted upskilling programme for data engineering roles",
        "Open two senior ML engineer requisitions",
    ],
    "use_case_portfolio": [
        "Run a 2-day use-case discovery workshop with business unit heads",
        "Prioritise top 3 AI use cases by EBITDA impact and feasibility",
        "Assign owners and 90-day milestones to each priority use case",
    ],
    "technology_stack": [
        "Benchmark current stack against cloud-native AI tooling",
        "Migrate key batch workloads to a managed ML platform",
        "Evaluate and pilot an MLOps orchestration layer",
    ],
    "data_culture": [
        "Launch a company-wide data literacy programme",
        "Introduce data OKRs at team level",
        "Run monthly data office hours with executive sponsors",
    ],
    "innovation_velocity": [
        "Establish a lightweight AI experimentation process (2-week sprints)",
        "Track and publish internal AI experiment win/loss ratio",
        "Create a small innovation fund for bottom-up AI ideas",
    ],
    "leadership": [
        "Add AI fluency criteria to executive performance reviews",
        "Brief C-suite on competitor AI capabilities and maturity benchmarks",
        "Include AI roadmap in next board strategy presentation",
    ],
}

# Score threshold below which a dimension is considered a gap
_GAP_THRESHOLD = 60.0

# Minimum estimated investment bracket per gap priority tier
_INVESTMENT_BRACKETS = {
    "Critical": "$2M – $5M",
    "High":     "$500K – $2M",
    "Medium":   "$150K – $500K",
    "Low":      "$50K – $150K",
}


def _priority(gap_size: float) -> str:
    if gap_size >= 40:
        return "Critical"
    if gap_size >= 25:
        return "High"
    if gap_size >= 10:
        return "Medium"
    return "Low"


class GapAnalyzer:
    def analyze(
        self,
        company_id: str,
        current_scores: dict,
        target_org_air: float,
    ) -> dict:
        """
        Identify dimension gaps against target_org_air and return a structured
        value creation plan with prioritised initiatives.

        If current_scores is empty the analysis still runs — each dimension is
        assumed to sit at the minimum observable score (30) so the output
        represents the worst-case gap picture.
        """
        all_dims = list(_DIMENSION_PLAYBOOK.keys())

        gaps = []
        for dim in all_dims:
            current = float(current_scores.get(dim, 30.0))
            gap_size = max(0.0, target_org_air - current)
            # Only surface gaps where the dimension is meaningfully below target
            # and below the acceptable threshold
            if gap_size <= 0 or current >= _GAP_THRESHOLD:
                continue
            gaps.append({
                "dimension": dim,
                "current_score": round(current, 1),
                "target_score": round(target_org_air, 1),
                "gap": round(gap_size, 1),
                "priority": _priority(gap_size),
                "initiatives": _DIMENSION_PLAYBOOK.get(dim, []),
            })

        # Sort highest-gap first
        gaps.sort(key=lambda g: g["gap"], reverse=True)

        top_priority = gaps[0]["priority"] if gaps else "Low"
        estimated_investment = _INVESTMENT_BRACKETS.get(top_priority, "$100K – $500K")

        return {
            "company_id": company_id,
            "target_org_air": target_org_air,
            "gap_count": len(gaps),
            "gaps": gaps,
            "top_priority": top_priority,
            "estimated_investment": estimated_investment,
            "projected_ebitda_pct": round(len(gaps) * 0.5, 1),  # rough proxy
        }


gap_analyzer = GapAnalyzer()
