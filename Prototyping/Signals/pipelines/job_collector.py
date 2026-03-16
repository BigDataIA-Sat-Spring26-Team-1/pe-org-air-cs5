import os
import pandas as pd
import logging
import time
import random
import re
from typing import List, Set, Dict, Any, Optional
from jobspy import scrape_jobs
from stealth_scraper import run_stealth_scrape
from .models import CollectorResult

# Configure logger
logger = logging.getLogger(__name__)

class JobCollector:
    """
    Analyzes job market data to quantify AI hiring intensity and skill breadth.
    """

    AI_KEYWORDS = [
        "machine learning", "ml engineer", "data scientist",
        "artificial intelligence", "deep learning", "nlp",
        "natural language processing", "computer vision", "mlops",
        "ai engineer", "pytorch", "tensorflow", "llm",
        "large language model", "generative ai", "genai",
        "transformer", "bert", "gpt", "rag", "vector database",
        "reinforcement learning", "neural network", "predictive modeling",
        "statistical learning", "autoencoder", "gan", "diffusion model"
    ]

    AI_SKILLS_LIST = [
        "python", "pytorch", "tensorflow", "scikit-learn",
        "spark", "hadoop", "kubernetes", "docker",
        "aws sagemaker", "azure ml", "gcp vertex",
        "huggingface", "langchain", "openai", "anthropic",
        "cohere", "llama", "mistral", "pandas", "numpy",
        "jax", "keras", "xgboost", "lightgbm", "pinecone",
        "milvus", "weaviate", "chroma", "mongodb", "snowflake",
        "databricks", "mlflow", "kubeflow", "airflow", "dvc"
    ]

    TECH_TITLE_KEYWORDS = [
        "engineer", "developer", "programmer", "software",
        "data", "analyst", "scientist", "technical"
    ]

    def __init__(self, output_file: str = "processed_jobs.csv"):
        self.output_file = output_file

    def _is_tech_job(self, title: str) -> bool:
        """Determines if a role is technical based on the title."""
        title_lower = title.lower()
        return any(kw in title_lower for kw in self.TECH_TITLE_KEYWORDS)

    def _classify_posting(self, title: str, description: str) -> tuple[bool, List[str], List[str]]:
        """Classifies a job posting as AI-related and extracts skills and categories."""
        text = f"{title} {description}".lower()
        is_ai = any(kw in text for kw in self.AI_KEYWORDS)
        skills = [skill for skill in self.AI_SKILLS_LIST if skill in text]
        
        categories = []
        if any(k in text for k in ["neural", "deep learning", "transformer", "gan"]):
            categories.append("deep_learning")
        if any(k in text for k in ["vision", "image", "object detection"]):
            categories.append("computer_vision")
        if any(k in text for k in ["predictive", "forecasting", "statistical"]):
            categories.append("predictive_analytics")
        if any(k in text for k in ["natural language", "nlp", "semantic"]):
            categories.append("nlp")
        if any(k in text for k in ["generative", "gpt", "llm"]):
            categories.append("generative_ai")
        
        return is_ai, skills, categories

    def _score_hiring(self, tech_total: int, ai_total: int, skill_diversity: int) -> Dict[str, float]:
        """Calculates a normalized score based on hiring proportions (5/2/10 style weights)."""
        if tech_total == 0:
            return {"score": 0.0, "confidence": 0.5}
            
        ai_ratio = ai_total / tech_total
        
        # Scoring: Proportion (60) + Skill Breadth (20) + Absolute Volume (20)
        score = (
            min(ai_ratio * 60, 60) +
            min(skill_diversity / 10, 1) * 20 +
            min(ai_total / 5, 1) * 20
        )
        
        confidence = min(0.5 + tech_total / 100, 0.95)
        return {"score": round(score, 1), "confidence": round(confidence, 2)}

    def collect(self, company_name: str, days: int = 7) -> CollectorResult:
        """Executes the job collection and analysis workflow."""
        logger.info(f"Scanning technical vacancies for {company_name}")
        
        # Clean query
        query = company_name
        for suffix in ["Inc.", "Inc", "Corporation", "Corp", "Group"]:
            if suffix in company_name:
                query = company_name.replace(suffix, "").strip()
                break

        try:
            df = scrape_jobs(
                site_name=["linkedin"],
                search_term=query,
                location="USA",
                results_wanted=50,
                hours_old=days * 24,
                linkedin_fetch_description=True
            )
        except Exception as e:
            logger.error(f"Job scraping failed for {company_name}: {e}")
            return CollectorResult(
                normalized_score=0.0,
                confidence=0.0,
                raw_value="Scraping failed",
                metadata={"error": str(e)}
            )

        if df.empty:
            return CollectorResult(
                normalized_score=0.0,
                confidence=0.5,
                raw_value="No jobs found",
                metadata={"tech_count": 0, "ai_count": 0}
            )

        tech_jobs = 0
        ai_jobs = 0
        captured_skills = set()
        processed_data = []

        for _, row in df.iterrows():
            title = str(row.get('title', ''))
            desc = str(row.get('description', ''))
            url = str(row.get('job_url', ''))

            if len(desc) < 200 and url:
                desc = run_stealth_scrape(url)
                time.sleep(random.uniform(1, 3))
            
            is_ai, skills, categories = self._classify_posting(title, desc)
            is_tech = self._is_tech_job(title) or is_ai
            
            if is_tech:
                tech_jobs += 1
                if is_ai:
                    ai_jobs += 1
                    captured_skills.update(skills)
                
                row_dict = row.to_dict()
                row_dict['is_tech'] = is_tech
                row_dict['is_ai'] = is_ai
                row_dict['ai_skills_found'] = ",".join(skills)
                processed_data.append(row_dict)

        # Persistence
        if processed_data:
            final_df = pd.DataFrame(processed_data)
            if os.path.exists(self.output_file):
                history = pd.read_csv(self.output_file)
                final_df = pd.concat([history, final_df[~final_df['job_url'].isin(history['job_url'])]], ignore_index=True)
            final_df.to_csv(self.output_file, index=False)

        scoring = self._score_hiring(tech_jobs, ai_jobs, len(captured_skills))
        
        return CollectorResult(
            normalized_score=scoring["score"],
            confidence=scoring["confidence"],
            raw_value=f"{ai_jobs} AI roles identified in {tech_jobs} technical postings",
            metadata={
                "tech_count": tech_jobs,
                "ai_count": ai_jobs,
                "skills": list(captured_skills),
                "count": len(processed_data)
            }
        )
