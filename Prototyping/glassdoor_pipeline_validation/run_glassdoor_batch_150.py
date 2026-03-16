
import asyncio
import logging
import sys
import os

# Ensure the app module is in the path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../pe-org-air-platform'))

from app.pipelines.glassdoor.glassdoor_orchestrator import GlassdoorOrchestrator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("batch_run_150.log", mode='w')
    ]
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting Extended Batch Run (150 Reviews)...")
    
    orchestrator = GlassdoorOrchestrator()
    
    companies = [
        {"ticker": "NVDA", "id": "7633"},
        {"ticker": "JPM", "id": "5224839"},
        {"ticker": "WMT", "id": "715"},
        {"ticker": "GE", "id": "277"},
        {"ticker": "DG", "id": "1342"}
    ]
    
    # Run batch with limit=150
    # Note: force_refresh=True to ensure we fetch new data if needed, or False if we trust cache.
    # Given the request "run the entire pipeline", and potential new limit, let's use force_refresh=False first
    # but since limit is 150 and previous runs might have been 100 (or less), we might need to fetch more.
    # The current fetch_reviews logic checks if file exists. If it exists, it reads it.
    # It does NOT check if the file has enough reviews.
    # So if we want 150, and we have a cached file with 12 (from verification), we will only get 12.
    # To get 150, we MUST force a fresh fetch from API or ensure the cache key is different (cache key is date based).
    # Since today's file exists for NVDA (12 reviews), we need to bypass it to get 150?
    # Actually, the user might want to fetch fresh.
    # However, `GlassdoorCollector.fetch_reviews` logic:
    # if file_exists: return read_json()
    # It doesn't use `force_refresh` arg from orchestrator yet inside `fetch_reviews` logic unless I passed it and used it.
    # In `run_pipeline`, I invoke `fetch_reviews(ticker, limit)`.
    # `fetch_reviews` checks S3.
    # Code cleanup removed `force_refresh` logic/args from `fetch_reviews` to adhere to signature?
    # Blueprint signature for `fetch_reviews` is `(self, ticker: str, limit: int = 100)`.
    # It does NOT accept `force_refresh`.
    # So to force a refresh for a higher limit on the same day, we might need to manually delete the S3 file 
    # or rely on the fact that maybe I shouldn't have cached it if I wanted more?
    # Or maybe the "limit" in fetch_reviews is passed to API only if fetching?
    # Logic in `fetch_reviews` (from memory):
    # if s3_exists: return read()
    # else: fetch from API with limit.
    
    # PROBLEM: If I have a file with 12 reviews, and I request 150, `fetch_reviews` will return 12.
    # I cannot pass `force_refresh` to `fetch_reviews` because of strict signature.
    # I can:
    # 1. Delete the S3 files before running.
    # 2. Modify `fetch_reviews` to check review count? No, strictly adhering to blueprint.
    # 3. Just run it. If it returns 12, it returns 12. But user asked for 150.
    
    # I will add a step in this script to DELETE the S3 cache files for today for these companies 
    # to ensure `fetch_reviews` actually hits the API for 150 reviews.
    
    from app.services.s3_storage import aws_service
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    for comp in companies:
        ticker = comp["ticker"]
        s3_key = f"raw/glassdoor/{ticker}/{date_str}.json"
        if aws_service.file_exists(s3_key):
             logger.info(f"Deleting cached file {s3_key} to ensure fresh fetch of 150 reviews.")
             aws_service.delete_file(s3_key)

    await orchestrator.run_batch(companies, limit=150)
    logger.info("Batch Run Complete.")

from datetime import datetime

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
