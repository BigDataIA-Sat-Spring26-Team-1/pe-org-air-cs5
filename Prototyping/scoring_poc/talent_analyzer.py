from decimal import Decimal
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class TalentConcentrationCalculator:
    """
    Quantifies 'people risk' by analyzing the concentration of key technical 
    functions and individual mentions in reviews.
    """
    
    def calculate_concentration_score(
        self, 
        job_postings: List[Dict], 
        glassdoor_mentions: int, 
        total_reviews: int
    ) -> Decimal:
        """
        Calculates a score representing how concentrated key talent is.
        Higher Score = Higher Risk (Concentration).
        Scale: 0.0 (Low Risk/Distributed) to 1.0 (High Risk/Concentrated).
        """
        if not job_postings and total_reviews == 0:
            return Decimal("0.5") # Neutral default
            
        # 1. Job Posting Concentration
        # Logic: If a small number of job posts contain most of the AI/Tech keywords, concentration is high.
        # For this POC, we'll simulate 'AI keyword count' per post.
        
        post_weights = []
        for post in job_postings:
            # metadata should contain 'ai_keyword_count'
            kw_count = post.get("metadata", {}).get("ai_keyword_count", 0)
            post_weights.append(kw_count)
            
        total_kws = sum(post_weights)
        job_concentration = Decimal("0.0")
        
        if total_kws > 0:
            # If 20% of AI keywords appear in just 1 job post, that's high concentration.
            # Simplified: Gini-like measure or just check max ratio.
            max_kw_in_single_post = max(post_weights)
            ratio = Decimal(str(max_kw_in_single_post)) / Decimal(str(total_kws))
            
            # If ratio >= 0.2 in a single post -> start increasing risk
            if ratio >= Decimal("0.2"):
                job_concentration = min(Decimal("1.0"), ratio * Decimal("2")) # Heuristic
            else:
                job_concentration = ratio
                
        # 2. Individual Mentions Concentration (Key Person Dependency)
        # From Glassdoor: "Individual mentions" vs total reviews
        mention_risk = Decimal("0.0")
        if total_reviews > 0:
            mention_ratio = Decimal(str(glassdoor_mentions)) / Decimal(str(total_reviews))
            # If a specific name or "key person" is mentioned in > 5% of reviews, it's high risk
            mention_risk = min(Decimal("1.0"), mention_ratio * Decimal("10"))
            
        # Combine
        # Job concentration is a 'future' risk, Mentions is 'current' risk.
        final_risk = (job_concentration * Decimal("0.6")) + (mention_risk * Decimal("0.4"))
        
        return round(max(Decimal("0.0"), min(Decimal("1.0"), final_risk)), 2)
