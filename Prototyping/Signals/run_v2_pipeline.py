import asyncio
import logging
import os
from pipelines_v2.orchestrator import MasterPipeline

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

async def main():
    # Ensure PatentsView key is available
    if not os.getenv("PATENTSVIEW_API_KEY"):
        logger.error("PATENTSVIEW_API_KEY not found in environment")
        return

    # Initialize MasterPipeline
    # bq_project is still passed for compatibility, but PatentCollector now uses PatentsView
    pipeline = MasterPipeline(bq_project="gen-lang-client-0720834968")
    
    company_name = "Caterpillar Inc."
    ticker = "CAT"
    
    logger.info(f"Running V2 MasterPipeline for {company_name} ({ticker})...")
    
    try:
        result = await pipeline.run(company_name, ticker)
        
        print("\n" + "="*50)
        print("PIPELINE EXECUTION SUMMARY")
        print("="*50)
        summary = result['summary']
        print(f"Company ID: {summary.get('company_id')}")
        print(f"Ticker: {summary.get('ticker')}")
        print(f"Composite Score: {summary.get('composite_score')}")
        print(f"Hiring Score: {summary.get('technology_hiring_score')}")
        print(f"Innovation Score: {summary.get('innovation_activity_score')}")
        print(f"Digital Score: {summary.get('digital_presence_score')}")
        print(f"Leadership Score: {summary.get('leadership_signals_score')}")
        print(f"Number of Signals: {result.get('signals', []).__len__()}")
        print("="*50 + "\n")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
