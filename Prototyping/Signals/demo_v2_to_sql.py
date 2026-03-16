import asyncio
import json
from pipelines_v2.orchestrator import MasterPipeline

async def demo():
    # We use a dummy project ID here
    pipeline = MasterPipeline(bq_project="your-gcp-project")
    
    print("--- Running V2 Pipeline for Caterpillar (CAT) ---")
    # Caterpillar is our verified benchmark
    result = await pipeline.run("Caterpillar Inc.", "CAT")
    
    summary = result["summary"]
    signals = result["signals"]
    
    print("\n--- [DATABASE UPLOAD PLAN] ---")
    
    print("\n1. Insert into COMPANY_SIGNAL_SUMMARIES:")
    print("Columns: ID, TICKER, HIRING_SCORE, INNOVATION_SCORE, DIGITAL_SCORE, LEADERSHIP_SCORE, COMPOSITE, LAST_UPDATED")
    print(f"Values: {summary['company_id']}, {summary['ticker']}, {summary['technology_hiring_score']}, {summary['innovation_activity_score']}, {summary['digital_presence_score']}, {summary['leadership_signals_score']}, {summary['composite_score']}, {summary['last_updated']}")
    
    print("\n2. Insert into EXTERNAL_SIGNALS (Multiple Rows):")
    print("Columns: ID, COMPANY_ID, CATEGORY, SOURCE, DATE, VALUE, SCORE, CONFIDENCE, METADATA(JSON)")
    for s in signals:
        # Truncate metadata for display
        meta_disp = str(s['metadata'])[:80] + "..."
        print(f"Row: {s['category']} | Score: {s['normalized_score']} | Data: {meta_disp}")

    print("\nReady for Snowflake ingestion.")

if __name__ == "__main__":
    asyncio.run(demo())
