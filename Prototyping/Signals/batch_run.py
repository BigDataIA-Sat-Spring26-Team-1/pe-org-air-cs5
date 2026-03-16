import asyncio
import subprocess
import time
import pandas as pd
import os

companies = ["CAT", "DE", "UNH", "HCA", "ADP", "PAYX", "WMT", "TGT", "JPM", "GS"]

async def run_pipelines():
    print(f"Starting batch run for {len(companies)} companies...")
    for company in companies:
        print(f"\n>>> Running pipeline for {company}...")
        try:
            # Run the command and wait for it to finish
            process = subprocess.run(
                ["uv", "run", "master_pipeline.py", "--company", company, "--days", "7"],
                check=True
            )
            print(f"<<< Completed {company}")
            # Smaller delay since we have many companies and BigQuery is fast
            time.sleep(5)
        except Exception as e:
            print(f"!!! Failed {company}: {e}")

    # After running all, show the results
    print("\n" + "="*50)
    print("BATCH RUN COMPLETE - RESULTS SUMMARY")
    print("="*50)
    if os.path.exists("company_summaries.csv"):
        df = pd.read_csv("company_summaries.csv")
        # Filter for the companies we just ran
        results = df[df['ticker'].isin(companies)]
        print(results[['ticker', 'composite_score', 'technology_hiring_score', 'innovation_activity_score', 'digital_presence_score', 'leadership_signals_score']])
    else:
        print("No results found in company_summaries.csv")

if __name__ == "__main__":
    asyncio.run(run_pipelines())
