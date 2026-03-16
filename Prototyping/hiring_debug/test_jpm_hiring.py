import asyncio
import logging
import pandas as pd
import re
from typing import List, Dict, Any, Tuple
from jobspy import scrape_jobs
from datetime import datetime
from difflib import SequenceMatcher

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("JPM-Hiring-Similarity-Test")

# --- Keywords from app/pipelines/external_signals/job_collector.py ---

AI_KEYWORDS = [
    "machine learning", "ml engineer", "data scientist",
    "artificial intelligence", "deep learning", "nlp",
    "natural language processing", "computer vision", "mlops",
    "ai engineer", "pytorch", "tensorflow", "llm",
    "large language model", "generative ai", "genai",
    "transformer", "bert", "gpt", "rag", "vector database",
    "reinforcement learning", "neural network", "predictive modeling",
    "statistical learning", "autoencoder", "gan", "diffusion model",
    "applied ai", "ai solutions", "ml researcher"
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
    "data", "analyst", "scientist", "technical",
    "quantitative", "researcher", "architect", "computing", "technology"
]

def string_similarity(a: str, b: str) -> float:
    """Calculates a similarity ratio between two strings (0 to 1)."""
    # Lowercase and strip for better matching
    a = a.lower().strip()
    b = b.lower().strip()
    
    # 1. Alphanumeric only comparison (good for JPMorganChase vs J.P. Morgan Chase)
    a_alpha = re.sub(r'[^a-z0-9]', '', a)
    b_alpha = re.sub(r'[^a-z0-9]', '', b)
    if a_alpha == b_alpha or a_alpha in b_alpha or b_alpha in a_alpha:
        return 1.0
        
    # 2. Sequence Matcher for fuzzy matching
    return SequenceMatcher(None, a, b).ratio()

def _is_matching_company(listing_company: str, target_company: str, ticker: str = None, threshold: float = 0.7) -> Tuple[bool, float]:
    """Uses similarity metrics to check for company match."""
    if not listing_company:
        return False, 0.0
        
    # Check ticker match first (absolute)
    if ticker and ticker.lower() in str(listing_company).lower().split():
        return True, 1.0

    score = string_similarity(listing_company, target_company)
    return score >= threshold, score

def _analyze_description(text: str) -> Tuple[bool, List[str], List[str]]:
    """Scans job text for AI categories and specific tools with word boundaries."""
    text = text.lower()
    
    # Check AI Keywords
    found_kws = []
    for kw in AI_KEYWORDS:
        if re.search(r'\b' + re.escape(kw) + r'\b', text):
            found_kws.append(kw)
    
    is_ai = len(found_kws) > 0
    skills = [skill for skill in AI_SKILLS_LIST if re.search(r'\b' + re.escape(skill) + r'\b', text)]
    
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

# --- Testing Script ---

async def test_jpm_hiring_advanced():
    company_name = "JPMorgan Chase"
    ticker = "JPM"
    days = 14
    
    logger.info(f"--- ADVANCED DEBUGGING FOR {company_name} ({ticker}) ---")
    
    try:
        df = scrape_jobs(
            site_name=["linkedin"],
            search_term=company_name,
            location="USA",
            results_wanted=100, # More results to verify count
            hours_old=days * 24,
            linkedin_fetch_description=True
        )
    except Exception as e:
        logger.error(f"Scrape failed: {e}")
        return

    if df.empty:
        logger.warning("No jobs found by scraper.")
        return

    logger.info(f"Retrieved {len(df)} total listings from LinkedIn.")
    
    stats = {"total": len(df), "company_match": 0, "tech_match": 0, "ai_match": 0}
    ai_roles_found = []

    for idx, row in df.iterrows():
        listing_company = row.get('company', 'Unknown')
        title = str(row.get('title', ''))
        desc = str(row.get('description', ''))
        
        is_comp, score = _is_matching_company(listing_company, company_name, ticker)
        
        if is_comp:
            stats["company_match"] += 1
            is_ai, cats, skills = _analyze_description(desc)
            
            # Check if title itself sounds like AI even if description is short
            title_is_ai = any(re.search(r'\b' + re.escape(kw) + r'\b', title.lower()) for kw in ["ai", "ml", "intelligence"])
            final_is_ai = is_ai or title_is_ai
            
            is_tech = any(kw in title.lower() for kw in TECH_TITLE_KEYWORDS) or final_is_ai
            
            if is_tech:
                stats["tech_match"] += 1
                if final_is_ai:
                    stats["ai_match"] += 1
                    ai_roles_found.append({
                        "title": title,
                        "cats": cats,
                        "skills": skills,
                        "company": listing_company
                    })
        else:
            if idx < 5: # Log first few rejections for visibility
                logger.info(f"Filter Out: '{listing_company}' (Score: {score:.2f})")

    logger.info("\n--- FINAL VERIFICATION RESULTS ---")
    logger.info(f"Similarity Threshold Used: 0.7")
    logger.info(f"Total Scraped:     {stats['total']}")
    logger.info(f"Company Matches:   {stats['company_match']}")
    logger.info(f"Technical Roles:   {stats['tech_match']}")
    logger.info(f"AI/ML Roles:       {stats['ai_match']}")
    
    if ai_roles_found:
        logger.info("\n--- AI ROLES LISTING ---")
        for i, role in enumerate(ai_roles_found):
            logger.info(f"{i+1}. {role['title']} (@{role['company']})")
            logger.info(f"   Cats: {role['cats']}, Skills: {role['skills'][:5]}")

if __name__ == "__main__":
    asyncio.run(test_jpm_hiring_advanced())
