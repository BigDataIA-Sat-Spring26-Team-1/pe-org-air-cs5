from decimal import Decimal
from typing import Dict, List, Set, Optional
import math
import re
import pandas as pd

class TalentConcentrationCalculatorV2:
    """
    Enhanced Talent Concentration Calculator using Glassdoor + Snowflake data.
    
    Formula:
    TC = 0.4 * leadership_ratio (Glassdoor) + 
         0.3 * team_size_factor (Glassdoor Proxy) + 
         0.2 * skill_concentration (Snowflake) + 
         0.1 * individual_mentions (Glassdoor)
    """
    
    SENIORITY_KEYWORDS = {
        "senior": ["principal", "staff", "director", "vp", "head", "chief", "executive", "president", "vice president", "svp"],
        "mid": ["senior", "manager", "lead", "architect", "fellow"], 
        "entry": ["junior", "associate", "entry", "intern", "analyst", "i", "ii", "iii", "iv", "v"]
    }
    
    # Expanded based on deep analysis of Snowflake & Glassdoor data
    AI_ROLE_KEYWORDS = [
        # Core AI/Data
        "data scientist", "data engineer", "machine learning", "ml engineer", "ai engineer",
        "artificial intelligence", "deep learning", "computer vision", "nlp", "statistician",
        "quantitative", "quant", "math", "model", "algorithm",
        
        # Tech Engineering
        "software engineer", "developer", "programmer", "architect", "technical", 
        "systems engineer", "security engineer", "feature engineer",
        
        # Data/Analytics (Banking heavy)
        "data analyst", "business intelligence", "analytics", "operations analyst", "technology analyst"
    ]
    
    AI_SKILL_KEYWORDS = [
        "python", "java", "scala", "r", "sql",
        "tensorflow", "pytorch", "keras", "scikit-learn",
        "spark", "hadoop", "kafka", "airflow",
        "aws", "azure", "gcp", "docker", "kubernetes",
        "nlp", "computer vision", "llm", "generative ai",
        "analytics", "models", "capital markets", "strategic", "design", "algorithm" # From deep analysis
    ]

    def calculate_tc(
        self,
        reviews_df: pd.DataFrame,
        job_descriptions: List[str]
    ) -> Decimal:
        """
        Calculate talent concentration.
        
        CRITICAL CHANGE: We first filter reviews to only consider the AI/Tech workforce.
        Using the total reviews for a massive bank like JPM dilutes the risk metric.
        """
        if reviews_df.empty:
            return Decimal("0.5")

        # 0. Filter for AI/Tech Roles
        # We look for role keywords in the 'job' (title) column
        pattern = '|'.join(self.AI_ROLE_KEYWORDS)
        tech_reviews = reviews_df[reviews_df['job'].str.contains(pattern, case=False, na=False)].copy()
        
        tech_count = len(tech_reviews)
        if tech_count == 0:
            # If no tech reviews found, we can't assess concentration properly.
            # Defaulting to High Concentration (1.0) or specific fallback?
            # Let's return neutral 0.5 but log warning implicitly by the count
            print("  Warning: No AI/Tech reviews found for concentration analysis.")
            return Decimal("0.5")

        print(f"  Filtered {len(reviews_df)} total reviews down to {tech_count} AI/Tech reviews.")

        # 1. Leadership Ratio (Glassdoor - Tech Only)
        leadership_ratio = self._calculate_leadership_ratio(tech_reviews)
        
        # 2. Team Size Factor (Glassdoor Proxy - Tech Only)
        team_size_factor = self._calculate_team_size_factor(tech_reviews)
        
        # 3. Skill Concentration (Snowflake - Already Job Description based)
        skill_concentration, _ = self._calculate_skill_concentration(job_descriptions)
        
        # 4. Individual Mentions (Glassdoor - Tech Only)
        # We care about key person risk *within* the tech team
        individual_factor = self._calculate_individual_mention_factor(tech_reviews)
        
        # Weighted combination
        tc = (
            Decimal("0.4") * leadership_ratio +
            Decimal("0.3") * team_size_factor +
            Decimal("0.2") * skill_concentration +
            Decimal("0.1") * individual_factor
        )
        
        tc = max(Decimal("0"), min(Decimal("1"), tc))
        return round(tc, 4)

    def _calculate_leadership_ratio(self, df: pd.DataFrame) -> Decimal:
        """
        Calculate leadership ratio based on review job titles.
        ratio = senior_reviews / total_reviews
        """
        total = int(len(df))
        if total == 0:
            return Decimal("0.5")
            
        senior_pattern = '|'.join(self.SENIORITY_KEYWORDS["senior"])
        # Case insensitive match for senior titles
        senior_count = int(df['job'].str.contains(senior_pattern, case=False, na=False).sum())
        
        ratio = Decimal(senior_count) / Decimal(total)
        # Normalize: if ratio > 0.3 (30% leaders), that's high concentration? 
        # Or just use the raw ratio? The original used raw.
        return ratio

    def _calculate_team_size_factor(self, df: pd.DataFrame) -> Decimal:
        """
        Calculate team size factor using review volume as proxy.
        More reviews -> Larger team -> Lower concentration (factor -> 0).
        Fewer reviews -> Smaller team -> Higher concentration (factor -> 1).
        
        Formula: 1.0 / (sqrt(total_reviews) + 0.1)
        """
        total = int(len(df))
        if total == 0:
            return Decimal("1.0")
            
        denominator = math.sqrt(total) + 0.1
        factor = min(1.0, 1.0 / denominator)
        return Decimal(str(round(factor, 4)))

    def _calculate_skill_concentration(self, descriptions: List[str]) -> (Decimal, Set[str]):
        """
        Calculate skill concentration from Snowflake job descriptions.
        Concentration = 1 - (unique_skills / 15)
        Returns: (score, set_of_found_skills)
        """
        found_skills = set()
        for desc in descriptions:
            desc_lower = str(desc).lower()
            for skill in self.AI_SKILL_KEYWORDS:
                if skill in desc_lower:
                    found_skills.add(skill)
        
        unique_count = len(found_skills)
        concentration = 1.0 - (unique_count / 15.0)
        return Decimal(str(max(0.0, min(1.0, concentration)))), found_skills

    def _calculate_individual_mention_factor(self, df: pd.DataFrame) -> Decimal:
        """
        Calculate individual mention factor from Glassdoor text.
        Looks for patterns like "CEO", "CTO", "Manager", "Supervisor" in pros/cons.
        """
        total = int(len(df))
        if total == 0:
            return Decimal("0.5")
            
        # Combining text fields
        text_data = df['pros'].fillna('') + " " + df['cons'].fillna('') + " " + df['advice'].fillna('')
        
        # Simple keywords for individual mentions
        keywords = ["ceo", "cto", "cfo", "manager", "supervisor", "lead", "head of", "director"]
        pattern = '|'.join(keywords)
        
        # Count reviews that mention at least one keyword
        mention_count = int(text_data.str.contains(pattern, case=False).sum())
        
        ratio = Decimal(mention_count) / Decimal(total)
        return ratio

