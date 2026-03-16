import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to sys.path for imports
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent / "pe-org-air-platform"
sys.path.append(str(project_root))

from app.pipelines.external_signals.job_collector import JobCollector

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Hiring-Batch-Audit")

TARGET_COMPANIES = {
    "CAT": "Caterpillar Inc.",
    "WMT": "Walmart Inc.",
    "JPM": "JPMorgan Chase",
}

async def run_audit():
    collector = JobCollector(output_file="audit_processed_jobs.csv")
    results = []

    logger.info(f"=== STARTING HIRING AUDIT FOR {len(TARGET_COMPANIES)} COMPANIES ===")
    
    for ticker, name in TARGET_COMPANIES.items():
        logger.info(f"\n>>> AUDITING: {name} ({ticker})")
        try:
            # Using 14 days to get a good sample without overloading
            result = await collector.collect(name, ticker=ticker, days=14)
            
            summary = {
                "ticker": ticker,
                "name": name,
                "score": result.normalized_score,
                "tech_count": result.metadata.get("tech_count", 0),
                "ai_count": result.metadata.get("ai_count", 0),
                "found_jobs": result.metadata.get("count", 0),
                "raw_total": 0, # To be filled if possible
                "skills": result.metadata.get("skills", [])
            }
            results.append(summary)
            
            logger.info(f"    RESULT: Score={summary['score']}, AI Roles={summary['ai_count']}/{summary['tech_count']}")
            if summary['score'] == 0:
                logger.warning(f"    DIAGNOSTIC: {ticker} got 0. Found {summary['found_jobs']} matched jobs. Tech count: {summary['tech_count']}")
                # Look at the raw file
                cache_file = Path("pe-org-air-platform/data/raw") / f"raw_jobs_{ticker}.csv"
                if cache_file.exists():
                    raw_df = pd.read_csv(cache_file)
                    logger.info(f"    RAW CACHE: {len(raw_df)} total jobs in file.")
                    if not raw_df.empty:
                        logger.info(f"    SAMPLE TITLES: {raw_df['title'].head(3).tolist()}")
                        companies = raw_df['company'].unique().tolist() if 'company' in raw_df.columns else []
                        logger.info(f"    RAW COMPANIES: {companies[:5]}")
            
            if summary['skills']:
                logger.info(f"    SKILLS: {', '.join(summary['skills'][:5])}...")
        except Exception as e:
            logger.error(f"    FAILED for {ticker}: {e}")

        # Sleep to be respectful to LinkedIn/API
        await asyncio.sleep(5)

    logger.info("\n=== FINAL AUDIT SUMMARY ===")
    print(f"{'Ticker':<6} | {'Score':<6} | {'AI/Tech':<10} | {'Name'}")
    print("-" * 50)
    for r in results:
        print(f"{r['ticker']:<6} | {r['score']:<6} | {r['ai_count']:>2}/{r['tech_count']:<7} | {r['name']}")

if __name__ == "__main__":
    asyncio.run(run_audit())
