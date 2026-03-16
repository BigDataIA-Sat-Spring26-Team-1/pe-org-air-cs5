import asyncio
import logging
import os
import pandas as pd
from datetime import datetime
from pipelines_v2.orchestrator import MasterPipeline

# Setup concise logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("batch_v2.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def run_batch():
    # Verify API Key
    if not os.getenv("PATENTSVIEW_API_KEY"):
        logger.error("PATENTSVIEW_API_KEY environment variable not set. Patent collection will fail.")
        # But we continue to see if other collectors work
        
    pipeline = MasterPipeline(bq_project="gen-lang-client-0720834968")
    
    # Full list from Table 1 screenshot
    companies = [
        {"name": "Caterpillar Inc.", "ticker": "CAT"},
        {"name": "Deere & Company", "ticker": "DE"},
        {"name": "UnitedHealth Group", "ticker": "UNH"},
        {"name": "HCA Healthcare", "ticker": "HCA"},
        {"name": "Automatic Data Processing", "ticker": "ADP"},
        {"name": "Paychex Inc.", "ticker": "PAYX"},
        {"name": "Walmart Inc.", "ticker": "WMT"},
        {"name": "Target Corporation", "ticker": "TGT"},
        {"name": "JPMorgan Chase", "ticker": "JPM"},
        {"name": "Goldman Sachs", "ticker": "GS"}
    ]
    
    results_summary = []
    all_signals = []
    
    print("\n" + "="*60)
    print("STARTING V2 PIPELINE BATCH EXECUTION (FULL LIST)")
    print("="*60 + "\n")
    
    for company in companies:
        try:
            print(f"\n🚀 Processing: {company['name']} ({company['ticker']})...")
            result = await pipeline.run(company["name"], company["ticker"])
            
            summary = result['summary']
            signals = result['signals']
            
            results_summary.append(summary)
            all_signals.extend(signals)
            
            print(f"✅ COMPLETED: {company['name']}")
            print(f"   Composite Score: {summary['composite_score']}")
            print("-" * 40)
            
            # Incremental save to prevent data loss
            pd.DataFrame(results_summary).to_csv("batch_results_v2_summary.csv", index=False)
            
        except Exception as e:
            logger.error(f"❌ FAILED: {company['name']} - {str(e)}")
            import traceback
            traceback.print_exc()
            
        # Buffer between companies to be polite to APIs
        await asyncio.sleep(2)

    # Final Save
    if results_summary:
        df_summary = pd.DataFrame(results_summary)
        df_summary.to_csv("batch_results_v2_summary.csv", index=False)
        print(f"\n✨ Batch Summary saved to batch_results_v2_summary.csv")

    if all_signals:
        # We need to flatten metadata for CSV if possible, or just save as JSON string
        import json
        for s in all_signals:
            if isinstance(s.get('metadata'), dict):
                s['metadata'] = json.dumps(s['metadata'])
        
        df_signals = pd.DataFrame(all_signals)
        df_signals.to_csv("batch_results_v2_signals.csv", index=False)
        print(f"✨ Detailed Signals saved to batch_results_v2_signals.csv")

    print("\n" + "="*60)
    print("BATCH EXECUTION COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(run_batch())
