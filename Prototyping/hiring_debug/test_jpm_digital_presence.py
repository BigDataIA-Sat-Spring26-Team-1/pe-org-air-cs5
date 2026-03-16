import asyncio
import logging
import re
import pandas as pd
from typing import List, Dict, Any, Tuple, Set
from difflib import SequenceMatcher
from datetime import datetime
from jobspy import scrape_jobs
from playwright.async_api import async_playwright

# Try to handle the stealth import based on what's available
try:
    from playwright_stealth import stealth_async as stealth_func
except ImportError:
    try:
        from playwright_stealth import stealth as stealth_func
    except ImportError:
        stealth_func = None

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("JPM-DigitalPresence-Simulation")

# --- Keywords from app/pipelines/external_signals/tech_stack_collector.py ---

TECH_INDICATORS = {
    "cloud_ml": ["aws sagemaker", "azure ml", "google vertex", "databricks", "sagemaker", "vertex ai", "azure machine learning", "amazon sagemaker", "google ml engine"],
    "ml_framework": ["tensorflow", "pytorch", "scikit-learn", "keras", "cuda", "onnx", "jax", "flax", "xgboost", "lightgbm", "catboost", "detectron2", "opencv"],
    "data_platform": ["snowflake", "databricks", "spark", "hadoop", "bigquery", "redshift", "athena", "presto", "dremio", "teradata", "cloudera", "confluent"],
    "ai_api": ["openai", "anthropic", "huggingface", "cohere", "langchain", "mistral", "llama-index", "gradio", "streamlit", "pinecone", "weaviate", "milvus", "qdrant"]
}

# --- Improved Similarity Logic ---

def _is_matching_company(listing_company: str, target_company: str, ticker: str = None) -> bool:
    if not listing_company: return False
    l_name = str(listing_company).lower().strip()
    t_name = str(target_company).lower().strip()
    
    # Simple match
    if l_name in t_name or t_name in l_name: return True
    if ticker and ticker.lower() in l_name.split(): return True
    
    # Alphanumeric match (handles JPMorganChase)
    l_norm = re.sub(r'[^a-z0-9]', '', l_name)
    t_norm = re.sub(r'[^a-z0-9]', '', t_name)
    if l_norm == t_norm or l_norm in t_norm or t_norm in l_norm: return True
    
    # Fuzzy match
    return SequenceMatcher(None, l_name, t_name).ratio() > 0.75

# --- Footprint Scan ---

async def scan_builtwith(domain: str):
    """Simulates the BuiltWith scan."""
    found = []
    logger.info(f"Scanning BuiltWith for: {domain}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Apply stealth if possible
        if stealth_func:
            try:
                if asyncio.iscoroutinefunction(stealth_func):
                    await stealth_func(page)
                else:
                    stealth_func(page)
            except:
                pass
        
        try:
            url = f"https://builtwith.com/{domain}"
            await page.goto(url, timeout=30000)
            await asyncio.sleep(3)
            content = (await page.inner_text("body")).lower()
            
            seen = set()
            for cat, techs in TECH_INDICATORS.items():
                for tech in techs:
                    if tech in content and tech not in seen:
                        found.append({"name": tech.upper(), "category": cat, "source": "builtwith"})
                        seen.add(tech)
                        
        except Exception as e:
            logger.warning(f"BuiltWith scan failed: {e}")
        finally:
            await browser.close()
    return found

async def simulate_pipeline():
    company_name = "JPMorgan Chase"
    ticker = "JPM"
    domain = "jpmorganchase.com"
    
    # 1. Job Multi-Signal Capture
    logger.info("--- Step 1: Capturing Intelligence from Job Descriptions ---")
    try:
        df = scrape_jobs(
            site_name=["linkedin"],
            search_term=company_name,
            location="USA",
            results_wanted=30,
            hours_old=168, # 7 days
            linkedin_fetch_description=True
        )
    except Exception as e:
        logger.error(f"Job scrape failed: {e}")
        df = pd.DataFrame()

    job_tech_markers = []
    if not df.empty:
        # Filter for the target company
        matching_count = sum(df['company'].apply(lambda x: _is_matching_company(x, company_name, ticker)))
        logger.info(f"Scraped {len(df)} jobs. Found {matching_count} matching {company_name}")
        
        company_df = df[df['company'].apply(lambda x: _is_matching_company(x, company_name, ticker))]
        combined_desc = " ".join(company_df['description'].fillna("").astype(str)).lower()
        
        seen = set()
        for cat, techs in TECH_INDICATORS.items():
            for tech in techs:
                if re.search(r'\b' + re.escape(tech) + r'\b', combined_desc):
                    job_tech_markers.append({"name": tech.upper(), "category": cat, "source": "job_descriptions"})
                    seen.add(tech)
        logger.info(f"Extracted {len(job_tech_markers)} tech markers from job text.")

    # 2. Web Footprint
    logger.info("\n--- Step 2: Capturing Intelligence from Web Footprint ---")
    web_markers = await scan_builtwith(domain)
    logger.info(f"Found {len(web_markers)} technology markers on BuiltWith.")

    # 3. Final Analysis
    all_detections = {m['name']: m for m in (job_tech_markers + web_markers)}
    final_list = list(all_detections.values())
    unique_cats = set(m['category'] for m in final_list)
    
    logger.info("\n--- ANALYTICAL SUMMARY ---")
    if not final_list:
        logger.error("RESULT: 0 DIGITAL PRESENCE SCORE")
        logger.info("Conclusion: JPM's high security or LinkedIn's naming convention is blocking both signals.")
    else:
        for m in final_list:
            logger.info(f" [+] DETECTED: {m['name']} ({m['category']})")
            
        score = min(len(final_list) * 10, 50) + min(len(unique_cats) * 12.5, 50)
        logger.info(f"SIMULATED SCORE: {score}/100")
        logger.info(f"CONFIDENCE: 0.85")

if __name__ == "__main__":
    asyncio.run(simulate_pipeline())
