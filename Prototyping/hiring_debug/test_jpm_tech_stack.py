import asyncio
import logging
import re
import pandas as pd
from typing import List, Dict, Any, Tuple
from difflib import SequenceMatcher
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("JPM-TechStack-Debug")

# --- Keywords from app/pipelines/external_signals/tech_stack_collector.py ---

TECH_INDICATORS = {
    "cloud_ml": ["aws sagemaker", "azure ml", "google vertex", "databricks", "sagemaker", "vertex ai", "azure machine learning", "amazon sagemaker", "google ml engine"],
    "ml_framework": ["tensorflow", "pytorch", "scikit-learn", "keras", "cuda", "onnx", "jax", "flax", "xgboost", "lightgbm", "catboost", "detectron2", "opencv"],
    "data_platform": ["snowflake", "databricks", "spark", "hadoop", "bigquery", "redshift", "athena", "presto", "dremio", "teradata", "cloudera", "confluent"],
    "ai_api": ["openai", "anthropic", "huggingface", "cohere", "langchain", "mistral", "llama-index", "gradio", "streamlit", "pinecone", "weaviate", "milvus", "qdrant"]
}

def string_similarity(a: str, b: str) -> float:
    a = a.lower().strip()
    b = b.lower().strip()
    a_alpha = re.sub(r'[^a-z0-9]', '', a)
    b_alpha = re.sub(r'[^a-z0-9]', '', b)
    if a_alpha == b_alpha or a_alpha in b_alpha or b_alpha in a_alpha:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()

def _is_matching_company(listing_company: str, target_company: str, ticker: str = None, threshold: float = 0.75) -> bool:
    if not listing_company:
        return False
    l_name = str(listing_company).lower().strip()
    t_name = str(target_company).lower().strip()
    if l_name in t_name or t_name in l_name:
        return True
    if ticker and ticker.lower() in l_name.split():
        return True
    l_norm = re.sub(r'[^a-z0-9]', '', l_name)
    t_norm = re.sub(r'[^a-z0-9]', '', t_name)
    if l_norm == t_norm or l_norm in t_norm or t_norm in l_norm:
        return True
    similarity = SequenceMatcher(None, l_name, t_name).ratio()
    return similarity >= threshold

def debug_job_tech_analysis(jobs_file: str, company: str, ticker: str = None):
    logger.info(f"Analyzing job tech for {company} in {jobs_file}")
    found = []
    try:
        df = pd.read_csv(jobs_file)
        logger.info(f"Loaded {len(df)} jobs from CSV")
        
        # Use a list to collect indices that match
        matching_indices = []
        for idx, row in df.iterrows():
            listing_company = row.get('company', '')
            if _is_matching_company(listing_company, company, ticker):
                matching_indices.append(idx)
        
        company_jobs = df.loc[matching_indices]
        logger.info(f"Matched {len(company_jobs)} jobs for {company}")
        
        if company_jobs.empty:
            logger.warning("No matching jobs found in CSV.")
            return []
            
        combined_text = " ".join(company_jobs['description'].fillna("").astype(str)).lower()
        logger.info(f"Combined text length: {len(combined_text)}")
        
        seen = set()
        for cat, techs in TECH_INDICATORS.items():
            for tech in techs:
                if tech in combined_text and tech not in seen:
                    found.append({"name": tech.upper(), "category": cat, "source": "job_descriptions"})
                    seen.add(tech)
        
        return found
    except Exception as e:
        logger.error(f"Job tech analysis failed: {e}")
        return []

async def debug_domain_resolution(company: str, ticker: str = None):
    logger.info(f"Resolving domain for {company}")
    # Simplified domain resolution for debug
    clean_name = re.sub(r'[^\w\s]', '', company).lower()
    # Mocking what typically happens
    domain = f"{clean_name.split()[0]}.com"
    logger.info(f"Guessed domain: {domain}")
    return domain

async def test_jpm_tech_stack():
    company_name = "JPMorgan Chase"
    ticker = "JPM"
    jobs_file = "processed_jobs.csv" # Or the one we generated: debug_jpm_jobs.csv
    
    # 1. Test with the jobs we just generated in last step if available
    import os
    if not os.path.exists(jobs_file):
        # Fallback to the debug one if it exists
        if os.path.exists("debug_jpm_jobs.csv"):
            jobs_file = "debug_jpm_jobs.csv"
        else:
            logger.error("No jobs file found to test with.")
            return

    logger.info(f"--- DEBUGGING TECH STACK FOR {company_name} ---")
    
    # Check Job Data
    job_tech = debug_job_tech_analysis(jobs_file, company_name, ticker)
    logger.info(f"Found {len(job_tech)} markers in job descriptions:")
    for t in job_tech:
        logger.info(f" - {t['name']} ({t['category']})")

    # Check Web Scan (Mocking/Simulating)
    domain = await debug_domain_resolution(company_name, ticker)
    
    # If job_tech is empty and web scan fails, score is 0.
    if not job_tech:
        logger.error("ZERO markers found in jobs. This is why Digital Presence might be 0.")
    else:
        # Score calculation from orchestrator
        detections = job_tech # Assuming only job tech for now
        unique_cats = set(s["category"] for s in detections)
        score = min(len(detections) * 10, 50) + min(len(unique_cats) * 12.5, 50)
        logger.info(f"Calculated Score: {score}")

if __name__ == "__main__":
    asyncio.run(test_jpm_tech_stack())
