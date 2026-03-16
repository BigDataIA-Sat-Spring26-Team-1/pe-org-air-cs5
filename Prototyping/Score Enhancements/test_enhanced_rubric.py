
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List

class ScoreLevel(Enum):
    LEVEL_5 = (80, 100, "Excellent")
    LEVEL_4 = (60, 79, "Good")
    LEVEL_3 = (40, 59, "Adequate")
    LEVEL_2 = (20, 39, "Developing")
    LEVEL_1 = (0, 19, "Nascent")

@dataclass
class RubricCriteria:
    level: ScoreLevel
    keywords: List[str]
    min_keyword_matches: int

class EnhancedRubricScorer:
    def __init__(self):
        # Base rubrics (existing)
        self.rubrics = {
            "use_case_portfolio": {
                ScoreLevel.LEVEL_5: RubricCriteria(ScoreLevel.LEVEL_5, ["production ai", "3x roi", "ai product", "h100", "cuda", "omni", "accelerated computing", "dgx"], 2),
                ScoreLevel.LEVEL_4: RubricCriteria(ScoreLevel.LEVEL_4, ["production", "measured roi", "scaling", "gpu infrastructure", "ai factory"], 2),
                ScoreLevel.LEVEL_3: RubricCriteria(ScoreLevel.LEVEL_3, ["pilot", "early production", "inference model"], 1),
                ScoreLevel.LEVEL_2: RubricCriteria(ScoreLevel.LEVEL_2, ["poc", "proof of concept"], 1),
                ScoreLevel.LEVEL_1: RubricCriteria(ScoreLevel.LEVEL_1, ["exploring", "no use cases"], 0),
            }
        }

    def score_dimension(self, dimension, text):
        text = text.lower()
        rubric = self.rubrics.get(dimension, {})
        
        for level in [ScoreLevel.LEVEL_5, ScoreLevel.LEVEL_4, ScoreLevel.LEVEL_3, ScoreLevel.LEVEL_2, ScoreLevel.LEVEL_1]:
            criteria = rubric[level]
            matches = [kw for kw in criteria.keywords if kw in text]
            
            if len(matches) >= criteria.min_keyword_matches:
                density = len(matches) / max(len(criteria.keywords), 1)
                range_size = level.value[1] - level.value[0]
                score = level.value[0] + (density * range_size)
                return {
                    "level": level.name,
                    "score": round(float(score), 2),
                    "matches": matches
                }
        return {"level": "LEVEL_1", "score": 10.0, "matches": []}

def run_test():
    scorer = EnhancedRubricScorer()
    
    # Mock SEC text for NVDA (simulating what an AI leader's filing looks like)
    nvda_text = """
    Our accelerated computing platform is the world leader in AI. 
    The H100 GPU and CUDA architecture are production standard. 
    NVIDIA DGX systems and Omniverse are scaling across industries.
    """
    
    # Mock SEC text for a smaller company
    dg_text = """
    We are exploring AI use cases and have completed a proof of concept (POC) 
    for inventory management.
    """

    print("NVDA Enhanced Score:")
    print(json.dumps(scorer.score_dimension("use_case_portfolio", nvda_text), indent=2))
    
    print("\nDG Enhanced Score:")
    print(json.dumps(scorer.score_dimension("use_case_portfolio", dg_text), indent=2))

if __name__ == "__main__":
    import json
    run_test()
