from dataclasses import dataclass
from typing import Dict, List, Tuple
from enum import Enum
from decimal import Decimal


class ScoreLevel(Enum):
    """5-level maturity scale."""
    LEVEL_5 = (80, 100, "Excellent")
    LEVEL_4 = (60, 79, "Good")
    LEVEL_3 = (40, 59, "Adequate")
    LEVEL_2 = (20, 39, "Developing")
    LEVEL_1 = (0, 19, "Nascent")

    @property
    def min_score(self) -> int:
        return self.value[0]

    @property
    def max_score(self) -> int:
        return self.value[1]


@dataclass
class RubricCriteria:
    """Criteria for a single rubric level."""
    level: ScoreLevel
    keywords: List[str]
    min_keyword_matches: int
    quantitative_threshold: float


@dataclass
class RubricResult:
    """Result of rubric scoring."""
    dimension: str
    level: ScoreLevel
    score: Decimal
    matched_keywords: List[str]
    keyword_match_count: int
    confidence: Decimal
    rationale: str


# Rubric definitions from Lab 5 PDF
DIMENSION_RUBRICS: Dict[str, Dict[ScoreLevel, RubricCriteria]] = {
    "talent": {
        ScoreLevel.LEVEL_5: RubricCriteria(
            level=ScoreLevel.LEVEL_5,
            keywords=["ml platform", "ai research", "large team", ">20 specialists",
                     "ai leadership", "principal ml", "staff ml"],
            min_keyword_matches=3,
            quantitative_threshold=0.40
        ),
        ScoreLevel.LEVEL_4: RubricCriteria(
            level=ScoreLevel.LEVEL_4,
            keywords=["data science team", "ml engineers", "10-20",
                     "active hiring", "retention"],
            min_keyword_matches=2,
            quantitative_threshold=0.25
        ),
        ScoreLevel.LEVEL_3: RubricCriteria(
            level=ScoreLevel.LEVEL_3,
            keywords=["data scientist", "growing team"],
            min_keyword_matches=1,
            quantitative_threshold=0.15
        ),
        ScoreLevel.LEVEL_2: RubricCriteria(
            level=ScoreLevel.LEVEL_2,
            keywords=["junior", "contractor", "turnover"],
            min_keyword_matches=1,
            quantitative_threshold=0.05
        ),
        ScoreLevel.LEVEL_1: RubricCriteria(
            level=ScoreLevel.LEVEL_1,
            keywords=["no data scientist", "vendor only"],
            min_keyword_matches=0,
            quantitative_threshold=0.0
        ),
    },
    
    "technology_stack": {
        ScoreLevel.LEVEL_5: RubricCriteria(
            level=ScoreLevel.LEVEL_5,
            keywords=["sagemaker", "mlops", "feature store"],
            min_keyword_matches=2,
            quantitative_threshold=0.30
        ),
        ScoreLevel.LEVEL_4: RubricCriteria(
            level=ScoreLevel.LEVEL_4,
            keywords=["mlflow", "kubeflow", "databricks ml"],
            min_keyword_matches=2,
            quantitative_threshold=0.20
        ),
        ScoreLevel.LEVEL_3: RubricCriteria(
            level=ScoreLevel.LEVEL_3,
            keywords=["jupyter", "notebooks", "manual deploy"],
            min_keyword_matches=1,
            quantitative_threshold=0.10
        ),
        ScoreLevel.LEVEL_2: RubricCriteria(
            level=ScoreLevel.LEVEL_2,
            keywords=["excel", "tableau only", "no ml"],
            min_keyword_matches=1,
            quantitative_threshold=0.05
        ),
        ScoreLevel.LEVEL_1: RubricCriteria(
            level=ScoreLevel.LEVEL_1,
            keywords=["manual", "no tools"],
            min_keyword_matches=0,
            quantitative_threshold=0.0
        ),
    },
    
    "data_infrastructure": {
        ScoreLevel.LEVEL_5: RubricCriteria(
            level=ScoreLevel.LEVEL_5,
            keywords=["snowflake", "databricks", "lakehouse", "real-time"],
            min_keyword_matches=3,
            quantitative_threshold=0.40
        ),
        ScoreLevel.LEVEL_4: RubricCriteria(
            level=ScoreLevel.LEVEL_4,
            keywords=["azure", "aws", "warehouse", "etl"],
            min_keyword_matches=2,
            quantitative_threshold=0.25
        ),
        ScoreLevel.LEVEL_3: RubricCriteria(
            level=ScoreLevel.LEVEL_3,
            keywords=["migration", "hybrid", "modernizing"],
            min_keyword_matches=1,
            quantitative_threshold=0.15
        ),
        ScoreLevel.LEVEL_2: RubricCriteria(
            level=ScoreLevel.LEVEL_2,
            keywords=["legacy", "silos", "on-premise"],
            min_keyword_matches=1,
            quantitative_threshold=0.05
        ),
        ScoreLevel.LEVEL_1: RubricCriteria(
            level=ScoreLevel.LEVEL_1,
            keywords=["mainframe", "spreadsheets", "manual"],
            min_keyword_matches=0,
            quantitative_threshold=0.0
        ),
    },
    
    "ai_governance": {
        ScoreLevel.LEVEL_5: RubricCriteria(
            level=ScoreLevel.LEVEL_5,
            keywords=["caio", "cdo", "board committee", "model risk"],
            min_keyword_matches=3,
            quantitative_threshold=0.40
        ),
        ScoreLevel.LEVEL_4: RubricCriteria(
            level=ScoreLevel.LEVEL_4,
            keywords=["vp data", "ai policy", "risk framework"],
            min_keyword_matches=2,
            quantitative_threshold=0.25
        ),
        ScoreLevel.LEVEL_3: RubricCriteria(
            level=ScoreLevel.LEVEL_3,
            keywords=["director", "guidelines", "it governance"],
            min_keyword_matches=1,
            quantitative_threshold=0.15
        ),
        ScoreLevel.LEVEL_2: RubricCriteria(
            level=ScoreLevel.LEVEL_2,
            keywords=["informal", "no policy", "ad-hoc"],
            min_keyword_matches=1,
            quantitative_threshold=0.05
        ),
        ScoreLevel.LEVEL_1: RubricCriteria(
            level=ScoreLevel.LEVEL_1,
            keywords=["none", "no oversight", "unmanaged"],
            min_keyword_matches=0,
            quantitative_threshold=0.0
        ),
    },
    
    "leadership": {
        ScoreLevel.LEVEL_5: RubricCriteria(
            level=ScoreLevel.LEVEL_5,
            keywords=["ceo ai", "board committee", "ai strategy"],
            min_keyword_matches=2,
            quantitative_threshold=0.30
        ),
        ScoreLevel.LEVEL_4: RubricCriteria(
            level=ScoreLevel.LEVEL_4,
            keywords=["cto ai", "strategic priority"],
            min_keyword_matches=2,
            quantitative_threshold=0.20
        ),
        ScoreLevel.LEVEL_3: RubricCriteria(
            level=ScoreLevel.LEVEL_3,
            keywords=["vp sponsor", "department initiative"],
            min_keyword_matches=1,
            quantitative_threshold=0.10
        ),
        ScoreLevel.LEVEL_2: RubricCriteria(
            level=ScoreLevel.LEVEL_2,
            keywords=["it led", "limited awareness"],
            min_keyword_matches=1,
            quantitative_threshold=0.05
        ),
        ScoreLevel.LEVEL_1: RubricCriteria(
            level=ScoreLevel.LEVEL_1,
            keywords=["no sponsor", "not discussed"],
            min_keyword_matches=0,
            quantitative_threshold=0.0
        ),
    },
    
    "use_case_portfolio": {
        ScoreLevel.LEVEL_5: RubricCriteria(
            level=ScoreLevel.LEVEL_5,
            keywords=["production ai", "3x roi", "ai product", "h100", "cuda", "nvidia dgx", "accelerated computing"],
            min_keyword_matches=2,
            quantitative_threshold=0.30
        ),
        ScoreLevel.LEVEL_4: RubricCriteria(
            level=ScoreLevel.LEVEL_4,
            keywords=["production", "measured roi", "scaling", "gpu cluster", "ai factory"],
            min_keyword_matches=2,
            quantitative_threshold=0.20
        ),
        ScoreLevel.LEVEL_3: RubricCriteria(
            level=ScoreLevel.LEVEL_3,
            keywords=["pilot", "early production", "inference"],
            min_keyword_matches=1,
            quantitative_threshold=0.10
        ),
        ScoreLevel.LEVEL_2: RubricCriteria(
            level=ScoreLevel.LEVEL_2,
            keywords=["poc", "proof of concept"],
            min_keyword_matches=1,
            quantitative_threshold=0.05
        ),
        ScoreLevel.LEVEL_1: RubricCriteria(
            level=ScoreLevel.LEVEL_1,
            keywords=["exploring", "no use cases"],
            min_keyword_matches=0,
            quantitative_threshold=0.0
        ),
    },
    
    "culture": {
        ScoreLevel.LEVEL_5: RubricCriteria(
            level=ScoreLevel.LEVEL_5,
            keywords=["innovative", "data-driven", "fail-fast"],
            min_keyword_matches=2,
            quantitative_threshold=0.30
        ),
        ScoreLevel.LEVEL_4: RubricCriteria(
            level=ScoreLevel.LEVEL_4,
            keywords=["experimental", "learning culture"],
            min_keyword_matches=2,
            quantitative_threshold=0.20
        ),
        ScoreLevel.LEVEL_3: RubricCriteria(
            level=ScoreLevel.LEVEL_3,
            keywords=["open to change", "some resistance"],
            min_keyword_matches=1,
            quantitative_threshold=0.10
        ),
        ScoreLevel.LEVEL_2: RubricCriteria(
            level=ScoreLevel.LEVEL_2,
            keywords=["bureaucratic", "resistant", "slow"],
            min_keyword_matches=1,
            quantitative_threshold=0.05
        ),
        ScoreLevel.LEVEL_1: RubricCriteria(
            level=ScoreLevel.LEVEL_1,
            keywords=["hostile", "siloed", "no data culture"],
            min_keyword_matches=0,
            quantitative_threshold=0.0
        ),
    },
}


class RubricScorer:
    """Score evidence against PE Org-AI-R rubrics."""

    def __init__(self):
        self.rubrics = DIMENSION_RUBRICS

    def score_dimension(
        self,
        dimension: str,
        evidence_text: str,
        quantitative_metrics: Dict[str, float],
    ) -> RubricResult:
        """
        Score a dimension using rubric matching.
        
        Algorithm:
        1. Normalize evidence text (lowercase)
        2. For each level (5 down to 1):
            a. Count keyword matches
            b. Check quantitative threshold
            c. If criteria met, return score in that level's range
        3. Use keyword density to interpolate within range
        """
        text = evidence_text.lower()
        rubric = self.rubrics.get(dimension, {})
        
        if not rubric:
            raise NotImplementedError(f"Rubric not defined for dimension: {dimension}")
        
        # Check each level from 5 to 1
        for level in [ScoreLevel.LEVEL_5, ScoreLevel.LEVEL_4, ScoreLevel.LEVEL_3, 
                      ScoreLevel.LEVEL_2, ScoreLevel.LEVEL_1]:
            criteria = rubric.get(level)
            if not criteria:
                continue
            
            # Count keyword matches
            matches = [kw for kw in criteria.keywords if kw in text]
            
            # Check if criteria met
            if len(matches) >= criteria.min_keyword_matches:
                # Interpolate score within level range
                keyword_density = len(matches) / max(len(criteria.keywords), 1)
                range_size = criteria.level.max_score - criteria.level.min_score
                score = criteria.level.min_score + (keyword_density * range_size)
                score = max(Decimal("10.0"), Decimal(str(round(score, 2))))
                
                return RubricResult(
                    dimension=dimension,
                    level=level,
                    score=score,
                    matched_keywords=matches,
                    keyword_match_count=len(matches),
                    confidence=Decimal(str(min(0.9, 0.5 + keyword_density * 0.4))),
                    rationale=f"Matched {len(matches)} keywords: {', '.join(matches[:3])}"
                )
        
        # Default to LEVEL_1 if no criteria met
        return RubricResult(
            dimension=dimension,
            level=ScoreLevel.LEVEL_1,
            score=Decimal("10.0"),
            matched_keywords=[],
            keyword_match_count=0,
            confidence=Decimal("0.3"),
            rationale="No rubric criteria met"
        )

    def score_all_dimensions(
        self,
        evidence_by_dimension: Dict[str, str],
        metrics_by_dimension: Dict[str, Dict[str, float]],
    ) -> Dict[str, RubricResult]:
        """Score all 7 dimensions."""
        results = {}
        
        for dimension in DIMENSION_RUBRICS.keys():
            evidence = evidence_by_dimension.get(dimension, "")
            metrics = metrics_by_dimension.get(dimension, {})
            results[dimension] = self.score_dimension(dimension, evidence, metrics)
        
        return results
