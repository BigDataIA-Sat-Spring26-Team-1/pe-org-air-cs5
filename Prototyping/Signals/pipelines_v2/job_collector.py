import logging
import asyncio
import random
import pandas as pd
from typing import List, Dict, Any, Tuple
from jobspy import scrape_jobs
from .utils import WebUtils
from .models import CollectorResult, SignalCategory
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from stealth_scraper import run_stealth_scrape

logger = logging.getLogger(__name__)

class JobCollector:
    """Scans job boards to find AI-related hiring trends and technical skill demands."""

    # Core keywords and skills used to identify AI-centric roles
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

    # Identifies roles with engineering, data, or analytical focus
    TECH_TITLE_KEYWORDS = [
        "engineer", "developer", "programmer", "software",
        "data", "analyst", "scientist", "technical"
    ]

    def __init__(self, output_file: str = "processed_jobs.csv"):
        self.output_file = output_file

    def _is_tech_role(self, title: str) -> bool:
        """Determines if a role is technical based on common keywords."""
        return any(kw in title.lower() for kw in self.TECH_TITLE_KEYWORDS)

    def _analyze_description(self, text: str) -> Tuple[bool, List[str], List[str]]:
        """Scans job text for AI categories and specific tools."""
        text = text.lower()
        is_ai = any(kw in text for kw in self.AI_KEYWORDS)
        skills = [skill for skill in self.AI_SKILLS_LIST if skill in text]
        
        categories = []
        if any(k in text for k in ["neural", "deep learning", "transformer", "gan"]): categories.append("deep_learning")
        if any(k in text for k in ["vision", "image", "object detection"]): categories.append("computer_vision")
        if any(k in text for k in ["predictive", "forecasting", "statistical"]): categories.append("predictive_analytics")
        if any(k in text for k in ["natural language", "nlp", "semantic"]): categories.append("nlp")
        if any(k in text for k in ["generative", "gpt", "llm"]): categories.append("generative_ai")
                
        return is_ai, categories, skills

    async def collect(self, company_name: str, days: int = 7) -> CollectorResult:
        """Scrapes LinkedIn for jobs and analyzes them for AI signals."""
        logger.info(f"Checking job postings for {company_name}")
        search_query = WebUtils.clean_company_name(company_name)
        
        try:
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, lambda: scrape_jobs(
                site_name=["linkedin"],
                search_term=search_query,
                location="USA",
                results_wanted=50,
                hours_old=days * 24,
                linkedin_fetch_description=True
            ))
        except Exception as e:
            logger.error(f"Hiring data collection failed: {str(e)}")
            return self._empty_result(f"Scraper error: {str(e)}")

        if df.empty:
            return self._empty_result("No jobs found")

        processed_jobs = []
        ai_count = 0
        tech_count = 0
        total_skills = set()
        
        for _, row in df.iterrows():
            title = str(row.get('title', '')).strip()
            desc = str(row.get('description', '')).strip()
            url = str(row.get('job_url', ''))
            
            # Enrich short descriptions with a second-pass scrape
            if len(desc) < 500 and url:
                try:
                    full_text = run_stealth_scrape(url)
                    if len(full_text) > len(desc):
                        desc = full_text
                        # Respectful delay after full page fetch
                        await asyncio.sleep(random.uniform(1, 2))
                except Exception:
                    pass

            is_ai, cats, skills = self._analyze_description(desc)
            is_tech = self._is_tech_role(title) or is_ai
            
            if is_tech:
                tech_count += 1
                if is_ai:
                    ai_count += 1
                    total_skills.update(skills)
                
                processed_jobs.append({
                    "company": company_name,
                    "title": title,
                    "description": desc,
                    "url": url,
                    "is_ai": is_ai,
                    "categories": cats,
                    "skills": skills,
                    "posted_at": str(row.get('date_posted', ''))
                })

        # Persistence for LeadershipCollector and TechStackCollector
        if processed_jobs:
            new_df = pd.DataFrame(processed_jobs)
            
            # Align schema if appending to existing history
            if os.path.exists(self.output_file):
                try:
                    old_df = pd.read_csv(self.output_file)
                    
                    # Normalize URL column for consistency
                    if 'job_url' in old_df.columns and 'url' in new_df.columns:
                        new_df = new_df.rename(columns={'url': 'job_url'})
                    
                    combined_df = pd.concat([old_df, new_df], ignore_index=True)
                    
                    # Deduplicate ensuring we keep the latest or just unique URLs
                    dedup_key = 'job_url' if 'job_url' in combined_df.columns else 'url'
                    if dedup_key in combined_df.columns:
                        combined_df = combined_df.drop_duplicates(subset=[dedup_key], keep='last')
                    
                    combined_df.to_csv(self.output_file, index=False)
                except Exception as e:
                    logger.warning(f"Could not merge with existing jobs file: {e}")
                    new_df.to_csv(self.output_file, index=False)
            else:
                new_df.to_csv(self.output_file, index=False)

        # Scoring: Proportion (60) + Skill Breadth (20) + Absolute Volume (20)
        ai_ratio = ai_count / tech_count if tech_count > 0 else 0
        score = (
            min(ai_ratio * 60, 60) +
            min(len(total_skills) / 10, 1) * 20 +
            min(ai_count / 5, 1) * 20
        )
        
        return CollectorResult(
            category=SignalCategory.TECHNOLOGY_HIRING,
            normalized_score=round(float(score), 2),
            confidence=min(0.5 + tech_count / 100, 0.95),
            raw_value=f"{ai_count} AI roles found within {tech_count} tech openings",
            source="LinkedIn",
            metadata={
                "job_evidence": processed_jobs,
                "tech_count": tech_count,
                "ai_count": ai_count,
                "skills": list(total_skills),
                "count": len(processed_jobs)
            }
        )

    def _empty_result(self, msg: str) -> CollectorResult:
        return CollectorResult(
            category=SignalCategory.TECHNOLOGY_HIRING,
            normalized_score=0,
            confidence=0.5,
            raw_value=msg,
            source="LinkedIn"
        )
