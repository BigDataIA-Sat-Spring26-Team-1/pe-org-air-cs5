import logging
import re
from datetime import datetime
import os
from pathlib import Path
import asyncio
import random
import pandas as pd
from typing import List, Dict, Any, Tuple
from difflib import SequenceMatcher
from jobspy import scrape_jobs
from .utils import WebUtils
from app.models.signals import CollectorResult, SignalCategory, SignalEvidenceItem


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
        "statistical learning", "autoencoder", "gan", "diffusion model",
        "applied ai", "ai solutions", "ml researcher",
        "agentic", "ai agent", "prompt engineer", "copilot", "autonomous system"
    ]

    AI_SKILLS_LIST = [
        "python", "pytorch", "tensorflow", "scikit-learn",
        "spark", "hadoop", "kubernetes", "docker",
        "aws sagemaker", "azure ml", "gcp vertex",
        "huggingface", "langchain", "openai", "anthropic",
        "cohere", "llama", "mistral", "pandas", "numpy",
        "jax", "keras", "xgboost", "lightgbm", "pinecone",
        "milvus", "weaviate", "chroma", "mongodb", "snowflake",
        "databricks", "mlflow", "kubeflow", "airflow", "dvc",
        "langgraph", "langsmith", "autogen", "crewai", "ollama"
    ]

    # Identifies roles with engineering, data, or analytical focus
    TECH_TITLE_KEYWORDS = [
        "engineer", "developer", "programmer", "software",
        "data", "analyst", "scientist", "technical",
        "quantitative", "researcher", "architect", "computing", "technology",
        "manager", "lead", "principal", "head", "specialist"
    ]

    def __init__(self, output_file: str = "processed_jobs.csv"):
        self.output_file = output_file

    def _is_tech_role(self, title: str) -> bool:
        """Determines if a role is technical based on common keywords."""
        return any(kw in title.lower() for kw in self.TECH_TITLE_KEYWORDS)

    def _analyze_description(self, text: str) -> Tuple[bool, List[str], List[str]]:
        """Scans job text for AI categories and specific tools."""
        text = text.lower()
        
        is_ai = False
        for kw in self.AI_KEYWORDS:
            if re.search(r'\b' + re.escape(kw) + r'\b', text):
                is_ai = True
                break
                
        skills = [skill for skill in self.AI_SKILLS_LIST if re.search(r'\b' + re.escape(skill) + r'\b', text)]
        
        categories = []
        if any(re.search(r'\b' + re.escape(k) + r'\b', text) for k in ["neural", "deep learning", "transformer", "gan", "applied ai"]): 
            categories.append("deep_learning")
        if any(re.search(r'\b' + re.escape(k) + r'\b', text) for k in ["vision", "image", "object detection"]): 
            categories.append("computer_vision")
        if any(re.search(r'\b' + re.escape(k) + r'\b', text) for k in ["predictive", "forecasting", "statistical"]): 
            categories.append("predictive_analytics")
        if any(re.search(r'\b' + re.escape(k) + r'\b', text) for k in ["natural language", "nlp", "semantic"]): 
            categories.append("nlp")
        if any(re.search(r'\b' + re.escape(k) + r'\b', text) for k in ["generative", "gpt", "llm", "chatbot", "claude"]): 
            categories.append("generative_ai")
                    
        return is_ai, categories, skills

    def _is_matching_company(self, listing_company: str, target_company: str, ticker: str = None) -> bool:
        """Robust check to ensure the job listing belongs to the target company using similarity."""
        if not listing_company:
            return False
            
        l_name = str(listing_company).lower().strip()
        t_name = str(target_company).lower().strip()
        
        # 1. Exact or partial name match
        if l_name in t_name or t_name in l_name:
            return True
            
        # 2. Ticker match
        if ticker and ticker.lower() in l_name.split():
            return True
            
        # 3. Alphanumeric normalization match (CRITICAL for JPMorganChase)
        l_norm = re.sub(r'[^a-z0-9]', '', l_name)
        t_norm = re.sub(r'[^a-z0-9]', '', t_name)
        if l_norm == t_norm or l_norm in t_norm or t_norm in l_norm:
            return True

        # 4. Sequence similarity ratio (Fuzzy match)
        similarity = SequenceMatcher(None, l_name, t_name).ratio()
        if similarity > 0.75:
            return True

        # 5. Significant word overlap
        ignore_words = {"inc", "corp", "corporation", "limited", "ltd", "company", "group", "holdings", "llc", "the", "and", "&"}
        l_words = {w for w in l_name.replace(',', ' ').replace('.', ' ').split() if w not in ignore_words and len(w) > 2}
        t_words = {w for w in t_name.replace(',', ' ').replace('.', ' ').split() if w not in ignore_words and len(w) > 2}
        
        if l_words & t_words:
            return True
            
        return False

    async def collect(self, company_name: str, days: int = 30, ticker: str = None) -> CollectorResult:
        """Scrapes LinkedIn for jobs using multiple search strategies to maximize AI signal discovery."""
        logger.info(f"Checking job postings for {company_name} (Ticker: {ticker})")
        
        clean_name = WebUtils.clean_company_name(company_name)
        
        # We run multiple targeted queries and combine results to overcome LinkedIn's noise for large corporations
        queries = [
            clean_name,                                      # Broad Strategy
            f"{clean_name} AI",                              # AI-Specific Strategy
            f"{clean_name} Data Science",                    # Data-Strategy
            f"{clean_name} Machine Learning",                # ML-Specific Strategy
            f"{clean_name} Software Engineer",               # General Tech Strategy (Crucial for non-tech firms)
            f"{clean_name} ML/AI"                             # Experimental Strategy (Proven effective)
        ]
        
        all_jobs_df = pd.DataFrame()
        loop = asyncio.get_event_loop()

        for q in queries:
            logger.info(f"   [Search Strategy] Querying: {q}...")
            try:
                # Add delay to avoid rate limiting
                await asyncio.sleep(random.uniform(3.0, 7.0))
                
                # Scraper is synchronous, run in executor
                df = await loop.run_in_executor(None, lambda query=q: scrape_jobs(
                    site_name=["linkedin"],
                    search_term=query,
                    location="USA",
                    results_wanted=50,  # Balanced for volume and safety
                    hours_old=days * 24,
                    linkedin_fetch_description=True
                ))
                
                if not df.empty:
                    logger.info(f"      Found {len(df)} postings for '{q}'")
                    all_jobs_df = pd.concat([all_jobs_df, df], ignore_index=True)
                else:
                    logger.warning(f"      No postings discovered for '{q}' (might be rate-limited if returned instantly)")
            except Exception as e:
                logger.error(f"      Hiring data scrape failed for query {q}: {str(e)}")

        if all_jobs_df.empty:
            return self._empty_result("No jobs discovered across all search strategies.")

        # Deduplicate results found by different queries
        dedup_key = 'job_url' if 'job_url' in all_jobs_df.columns else 'url'
        if dedup_key in all_jobs_df.columns:
            # We keep the one with longer description if available, usually the latest find is fine
            all_jobs_df = all_jobs_df.drop_duplicates(subset=[dedup_key], keep='last')

        processed_jobs = []
        evidence_items = []
        tech_count = 0
        ai_count = 0
        total_skills = set()
        
        for _, row in all_jobs_df.iterrows():
            listing_company = row.get('company', '')
            if not self._is_matching_company(listing_company, company_name, ticker):
                continue

            title = str(row.get('title', '')).strip()
            desc = str(row.get('description', '')).strip()
            url = str(row.get('job_url', ''))
            
            # Enrich short descriptions if needed
            if len(desc) < 500 and url:
                try:
                    full_text = await WebUtils.fetch_page_text(url)
                    if len(full_text) > len(desc):
                        desc = full_text
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                except Exception:
                    pass

            is_ai, cats, skills = self._analyze_description(desc)
            
            # Check title fallback for AI keywords
            title_is_ai = any(re.search(r'\b' + re.escape(kw.lower()) + r'\b', title.lower()) for kw in ["ai", "ml", "intelligence", "data science"])
            final_is_ai = is_ai or title_is_ai
            
            # Roles tagged as Tech if they match TECH_TITLE_KEYWORDS OR are final_is_ai
            is_tech = self._is_tech_role(title) or final_is_ai
            
            if is_tech:
                tech_count += 1
                if final_is_ai:
                    ai_count += 1
                    total_skills.update(skills)
                
                # Sanitize date
                raw_date = row.get('date_posted')
                if pd.isna(raw_date) or not str(raw_date).strip() or str(raw_date).lower() == 'nan':
                    evidence_date = datetime.now().date().isoformat()
                else:
                    evidence_date = str(raw_date)

                processed_jobs.append({
                    "company": company_name,
                    "title": title,
                    "description": desc,
                    "url": url,
                    "is_ai": final_is_ai,
                    "categories": cats,
                    "skills": list(skills),
                    "posted_at": evidence_date
                })
                evidence_items.append(SignalEvidenceItem(
                    title=title,
                    description=desc[:2000] if desc else None,
                    url=url,
                    tags=cats + (["AI"] if final_is_ai else []) + (["Tech"] if is_tech else []),
                    date=evidence_date,
                    metadata={
                        "skills": list(skills),
                        "is_ai": final_is_ai
                    }
                ))

        # Scoring: Based on deduplicated aggregate from all search strategies
        ai_ratio = ai_count / tech_count if tech_count > 0 else 0
        # Score blends Ratio (intensity) with Volume (absolute discovery)
        # Ratio part: 40 points, Volume part: 60 points (scaled to 10 hires as high benchmark)
        score = (min(ai_ratio * 40, 40)) + (min(ai_count / 10, 1) * 60)
        
        return CollectorResult(
            category=SignalCategory.TECHNOLOGY_HIRING,
            normalized_score=round(float(score), 2),
            confidence=min(0.5 + tech_count / 100, 0.95),
            raw_value=f"{ai_count} AI roles found within {tech_count} unique technical openings",
            source="LinkedIn (Combined Strategies)",
            evidence=evidence_items,
            metadata={
                "tech_count": tech_count,
                "ai_count": ai_count,
                "skills": list(total_skills),
                "count": len(processed_jobs),
                "queries_executed": queries
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
