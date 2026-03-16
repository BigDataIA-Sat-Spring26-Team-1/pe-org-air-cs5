import asyncio
import json
import logging
from typing import List, Dict, Any
from pipelines_v2.orchestrator import MasterPipeline

# Setup basic logging for the batch run
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# List of target companies for the AI Audit
TARGET_COMPANIES = [
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

async def run_batch_audit():
    """
    Processes all target companies through the V2 pipeline.
    Results are aggregated and formatted for database ingestion (Snowflake).
    """
    # Initialize the master pipeline
    # bq_project is needed for initialization even if patents are skipped
    pipeline = MasterPipeline(bq_project="gen-lang-client-0720834968")
    
    all_summary_results = []
    all_detailed_signals = []
    
    logger.info(f"Starting batch AI Audit for {len(TARGET_COMPANIES)} companies...")
    
    for company in TARGET_COMPANIES:
        ticker = company["ticker"]
        name = company["name"]
        
        logger.info(f"\n>>> AUDITING: {ticker} | {name}")
        
        try:
            # We use a 30-second timeout per audit to keep the batch moving
            # although some scrapers might take longer if they hit retries.
            result = await pipeline.run(name, ticker)
            
            all_summary_results.append(result["summary"])
            all_detailed_signals.extend(result["signals"])
            
            # Temporary local save after each company to prevent data loss
            with open("summary_results_v2.json", "w") as f:
                json.dump(all_summary_results, f, indent=4, default=str)
            
            with open("detailed_signals_v2.json", "w") as f:
                json.dump(all_detailed_signals, f, indent=4, default=str)
                
            # Rate limiting: wait a bit between companies to avoid IP blocks
            logger.info("Audit successful. Resting for 5 seconds...")
            await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"Audit failed for {ticker}: {str(e)}")

    logger.info("\n" + "="*50)
    logger.info("BATCH AUDIT COMPLETE")
    logger.info("="*50)
    logger.info(f"Summary records generated: {len(all_summary_results)}")
    logger.info(f"Detailed signals generated: {len(all_detailed_signals)}")
    logger.info("Results saved to summary_results_v2.json and detailed_signals_v2.json")

if __name__ == "__main__":
    asyncio.run(run_batch_audit())
