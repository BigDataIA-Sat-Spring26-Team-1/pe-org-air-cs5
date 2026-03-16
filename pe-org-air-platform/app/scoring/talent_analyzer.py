from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Any, Set, Optional
import math
import re
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class JobAnalysis:
    """Analysis of job postings for talent concentration."""
    total_ai_jobs: int
    senior_ai_jobs: int      # Principal, Staff, Director, VP level
    mid_ai_jobs: int         # Senior, Lead level
    entry_ai_jobs: int       # Junior, Associate, entry level
    unique_skills: Set[str]  # Distinct skills required

class TalentConcentrationCalculator:
    """
    Calculate talent concentration (key-person risk).
    
    Formula (Task 5.0e):
    TC = 0.4 * leadership_ratio + 
         0.3 * team_size_factor + 
         0.2 * skill_concentration + 
         0.1 * individual_mentions
    
    Formula for H^R:
    TalentRiskAdj = 1 - 0.15 * max(0, TC - 0.25)
    """
    
    SENIORITY_KEYWORDS = {
        "senior": ["principal", "staff", "director", "vp", "head", "chief", "executive"],
        "mid": ["senior", "lead", "manager", "architect"],
        "entry": ["junior", "associate", "entry", "intern", "analyst"]
    }
    
    # Dynamic tech-first role markers (Sector agnostic)
    AI_ROLE_KEYWORDS = [
        "machine learning", "ml engineer", "data scientist", "ai engineer",
        "artificial intelligence", "deep learning", "nlp", "computer vision",
        "software engineer", "developer", "programmer", "architect", "systems engineer",
        "data engineer", "ai scientist"
    ]

    # Expanded skill markers for maximum coverage
    AI_SKILL_KEYWORDS = [
        "python", "java", "scala", "r", "sql",
        "tensorflow", "pytorch", "keras", "scikit-learn",
        "spark", "hadoop", "kafka", "airflow",
        "aws", "azure", "gcp", "docker", "kubernetes",
        "nlp", "computer vision", "llm", "generative ai",
        "algorithm", "neural networks", "cuda", "pandas", "pytorch"
    ]

    def calculate_tc(
        self,
        job_analysis: JobAnalysis,
        glassdoor_individual_mentions: int = 0,
        glassdoor_review_count: int = 1
    ) -> Decimal:
        """
        Calculate talent concentration ratio.
        
        Args:
            job_analysis: Analysis object from analyze_job_postings
            glassdoor_individual_mentions: Count of reviews mentioning specific individual names/titles
            glassdoor_review_count: Total count of glassdoor reviews
        """
        
        # 1. Leadership Ratio (40%)
        if job_analysis.total_ai_jobs > 0:
            leadership_ratio = Decimal(job_analysis.senior_ai_jobs) / Decimal(job_analysis.total_ai_jobs)
        else:
            leadership_ratio = Decimal("0.5")  # Default neutrality

        # 2. Team Size Factor (30%)
        # team_size_factor = min(1.0, 1.0 / (total_ai_jobs ** 0.5 + 0.1))
        total_jobs = Decimal(str(job_analysis.total_ai_jobs))
        team_size_denominator = Decimal(str(math.sqrt(float(total_jobs)) + 0.1)) if total_jobs > 0 else Decimal("0.1")
        team_size_factor = min(Decimal("1.0"), Decimal("1.0") / team_size_denominator)

        # 3. Skill Concentration (20%)
        # skill_concentration = max(0, 1 - (unique_skills / 15))
        unique_skills_count = len(job_analysis.unique_skills)
        skill_concentration = max(Decimal("0"), Decimal("1.0") - (Decimal(str(unique_skills_count)) / Decimal("15.0")))
        skill_concentration = min(Decimal("1.0"), skill_concentration)

        # 4. Individual Mentions (10%)
        # individual_factor = individual_mentions / review_count
        if glassdoor_review_count > 0:
            individual_factor = min(Decimal("1.0"), Decimal(str(glassdoor_individual_mentions)) / Decimal(str(glassdoor_review_count)))
        else:
            individual_factor = Decimal("0.5")  # Default neutrality

        # Weighted combination
        tc = (
            Decimal("0.4") * leadership_ratio +
            Decimal("0.3") * team_size_factor +
            Decimal("0.2") * skill_concentration +
            Decimal("0.1") * individual_factor
        )
        
        final_tc = Decimal(str(max(0, min(1, tc)))).quantize(Decimal("0.0001"))
        
        logger.info(
            "talent_concentration_calculated",
            tc_final=float(final_tc),
            components={
                "leadership_ratio": float(leadership_ratio),
                "team_size_factor": float(team_size_factor),
                "skill_concentration": float(skill_concentration),
                "individual_factor": float(individual_factor)
            },
            raw_metrics={
                "total_ai_jobs": job_analysis.total_ai_jobs,
                "senior_jobs": job_analysis.senior_ai_jobs,
                "unique_skills": len(job_analysis.unique_skills),
                "glassdoor_mentions": glassdoor_individual_mentions
            }
        )
        
        return final_tc

    def analyze_job_postings(self, postings: List[Dict]) -> JobAnalysis:
        """
        Categorize job postings by level and extract tech skills.
        Expected format for postings: [{'title': str, 'description': str}]
        """
        analysis = JobAnalysis(
            total_ai_jobs=0,
            senior_ai_jobs=0,
            mid_ai_jobs=0,
            entry_ai_jobs=0,
            unique_skills=set()
        )
        
        for job in postings:
            title = str(job.get("title", "") or "").lower()
            desc = str(job.get("description", "") or "").lower()
            
            # Check if role matches AI/Tech taxonomy
            is_tech_role = any(kw in title or kw in desc for kw in self.AI_ROLE_KEYWORDS)
            if not is_tech_role:
                continue
                
            analysis.total_ai_jobs += 1
            
            # Determine Seniority
            if any(kw in title for kw in self.SENIORITY_KEYWORDS["senior"]):
                analysis.senior_ai_jobs += 1
            elif any(kw in title for kw in self.SENIORITY_KEYWORDS["entry"]):
                analysis.entry_ai_jobs += 1
            else:
                analysis.mid_ai_jobs += 1  # Default to mid (Senior/Lead) if unspecified

            # Extract Skills
            for skill in self.AI_SKILL_KEYWORDS:
                if skill in desc or skill in title:
                    analysis.unique_skills.add(skill)
                    
        return analysis

    def analyze_glassdoor_reviews(self, reviews: List[Dict]) -> Dict[str, int]:
        """
        Analyze Glassdoor reviews for individual mentions and sentiment.
        Returns: {'individual_mentions': int, 'total_reviews': int}
        """
        mention_keywords = ["ceo", "cto", "cfo", "manager", "supervisor", "lead", "head of", "director"]
        mention_count = 0
        
        for r in reviews:
            text = (str(r.get("title", "")) + " " + str(r.get("review_text", ""))).lower()
            if any(kw in text for kw in mention_keywords):
                mention_count += 1
                
        return {
            "individual_mentions": mention_count,
            "total_reviews": len(reviews)
        }

    @classmethod
    async def get_company_talent_risk(cls, company_id: str, db_service) -> Dict[str, Any]:
        """
        Complete API flow: Fetches data from Snowflake and calculates Talent Concentration.
        This provides a dynamic assessment based on the latest scraped signals.
        """
        analyzer = cls()
        
        # 1. Fetch Job Descriptions from Snowflake (Hiring Pipeline)
        job_list = await db_service.fetch_job_descriptions_for_talent(company_id)
        
        # 2. Analyze Jobs
        job_analysis = analyzer.analyze_job_postings(job_list)
        
        # 3. Fetch Glassdoor Reviews from Snowflake (Signal Pipeline)
        reviews = await db_service.fetch_glassdoor_reviews_for_talent(company_id)
        
        # 4. Analyze Reviews for individual mentions
        review_analysis = analyzer.analyze_glassdoor_reviews(reviews)
        
        # 5. Calculate Final TC Score using Case Study Logic
        tc_score = analyzer.calculate_tc(
            job_analysis,
            glassdoor_individual_mentions=review_analysis['individual_mentions'],
            glassdoor_review_count=review_analysis['total_reviews']
        )
        
        # 6. Calculate TalentRiskAdj for H^R formula
        risk_adj = analyzer.calculate_talent_risk_adj(tc_score)
        
        return {
            "company_id": company_id,
            "talent_concentration_score": float(tc_score),
            "talent_risk_adjustment": float(risk_adj),
            "breakdown": {
                "total_ai_jobs": job_analysis.total_ai_jobs,
                "senior_jobs": job_analysis.senior_ai_jobs,
                "mid_jobs": job_analysis.mid_ai_jobs,
                "entry_jobs": job_analysis.entry_ai_jobs,
                "unique_skills_count": len(job_analysis.unique_skills),
                "unique_skills": sorted(list(job_analysis.unique_skills)),
                "glassdoor_mentions": review_analysis['individual_mentions'],
                "glassdoor_reviews": review_analysis['total_reviews']
            }
        }

    def calculate_talent_risk_adj(self, tc: Decimal) -> Decimal:
        """
        Calculate TalentRiskAdj factor for Horizontal Readiness.
        TalentRiskAdj = 1 - 0.15 * max(0, TC - 0.25)
        """
        penalty_range = max(Decimal("0"), tc - Decimal("0.25"))
        adj = Decimal("1.0") - (Decimal("0.15") * penalty_range)
        return round(adj, 4)
