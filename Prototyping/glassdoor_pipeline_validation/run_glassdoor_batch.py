import asyncio
import logging
import sys
import os

# Ensure app is in path
sys.path.append(os.getcwd())

from app.pipelines.glassdoor.glassdoor_orchestrator import GlassdoorOrchestrator
from app.pipelines.glassdoor.glassdoor_collector import COMPANY_IDS

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Initializing Glassdoor Orchestrator for Batch Run...")
    orchestrator = GlassdoorOrchestrator()
    
    # Transform COMPANY_IDS dict to list of dicts required by run_batch
    # COMPANY_IDS is { "NVDA": "7633", ... }
    companies = [
        {"ticker": ticker, "id": gid} 
        for ticker, gid in COMPANY_IDS.items()
    ]
    
    logger.info(f"Target Companies: {[c['ticker'] for c in companies]}")
    logger.info("Configuration: Limit=100, Force Refresh=True")
    
    try:
        # We use force_refresh=True to ensure we download fresh 100 reviews 
        # and don't just use the cached ones from verification.
        await orchestrator.run_batch(companies, limit=100, force_refresh=True)
        logger.info("Batch run completed successfully.")
    except Exception as e:
        logger.error(f"Batch run failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
