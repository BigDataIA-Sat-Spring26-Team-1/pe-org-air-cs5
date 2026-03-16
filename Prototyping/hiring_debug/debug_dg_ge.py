import asyncio
import logging
import re
import os
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple
from jobspy import scrape_jobs

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Debug-DG-GE")

class WebUtilsLite:
    @staticmethod
    def clean_company_name(name: str) -> str:
        suffixes = [r"\bInc\.?\b", r"\bCorp(oration)?\.?\b", r"\bLLC\b", r"\bLtd\.?\b"]
        clean = name
        for s in suffixes:
            clean = re.sub(s, "", clean, flags=re.IGNORECASE)
        return clean.strip()

class HiringCollectorDebug:
    AI_KEYWORDS = [
        "machine learning", "ml engineer", "data scientist",
        "artificial intelligence", "deep learning", "nlp",
        "computer vision", "llm", "generative ai", "genai",
        "pytorch", "tensorflow", "transformer", "gpt"
    ]

    TECH_TITLE_KEYWORDS = [
        "engineer", "developer", "programmer", "software",
        "data", "analyst", "scientist", "technical",
        "manager", "lead", "principal", "head", "specialist"
    ]

    def _is_tech_role(self, title: str) -> bool:
        if not title: return False
        return any(kw in title.lower() for kw in self.TECH_TITLE_KEYWORDS)

    def _analyze_description(self, text: str) -> bool:
        if not text: return False
        text = text.lower()
        return any(re.search(r'\b' + re.escape(kw) + r'\b', text) for kw in self.AI_KEYWORDS)

    async def collect(self, company_name: str, ticker: str = None, hours_old: int = 720):
        clean_name = WebUtilsLite.clean_company_name(company_name)
        
        # Testing multiple search variations
        queries = [
            clean_name,                                      # Broad
            f'"{clean_name}"',                               # Exact Quote
            f"{clean_name} software",                        # Targeted Tech
            f"{clean_name} data"                             # Targeted Data
        ]
        
        all_jobs_df = pd.DataFrame()
        total_attempts = 0
        total_success = 0
        
        print(f"\n--- Debugging: {company_name} ({ticker}) ---")
        
        loop = asyncio.get_event_loop()
        
        for q in queries:
            print(f"  > Searching: '{q}' (Hours: {hours_old})")
            try:
                # Synchronous call wrapped in executor
                df = await loop.run_in_executor(None, lambda: scrape_jobs(
                    site_name=["linkedin", "indeed", "glassdoor"], # Try multiple sites!
                    search_term=q,
                    location="USA",
                    results_wanted=10, # Keep small for debug speed
                    hours_old=hours_old, 
                    linkedin_fetch_description=True
                ))
                
                total_attempts += 1
                if df is not None and not df.empty:
                    print(f"    SUCCESS: Found {len(df)} jobs for '{q}'")
                    total_success += 1
                    all_jobs_df = pd.concat([all_jobs_df, df], ignore_index=True)
                    # Peek at first job
                    first_title = df.iloc[0].get('title', 'N/A')
                    first_company = df.iloc[0].get('company', 'N/A')
                    print(f"    Sample: {first_title} at {first_company}")
                else:
                    print(f"    WARNING: No jobs found for '{q}'")
                    
            except Exception as e:
                print(f"    ERROR executing scrape for '{q}': {e}")
                # Print stack trace if needed, but message is usually enough

        if all_jobs_df.empty:
            print(f"!!! FAILURE: Zero jobs found for {company_name} across all queries.")
            return

        # Deduplicate
        if 'job_url' in all_jobs_df.columns:
            start_len = len(all_jobs_df)
            all_jobs_df = all_jobs_df.drop_duplicates(subset=['job_url'])
            print(f"  > Deduplicated: {start_len} -> {len(all_jobs_df)} unique jobs.")
        
        # Analyze Content
        tech_count = 0
        ai_count = 0
        
        for _, row in all_jobs_df.iterrows():
            title = str(row.get('title', ''))
            desc = str(row.get('description', ''))
            
            is_tech = self._is_tech_role(title)
            is_ai = self._analyze_description(desc)
            
            if is_tech: tech_count += 1
            if is_ai: ai_count += 1
            
        print(f"  > Analysis Results:")
        print(f"    Total Unique Jobs: {len(all_jobs_df)}")
        print(f"    Tech Roles: {tech_count}")
        print(f"    AI Roles: {ai_count}")

async def run_debug():
    debugger = HiringCollectorDebug()
    
    # 1. DG (Dollar General)
    await debugger.collect("Dollar General", "DG", hours_old=720) # 30 days
    
    # 2. GE (General Electric)
    await debugger.collect("General Electric", "GE", hours_old=720)
    
    # 3. Test with longer duration if previous failed?
    # User suggestion: "Check if increasing the time duration... would be better"
    # Let's try 1440 (60 days) for DG specifically as a test
    print("\n--- Retrying DG with 60 days ---")
    await debugger.collect("Dollar General", "DG", hours_old=1440)

if __name__ == "__main__":
    asyncio.run(run_debug())
