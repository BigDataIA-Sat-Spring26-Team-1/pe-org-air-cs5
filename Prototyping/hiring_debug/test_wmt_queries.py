import asyncio
import pandas as pd
from jobspy import scrape_jobs
import re

async def test_wmt():
    queries = ["Walmart", "Walmart AI", "Walmart Technology"]
    for q in queries:
        print(f"\n--- Testing Query: {q} ---")
        try:
            df = scrape_jobs(
                site_name=["linkedin"],
                search_term=q,
                location="USA",
                results_wanted=20,
            )
            if df.empty:
                print(f"No jobs found for {q}")
                continue
            
            print(f"Found {len(df)} jobs.")
            print("Sample Titles:")
            for t in df['title'].head(5).tolist():
                print(f" - {t}")
                
            tech_keywords = ["engineer", "developer", "data", "scientist", "analyst", "tech"]
            tech_jobs = [t for t in df['title'].tolist() if any(kw in str(t).lower() for kw in tech_keywords)]
            print(f"Tech jobs matched: {len(tech_jobs)}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_wmt())
