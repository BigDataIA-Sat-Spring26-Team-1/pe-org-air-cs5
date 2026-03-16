
import pytest
from decimal import Decimal
from app.scoring.rubric_scorer import RubricScorer, ScoreLevel

def test_talent_high_maturity():
    scorer = RubricScorer()
    # Need 3 key matches for Level 5
    evidence = "Our ML platform is led by ai leadership and several staff ml engineers."
    metrics = {"talent": 0.50}
    
    result = scorer.score_dimension("talent", evidence, metrics)
    assert result.level == ScoreLevel.LEVEL_5
    assert result.score >= 80

def test_nascent_score_minimum():
    scorer = RubricScorer()
    evidence = "Initial exploration phase."
    metrics = {"talent": 0.0}
    
    result = scorer.score_dimension("talent", evidence, metrics)
    assert float(result.score) >= 10.0

def test_bulk_dimension_scoring():
    scorer = RubricScorer()
    dims = list(scorer.rubrics.keys())
    evidence = {d: "general progress" for d in dims}
    metrics = {d: {"value": 0.5} for d in dims}
    
    results = scorer.score_all_dimensions(evidence, metrics)
    assert len(results) == len(dims)
    for res in results.values():
        assert float(res.score) >= 10.0
