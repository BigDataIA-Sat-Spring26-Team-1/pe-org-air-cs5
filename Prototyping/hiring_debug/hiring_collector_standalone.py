import asyncio
import logging
import re
import os
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple
from jobspy import scrape_jobs

# Simulating WebUtils for standalone
class WebUtilsLite:
    @staticmethod
    def clean_company_name(name: str) -> str:
        suffixes = [r"\bInc\.?\b", r"\bCorp(oration)?\.?\b", r"\bLLC\b", r"\bLtd\.?\b"]
        clean = name
        for s in suffixes:
            clean = re.sub(s, "", clean, flags=re.IGNORECASE)
        return clean.strip()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Hiring-Standalone")

class HiringCollectorStandalone:
    AI_KEYWORDS = [
        "machine learning", "ml engineer", "data scientist",
        "artificial intelligence", "deep learning", "nlp",
        "natural language processing", "computer vision", "mlops",
        "ai engineer", "pytorch", "tensorflow", "llm",
        "large language model", "generative ai", "genai",
        "transformer", "bert", "gpt", "rag", "vector database"
    ]

    TECH_TITLE_KEYWORDS = [
        "engineer", "developer", "programmer", "software",
        "data", "analyst", "scientist", "technical",
        "manager", "lead", "principal", "head", "specialist"
    ]

    def __init__(self, data_dir: str = "data/raw"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _is_tech_role(self, title: str) -> bool:
        return any(kw in title.lower() for kw in self.TECH_TITLE_KEYWORDS)

    def _analyze_description(self, text: str) -> Tuple[bool, List[str]]:
        text = text.lower()
        is_ai = any(re.search(r'\b' + re.escape(kw) + r'\b', text) for kw in self.AI_KEYWORDS)
        return is_ai, []

    async def collect(self, company_name: str, ticker: str = None):
        clean_name = WebUtilsLite.clean_company_name(company_name)
        
        # WE RUN MULTIPLE STRATEGIES AND COMBINE THEM
        queries = [
            clean_name,                                      # Broad
            f"{clean_name} AI",                              # Targeted AI
            f"{clean_name} Data Science"                    # Targeted Data
        ]
        
        all_jobs_df = pd.DataFrame()
        
        for q in queries:
            logger.info(f"   [Query] Scoping: {q}")
            try:
                loop = asyncio.get_event_loop()
                df = await loop.run_in_executor(None, lambda: scrape_jobs(
                    site_name=["linkedin"],
                    search_term=q,
                    location="USA",
                    results_wanted=20,
                    hours_old=720, 
                    linkedin_fetch_description=True
                ))
                if not df.empty:
                    all_jobs_df = pd.concat([all_jobs_df, df], ignore_index=True)
            except Exception as e:
                logger.error(f"      Scrape failed for {q}: {e}")

        if all_jobs_df.empty:
            return {"score": 0, "ai_count": 0, "tech_count": 0, "total_found": 0}

        # DEDUPLICATION is critical when combining strategies
        if 'job_url' in all_jobs_df.columns:
            all_jobs_df = all_jobs_df.drop_duplicates(subset=['job_url'])
        
        tech_count = 0
        ai_count = 0
        found_processed = 0
        
        for _, row in all_jobs_df.iterrows():
            title = str(row.get('title', '')).lower()
            desc = str(row.get('description', '')).lower()
            
            is_tech = self._is_tech_role(title)
            is_ai, _ = self._analyze_description(desc)
            
            # Title fallback
            if not is_ai and any(kw in title for kw in ["ai", "machine learning", "data scientist"]):
                is_ai = True
                
            if is_tech or is_ai:
                found_processed += 1
                tech_count += 1
                if is_ai:
                    ai_count += 1

        ai_ratio = ai_count / tech_count if tech_count > 0 else 0
        # Balancing Ratio (Consistency) + Volume (Momentum)
        score = (ai_ratio * 40) + (min(ai_count / 10, 1) * 60)
        
        return {
            "score": round(score, 2),
            "ai_count": ai_count,
            "tech_count": tech_count,
            "total_found": len(all_jobs_df),
            "processed": found_processed
        }

async def run_audit():
    companies = [
        ("Walmart Inc.", "WMT"),
        ("JPMorgan Chase", "JPM"),
        ("Caterpillar Inc.", "CAT"),
        ("Goldman Sachs", "GS")
    ]
    collector = HiringCollectorStandalone()
    
    print(f"{'Company':<20} | {'Score':<6} | {'AI/Tech':<8} | {'Deduplicated Total'}")
    print("-" * 70)
    
    for name, ticker in companies:
        res = await collector.collect(name, ticker)
        print(f"{name:<20} | {res['score']:<6} | {res['ai_count']:>2}/{res['tech_count']:<5} | {res['total_found']}")
        await asyncio.sleep(2) # Avoid being too aggressive

if __name__ == "__main__":
    asyncio.run(run_audit())
