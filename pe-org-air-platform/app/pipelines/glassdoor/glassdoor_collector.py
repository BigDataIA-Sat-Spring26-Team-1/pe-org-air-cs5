import asyncio
import json
import logging
import re
import httpx
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Optional

from app.config import settings
from app.models.glassdoor_models import GlassdoorReview, CultureSignal

logger = logging.getLogger(__name__)

# --- Constants ---

COMPANY_IDS = {
    "NVDA": "7633",
    "JPM": "5224839",
    "WMT": "715",
    "GE": "277",
    "DG": "1342"
}

WEXTRACTOR_URL = "https://wextractor.com/api/v1/reviews/glassdoor"

# --- RubricScorer Class ---

from enum import Enum
from dataclasses import dataclass, field

class ScoreLevel(Enum):
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5

@dataclass
class RubricCriteria:
    level: ScoreLevel
    keywords: List[str] = field(default_factory=list)
    min_keyword_matches: int = 0
    quantitative_threshold: Optional[Decimal] = None


def _stem_match(keyword: str, text: str) -> bool:
    """
    Match a keyword in text using stem-aware word-boundary matching.
    
    Strategy:
    1. Try exact substring first (fast path for multi-word phrases)
    2. For single words >= 5 chars, try stem matching by trimming suffix
       e.g. "analytical" stem "analyt" matches "analysis", "analytics", "analyze"
    3. For short words or phrases, only do exact match
    """
    # Fast path: exact substring
    if keyword in text:
        return True
    
    # Stem matching for single words that are long enough
    words = keyword.split()
    if len(words) == 1 and len(keyword) >= 5:
        # Create stem by keeping at least 4 chars, trimming up to 3 suffix chars
        stem_len = max(4, len(keyword) - 3)
        stem = keyword[:stem_len]
        # Word-boundary match: stem followed by optional word chars
        pattern = r'\b' + re.escape(stem) + r'\w*\b'
        if re.search(pattern, text):
            return True
    
    return False


class RubricScorer:
    # SCORING_KEYWORDS: Expanded with colloquial synonyms that real employees
    # use in Glassdoor reviews. The original technical terms are preserved;
    # new additions bridge the vocabulary gap between curated keywords and
    # casual review language.
    SCORING_KEYWORDS = {
        "innovation": {
            "positive": [
                # Original technical terms
                "innovative", "cutting-edge", "forward-thinking",
                "encourages new ideas", "experimental", "creative freedom",
                "startup mentality", "move fast", "disruptive",
                # Colloquial additions - how employees actually talk
                "new technology", "open to ideas", "think outside the box",
                "try new things", "modern", "tech-savvy", "evolving",
                "pioneering", "creative", "fresh ideas", "encouraged to innovate",
                "bleeding edge", "state of the art", "leading edge",
                "pushing boundaries", "ahead of the curve", "trailblazing",
                "invention", "r&d", "research and development",
                "hackathon", "innovation lab"
            ],
            "negative": [
                # Original
                "bureaucratic", "slow to change", "resistant",
                "outdated", "stuck in old ways", "red tape",
                "politics", "siloed", "hierarchical",
                # Colloquial additions
                "old fashioned", "micromanagement", "corporate",
                "stagnant", "no innovation", "legacy", "behind the times",
                "dinosaur", "archaic", "old-school", "dated"
            ]
        },
        "data_driven": {
            "positive": [
                # Original technical terms
                "data-driven", "metrics", "evidence-based",
                "analytical", "kpis", "dashboards", "data culture",
                "measurement", "quantitative",
                # Colloquial additions - how employees describe data usage
                "numbers", "tracked", "reporting", "analytics",
                "performance review", "goals", "targets",
                "accountability", "results-oriented", "insights",
                "transparency", "data", "facts", "objective",
                "statistics", "reports", "measure results",
                "performance metrics", "scorecards", "benchmarks",
                "data analysis", "business intelligence", "bi tools",
                "tableau", "power bi", "excel", "spreadsheet",
                # Ground-level terms (banking/retail employee language)
                "training", "expectations", "monitor", "feedback",
                "evaluation", "standards", "quota", "productivity",
                "efficiency", "tracking", "score", "rating",
                "graded", "assessed", "reviewed", "audit",
                "compliance", "process", "documented", "systematic"
            ],
            "negative": []
        },
        "ai_awareness": {
            "positive": [
                # Original technical terms
                "ai", "artificial intelligence", "machine learning",
                "automation", "data science", "ml", "algorithms",
                "predictive", "neural network",
                # Colloquial additions - how employees talk about AI/tech
                "automated", "chatbot", "tech-forward",
                "digital transformation", "intelligent", "deep learning",
                "nlp", "computer vision", "robotics", "smart systems",
                "natural language", "generative ai", "gpt", "copilot",
                "model training", "data pipeline", "data engineering",
                "cloud computing", "aws", "azure", "tensorflow",
                "pytorch", "big data", "advanced analytics"
            ],
            "negative": []
        },
        "change_readiness": {
            "positive": [
                # Original
                "agile", "adaptive", "fast-paced", "embraces change",
                "continuous improvement", "growth mindset",
                # Colloquial additions
                "flexible", "open-minded", "willing to learn",
                "evolving", "modern approach", "progressive",
                "dynamic", "forward-looking", "constantly improving",
                "lean", "iterative", "quick to adapt", "nimble",
                "open to feedback", "learning culture", "receptive",
                "collaborative", "cross-functional"
            ],
            "negative": [
                # Original
                "rigid", "traditional", "slow", "risk-averse",
                "change resistant", "old school",
                # Colloquial additions
                "resistant to change", "set in their ways",
                "bureaucracy", "red tape heavy", "inflexible",
                "stagnant", "won't change", "afraid of change",
                "stuck", "complacent", "status quo", "no growth"
            ]
        }
    }

    # DIMENSION_RUBRICS: The Level 1-5 structure required by blueprint
    # Populated with representative criteria to satisfy class design
    DIMENSION_RUBRICS = {
        "innovation": [
            RubricCriteria(level=ScoreLevel.ONE, keywords=["bureaucratic", "slow to change", "stuck in old ways"], min_keyword_matches=1, quantitative_threshold=Decimal(20)),
            RubricCriteria(level=ScoreLevel.TWO, keywords=["hierarchical", "red tape", "politics"], min_keyword_matches=1, quantitative_threshold=Decimal(40)),
            RubricCriteria(level=ScoreLevel.THREE, keywords=["encourages new ideas", "creative freedom"], min_keyword_matches=1, quantitative_threshold=Decimal(60)),
            RubricCriteria(level=ScoreLevel.FOUR, keywords=["innovative", "forward-thinking", "startup mentality"], min_keyword_matches=2, quantitative_threshold=Decimal(80)),
            RubricCriteria(level=ScoreLevel.FIVE, keywords=["disruptive", "cutting-edge", "experimental", "move fast"], min_keyword_matches=3, quantitative_threshold=Decimal(90)),
        ],
        "data_driven": [
            RubricCriteria(level=ScoreLevel.ONE, keywords=[], min_keyword_matches=0, quantitative_threshold=Decimal(0)),
            RubricCriteria(level=ScoreLevel.TWO, keywords=["measurement", "quantitative"], min_keyword_matches=1, quantitative_threshold=Decimal(25)),
            RubricCriteria(level=ScoreLevel.THREE, keywords=["data-driven", "metrics", "kpis"], min_keyword_matches=2, quantitative_threshold=Decimal(50)),
            RubricCriteria(level=ScoreLevel.FOUR, keywords=["analytical", "dashboards", "evidence-based"], min_keyword_matches=3, quantitative_threshold=Decimal(75)),
            RubricCriteria(level=ScoreLevel.FIVE, keywords=["data culture"], min_keyword_matches=4, quantitative_threshold=Decimal(90)),
        ],
        "ai_awareness": [
            RubricCriteria(level=ScoreLevel.ONE, keywords=[], min_keyword_matches=0, quantitative_threshold=Decimal(0)),
            RubricCriteria(level=ScoreLevel.TWO, keywords=["automation"], min_keyword_matches=1, quantitative_threshold=Decimal(25)),
            RubricCriteria(level=ScoreLevel.THREE, keywords=["data science", "algorithms", "predictive"], min_keyword_matches=2, quantitative_threshold=Decimal(50)),
            RubricCriteria(level=ScoreLevel.FOUR, keywords=["machine learning", "ml", "neural network"], min_keyword_matches=3, quantitative_threshold=Decimal(75)),
            RubricCriteria(level=ScoreLevel.FIVE, keywords=["ai", "artificial intelligence"], min_keyword_matches=4, quantitative_threshold=Decimal(90)),
        ],
        "change_readiness": [
            RubricCriteria(level=ScoreLevel.ONE, keywords=["rigid", "slow", "old school"], min_keyword_matches=1, quantitative_threshold=Decimal(20)),
            RubricCriteria(level=ScoreLevel.TWO, keywords=["traditional", "risk-averse", "change resistant"], min_keyword_matches=1, quantitative_threshold=Decimal(40)),
            RubricCriteria(level=ScoreLevel.THREE, keywords=["adaptive", "growth mindset"], min_keyword_matches=1, quantitative_threshold=Decimal(60)),
            RubricCriteria(level=ScoreLevel.FOUR, keywords=["agile", "continuous improvement"], min_keyword_matches=2, quantitative_threshold=Decimal(80)),
            RubricCriteria(level=ScoreLevel.FIVE, keywords=["fast-paced", "embraces change"], min_keyword_matches=3, quantitative_threshold=Decimal(90)),
        ]
    }
    
    def get_evidence_keywords(self, reviews: List[GlassdoorReview]) -> tuple[List[str], List[str]]:
        """Helper to extract found keywords for evidence using stem matching."""
        found_pos = set()
        found_neg = set()
        
        all_text = " ".join([((r.pros or "") + " " + (r.cons or "")).lower() for r in reviews])
        
        for config in self.SCORING_KEYWORDS.values():
            for k in config["positive"]:
                if _stem_match(k, all_text):
                    found_pos.add(k)
            for k in config["negative"]:
                if _stem_match(k, all_text):
                    found_neg.add(k)
                    
        return list(found_pos), list(found_neg)


class GlassdoorCultureCollector:
    def __init__(self):
        self.api_key = settings.WEXTRACTOR_API_KEY.get_secret_value() if settings.WEXTRACTOR_API_KEY else None
        self.scorer = RubricScorer()
        
        if not self.api_key or self.api_key == "dummy_key":
            logger.warning("WEXTRACTOR_API_KEY is not set or is dummy. Collector will fail.")

    async def fetch_reviews(self, ticker: str, limit: int = 100) -> List[GlassdoorReview]:
        """
        Fetch raw reviews from Glassdoor (or cached data), parse them, and return objects.
        Handles S3 caching of raw JSON internally.
        """
        glassdoor_id = COMPANY_IDS.get(ticker)
        if not glassdoor_id:
            logger.error(f"No Glassdoor ID found for ticker {ticker}.")
            return []

        # 1. Check S3 for existing data for today
        date_str = datetime.now().strftime("%Y-%m-%d")
        s3_key = f"raw/glassdoor/{ticker}/{date_str}.json"
        
        # Late import to avoid circular dependency if needed, though usually safe here
        from app.services.s3_storage import aws_service

        raw_reviews = None
        if aws_service.file_exists(s3_key):
             logger.info(f"Found existing raw data for {ticker} in S3: {s3_key}")
             raw_reviews = aws_service.read_json(s3_key)

        if not raw_reviews:
            # Fetch from API
            params = {
                "id": glassdoor_id,
                "auth_token": self.api_key,
                "limit": limit,
                "language": "en"
            }
            
            all_reviews = []
            
            async with httpx.AsyncClient() as client:
                try:
                    # Simple fetch for now, can add pagination loop if needed for >10 reviews
                    # But request limit is 100 usually max.
                    # Re-implementing the loop from before:
                    fetched_count = 0
                    current_offset = 0
                    
                    while fetched_count < limit:
                        params["offset"] = current_offset
                        logger.info(f"Fetching Glassdoor reviews for {ticker} (ID: {glassdoor_id}), offset={current_offset}")
                        
                        response = await client.get(WEXTRACTOR_URL, params=params, timeout=30.0)
                        response.raise_for_status()
                        data = response.json()
                        
                        reviews = data.get("reviews", [])
                        if not reviews:
                            break
                            
                        all_reviews.extend(reviews)
                        fetched_count += len(reviews)
                        current_offset += len(reviews)
                        
                        await asyncio.sleep(0.5)
                        if len(reviews) < 10: # API page size often small
                            break
                except Exception as e:
                     logger.error(f"Error fetching from Wextractor: {e}")
                     return []
            
            raw_reviews = all_reviews[:limit]
            
            # Save Raw to S3
            if raw_reviews:
                 success = aws_service.upload_bytes(
                    data=json.dumps(raw_reviews).encode('utf-8'),
                    s3_key=s3_key,
                    content_type="application/json"
                )
                 if success:
                     logger.info(f"Saved {len(raw_reviews)} raw reviews to S3: {s3_key}")

        # Parse Reviews
        parsed_reviews = [
            self.parse_review(r, ticker, glassdoor_id) 
            for r in raw_reviews
        ]
        
        return parsed_reviews

    def parse_review(self, raw: Dict, ticker: str, company_id: str) -> GlassdoorReview:
        """
        Parse a single raw review dictionary into a GlassdoorReview object.
        """
        # Date parsing
        try:
            rdate = datetime.fromisoformat(raw.get("datetime"))
        except:
            rdate = datetime.now()

        # Helper for ratings
        def parse_float(val):
            try:
                return float(val)
            except:
                return 0.0

        return GlassdoorReview(
            id=raw.get("id"),
            company_id=company_id,
            ticker=ticker,
            review_date=rdate,
            rating=parse_float(raw.get("rating")),
            title=raw.get("title"),
            pros=raw.get("pros"),
            cons=raw.get("cons"),
            advice_to_management=raw.get("advice"),
            is_current_employee=raw.get("is_current_job", False),
            job_title=raw.get("reviewer"),
            location=raw.get("location"),
            culture_rating=parse_float(raw.get("culture_and_values_rating")),
            diversity_rating=parse_float(raw.get("diversity_and_inclusion_rating")),
            work_life_rating=parse_float(raw.get("work_life_balance_rating")),
            senior_management_rating=parse_float(raw.get("senior_management_rating")),
            comp_benefits_rating=parse_float(raw.get("compensation_and_benefits_rating")),
            career_opp_rating=parse_float(raw.get("career_opportunities_rating")),
            recommend_to_friend=raw.get("rating_recommend_to_friend"),
            ceo_rating=raw.get("rating_ceo"),
            business_outlook=raw.get("rating_business_outlook"),
            raw_json=raw
        )

    def analyze_reviews(self, company_id: str, ticker: str, reviews: List[GlassdoorReview]) -> Optional[CultureSignal]:
        """
        Analyze reviews using Weighted Aggregation (Recency + Employee Status).
        """
        if not reviews:
            return None

        # 1. Calculate Weights & Weighted Counts
        # Algorithm:
        # Weight = recency_weight * employee_weight
        # - recency: < 730 days = 1.0, else 0.5
        # - employee: current = 1.2, else 1.0
        
        total_weight = Decimal(0)
        
        # We need to track weighted positive/negative counts for each dimension
        # dim -> {pos: 0.0, neg: 0.0, mentions: 0.0}
        dim_scores = {
            k: {"pos": Decimal(0), "neg": Decimal(0)} 
            for k in self.scorer.SCORING_KEYWORDS.keys()
        }
        
        today = datetime.now()
        
        for r in reviews:
            # Calculate Weight
            days_old = (today - r.review_date).days
            recency_weight = Decimal("1.0") if days_old < 730 else Decimal("0.5")
            
            employee_weight = Decimal("1.2") if r.is_current_employee else Decimal("1.0")
            
            weight = recency_weight * employee_weight
            total_weight += weight
            
            # Text Analysis
            text = ((r.pros or "") + " " + (r.cons or "")).lower()
            
            # Check keywords for each dimension (using stem-aware matching)
            for dim, config in self.scorer.SCORING_KEYWORDS.items():
                # Positive Matches
                for k in config["positive"]:
                    if _stem_match(k, text):
                        dim_scores[dim]["pos"] += weight
                
                # Negative Matches
                for k in config["negative"]:
                    if _stem_match(k, text):
                        dim_scores[dim]["neg"] += weight

        # 2. Calculate Component Scores
        final_scores = {}
        
        for dim, counts in dim_scores.items():
            if total_weight == 0:
                final_scores[dim] = Decimal(0)
                continue
                
            if dim in ["data_driven", "ai_awareness"]:
                # Formula: (Mentions / TotalWeight) * 100
                # "Mentions" here is strictly positive keywords for these dimensions
                raw = (counts["pos"] / total_weight) * Decimal(100)
            else:
                # Formula: ((Pos - Neg) / TotalWeight) * 50 + 50
                net = counts["pos"] - counts["neg"]
                raw = (net / total_weight) * Decimal(50) + Decimal(50)
            
            final_scores[dim] = max(Decimal(0), min(Decimal(100), raw))

        innov_final = final_scores["innovation"]
        change_final = final_scores["change_readiness"]
        data_final = final_scores["data_driven"]
        ai_final = final_scores["ai_awareness"]

        logger.debug(f"Culture Component Scores for {ticker}: "
                     f"Innov={innov_final}, Change={change_final}, "
                     f"Data={data_final}, AI={ai_final}")
        
        # 3. Calculate Overall Weighted Average
        # Weights: Innov 0.30, Data 0.25, AI 0.25, Change 0.20
        overall = (
            Decimal("0.30") * innov_final +
            Decimal("0.25") * data_final +
            Decimal("0.25") * ai_final +
            Decimal("0.20") * change_final
        )
        
        # Additional Metrics
        total_rating = sum(Decimal(r.rating) for r in reviews)
        avg_rating = total_rating / Decimal(len(reviews)) if reviews else Decimal(0)
        
        current_employees = sum(1 for r in reviews if r.is_current_employee)
        current_employee_ratio = Decimal(current_employees) / Decimal(len(reviews)) if reviews else Decimal(0)
        
        # Evidence (Unweighted list of found keywords)
        pos_keys, neg_keys = self.scorer.get_evidence_keywords(reviews)

        return CultureSignal(
            company_id=company_id,
            ticker=ticker,
            batch_date=date.today(),
            innovation_score=innov_final.quantize(Decimal("0.00")),
            data_driven_score=data_final.quantize(Decimal("0.00")),
            ai_awareness_score=ai_final.quantize(Decimal("0.00")),
            change_readiness_score=change_final.quantize(Decimal("0.00")),
            overall_sentiment=overall.quantize(Decimal("0.00")),
            review_count=len(reviews),
            avg_rating=avg_rating.quantize(Decimal("0.00")),
            current_employee_ratio=current_employee_ratio.quantize(Decimal("0.00")),
            positive_keywords_found=pos_keys,
            negative_keywords_found=neg_keys,
            confidence=Decimal("0.80")
        )
