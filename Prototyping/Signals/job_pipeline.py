import os
import pandas as pd
import re
import logging
import time
import random
from dataclasses import dataclass, field
from typing import List, Set, Optional
from datetime import datetime
from jobspy import scrape_jobs
from stealth_scraper import run_stealth_scrape

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass
class JobPosting:
    """Represents a job posting as defined in the Collector spec."""
    title: str
    company: str
    location: str
    description: str
    posted_date: Optional[str] = None
    source: str = "linkedin"
    url: str = ""
    is_ai_related: bool = False
    ai_skills: List[str] = field(default_factory=list)

class JobPipeline:
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

    def __init__(self, output_file="processed_jobs.csv"):
        self.output_file = output_file

    def _is_tech_job(self, title: str) -> bool:
        """Check if posting is a technology job based on title (from screenshot)."""
        title_lower = title.lower()
        return any(kw in title_lower for kw in self.TECH_TITLE_KEYWORDS)

    def classify_posting(self, title: str, description: str) -> tuple[bool, List[str], List[str]]:
        """Classify a job posting as AI-related and extract skills and categories."""
        text = f"{title} {description}".lower()
        
        # Check for AI keywords
        is_ai = any(kw in text for kw in self.AI_KEYWORDS)
        
        # Extract AI skills
        skills = [skill for skill in self.AI_SKILLS_LIST if skill in text]
        
        # Extract AI categories using same logic as patents
        categories = []
        if any(k in text for k in ["neural", "deep learning", "transformer", "backpropagation", "autoencoder", "gan"]):
            categories.append("deep_learning")
        if any(k in text for k in ["vision", "image", "object detection", "pattern recognition", "signal processing"]):
            categories.append("computer_vision")
        if any(k in text for k in ["predictive", "forecasting", "probabilistic", "statistical learning", "classification"]):
            categories.append("predictive_analytics")
        if any(k in text for k in ["natural language", "nlp", "semantic", "text mining", "information retrieval"]):
            categories.append("nlp")
        if any(k in text for k in ["generative", "gpt", "llm", "large language model", "diffusion model"]):
            categories.append("generative_ai")
        
        return is_ai, skills, categories

    def calculate_hiring_signal(self, total_tech_jobs: int, ai_jobs: int, all_skills: Set[str]):
        """
        Calculate hiring signal score (0-100) based on screenshots:
        - Base: AI ratio * 60 (max 60)
        - Skill diversity: (len(skills)/10) * 20 (max 20)
        - Volume bonus: (ai_jobs / 5) * 20 (max 20)
        """
        if total_tech_jobs == 0:
            return 0.0, 0.5
            
        ai_ratio = ai_jobs / total_tech_jobs
        
        score = (
            min(ai_ratio * 60, 60) +
            min(len(all_skills) / 10, 1) * 20 +
            min(ai_jobs / 5, 1) * 20
        )
        
        confidence = min(0.5 + total_tech_jobs / 100, 0.95)
        return round(score, 1), confidence

    def process_jobs(self, company: str, days: int = 7, results_wanted: int = 50):
        logging.info(f"Fetching jobs for {company} in the USA (Last {days} days)...")
        
        # Strategy 1: Search with full name
        search_query = company
        
        # Strategy 2: If company name has "Inc." or "Corp", try stripping it for broader results
        if "Inc" in company or "Corp" in company or "Group" in company:
            clean_variations = [
                company.replace("Inc.", "").replace("Inc", "").strip(),
                company.replace("Corporation", "").replace("Corp", "").strip(),
                company.replace("Group", "").strip()
            ]
            # Use the shortest clean version to cast a wider net
            search_query = min(clean_variations, key=len)
                
        logging.info(f"Using search query: '{search_query}'")

        try:
            df = scrape_jobs(
                site_name=["linkedin"],
                search_term=search_query,
                location="USA",
                results_wanted=results_wanted,
                hours_old=days * 24,
                linkedin_fetch_description=True
            )
        except Exception as e:
            logging.error(f"Scraping failed: {e}")
            return

        if df.empty:
            logging.info("No jobs found.")
            return

        processed_jobs = []
        total_tech_count = 0
        ai_job_count = 0
        captured_skills = set()

        for _, row in df.iterrows():
            title = str(row['title'])
            desc = str(row.get('description', ''))
            job_url = str(row.get('job_url', ''))

            # Fallback: If description is missing or abnormally short, use Playwright
            if len(desc) < 200 and job_url:
                logging.info(f"Description missing/short for '{title}'. Attempting stealth fallback...")
                desc = run_stealth_scrape(job_url)
                # Small wait to prevent rapid browser launches
                time.sleep(random.uniform(2, 5))
            
            is_tech = self._is_tech_job(title)
            is_ai, skills, categories = self.classify_posting(title, desc)
            
            # Update metrics
            if is_ai: is_tech = True # Force AI jobs to count as tech
            
            if is_tech:
                total_tech_count += 1
            if is_ai:
                ai_job_count += 1
                captured_skills.update(skills)

            # Keep only Tech or AI jobs
            if is_tech or is_ai:
                job_data = row.to_dict()
                job_data['is_tech'] = is_tech
                job_data['is_ai'] = is_ai
                job_data['ai_skills_found'] = ",".join(skills)
                job_data['ai_categories'] = ",".join(categories)
                
                # Capture Company URL if available from scraper
                if 'company_url' in row and row['company_url']:
                    job_data['company_url'] = str(row['company_url'])
                    
                processed_jobs.append(job_data)

        # Calculate final signal score for the company
        score, confidence = self.calculate_hiring_signal(total_tech_count, ai_job_count, captured_skills)
        
        logging.info(f"Summary for {company}:")
        logging.info(f" - Total Tech Jobs Found: {total_tech_count}")
        logging.info(f" - AI Jobs Found: {ai_job_count}")
        logging.info(f" - AI Hiring Signal Score: {score}/100 (Confidence: {confidence})")

        if processed_jobs:
            final_df = pd.DataFrame(processed_jobs)
            if os.path.exists(self.output_file):
                history = pd.read_csv(self.output_file)
                final_df = final_df[~final_df['job_url'].isin(history['job_url'])]
                if not final_df.empty:
                    final_df = pd.concat([history, final_df], ignore_index=True)
                else:
                    final_df = history
            
            final_df.to_csv(self.output_file, index=False)
            logging.info(f"Saved {len(processed_jobs)} relevant jobs to {self.output_file}")
            
        return {
            "score": score,
            "confidence": confidence,
            "total_tech_count": total_tech_count,
            "ai_job_count": ai_job_count,
            "skills": list(captured_skills)
        }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--company", required=True)
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    
    pipeline = JobPipeline()
    pipeline.process_jobs(company=args.company, days=args.days)
