import asyncio
import json
import os
import pandas as pd
from datetime import datetime, timezone
from pipelines.orchestrator import PipelineOrchestrator

companies = [
    {"ticker": "CAT", "name": "Caterpillar Inc."},
    {"ticker": "DE",  "name": "Deere & Company"},
    {"ticker": "UNH", "name": "UnitedHealth Group"},
    {"ticker": "HCA", "name": "HCA Healthcare"},
    {"ticker": "ADP", "name": "Automatic Data Processing"},
    {"ticker": "PAYX", "name": "Paychex Inc."},
    {"ticker": "WMT", "name": "Walmart Inc."},
    {"ticker": "TGT", "name": "Target Corporation"},
    {"ticker": "JPM", "name": "JPMorgan Chase"},
    {"ticker": "GS",  "name": "Goldman Sachs"}
]

async def run_batch():
    # Initialize orchestrator with BigQuery project
    orc = PipelineOrchestrator(bq_project="gen-lang-client-0720834968")
    
    all_summaries = []
    
    print(f"Starting stabilized batch run for {len(companies)} companies...")
    
    for company in companies:
        print(f"\n>>> Processing {company['ticker']} ({company['name']})...")
        try:
            result = await orc.execute(company['name'], company['ticker'])
            all_summaries.append(result["summary"])
            
            # Save progress incrementally
            df = pd.DataFrame(all_summaries)
            df.to_csv("orchestrator_results.csv", index=False)
            
            # Small delay to prevent rate limits
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"!!! Error processing {company['ticker']}: {e}")

    print("\n" + "="*50)
    print("ORCHESTRATOR BATCH RUN COMPLETE")
    print("="*50)
    print(pd.DataFrame(all_summaries)[['ticker', 'composite_score', 'technology_hiring_score', 'innovation_activity_score', 'digital_presence_score', 'leadership_signals_score']])

if __name__ == "__main__":
    asyncio.run(run_batch())
