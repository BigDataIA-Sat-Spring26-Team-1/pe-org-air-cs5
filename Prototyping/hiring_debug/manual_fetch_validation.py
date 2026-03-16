import asyncio
import logging
import re
import pandas as pd
from jobspy import scrape_jobs

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Manual-Validation")

class HiringCollectorValidation:
    # Standard Keywords from the standalone collector
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

    def _is_tech_role(self, title: str) -> bool:
        if not title: return False
        return any(kw in title.lower() for kw in self.TECH_TITLE_KEYWORDS)

    def _analyze_description(self, text: str) -> bool:
        if not text: return False
        text = text.lower()
        return any(re.search(r'\b' + re.escape(kw) + r'\b', text) for kw in self.AI_KEYWORDS)

    async def validate_company(self, name: str, ticker: str, hours_old: int = 720):
        print(f"\n--- Validating: {name} ({ticker}) [Last {hours_old} hours] ---")
        
        # Using the standard "Broad" + "Targeted" search strategy
        queries = [
            name,                            # Broad
            f"{name} AI",                    # Targeted AI
            f"{name} Data Science",          # Targeted Data
            f"{name} Software Engineer",      # Targeted Tech (Added for robustness)
            f"{name} ML/AI"                   # Experimental: Combined ML/AI query
        ]
        
        all_jobs_df = pd.DataFrame()
        
        loop = asyncio.get_event_loop()
        
        for q in queries:
            print(f"  > Scrape Query: '{q}'")
            try:
                # Fetch more results since we are validating volume (limit 50 per query)
                df = await loop.run_in_executor(None, lambda: scrape_jobs(
                    site_name=["linkedin", "indeed", "glassdoor"],
                    search_term=q,
                    location="USA",
                    results_wanted=100, 
                    hours_old=hours_old, 
                    linkedin_fetch_description=True
                ))
                
                if df is not None and not df.empty:
                    print(f"    Found {len(df)} raw jobs.")
                    all_jobs_df = pd.concat([all_jobs_df, df], ignore_index=True)
                else:
                    print("    Found 0 jobs.")
                    
            except Exception as e:
                print(f"    Error: {e}")

        if all_jobs_df.empty:
            print(f"!!! No jobs found for {name}.")
            return

        # Deduplicate by URL
        original_count = len(all_jobs_df)
        if 'job_url' in all_jobs_df.columns:
            all_jobs_df = all_jobs_df.drop_duplicates(subset=['job_url'])
        
        dedup_count = len(all_jobs_df)
        print(f"  > Consolidated: {original_count} -> {dedup_count} unique jobs.")

        # Apply "Normal Filtering"
        tech_count = 0
        ai_count = 0
        
        print("  > Applying Filters...")
        for _, row in all_jobs_df.iterrows():
            title = str(row.get('title', ''))
            desc = str(row.get('description', ''))
            
            is_tech = self._is_tech_role(title)
            is_ai = self._analyze_description(desc)
            
            # Title fallback logic used in collector
            if not is_ai and any(kw in title.lower() for kw in ["ai", "machine learning", "data scientist"]):
                is_ai = True
            
            if is_tech or is_ai:
                tech_count += 1
            
            if is_ai:
                ai_count += 1
        
        print(f"  > Final Counts for {ticker} (30 Days):")
        print(f"    Total Tech Roles: {tech_count}")
        print(f"    Total AI Roles:   {ai_count}")
        print(f"    AI/Tech Ratio:    {ai_count/tech_count:.2f}" if tech_count > 0 else "    AI/Tech Ratio:    0.0")

async def run():
    validator = HiringCollectorValidation()
    
    # 1. NVIDIA
    # await validator.validate_company("NVIDIA", "NVDA", 720)
    
    # 2. JPMorgan Chase
    await validator.validate_company("JPMorgan Chase", "JPM", 720)
    
    # 3. Walmart
    # await validator.validate_company("Walmart", "WMT", 720)

if __name__ == "__main__":
    asyncio.run(run())
