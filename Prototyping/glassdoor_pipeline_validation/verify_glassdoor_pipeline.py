
import asyncio
import logging
import sys
import os

# Ensure the app module is in the path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../pe-org-air-platform'))

from datetime import datetime
from app.pipelines.glassdoor.glassdoor_orchestrator import GlassdoorOrchestrator
from app.services.s3_storage import aws_service
from app.services.snowflake import db

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("verification_run.log", mode='w')
    ]
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting Glassdoor Pipeline Verification...")
    
    # 1. Setup
    ticker = "NVDA"
    # Force a unique S3 key for testing if needed, or just let it use date
    # Ideally we want to test the full flow, so we might want to ensure no file exists if we want to test API fetching.
    # checking if text exists
    date_str = datetime.now().strftime("%Y-%m-%d")
    s3_key = f"raw/glassdoor/{ticker}/{date_str}.json"
    
    logger.info(f"Checking S3 for {s3_key}...")
    exists = aws_service.file_exists(s3_key)
    if exists:
        logger.info("File already exists in S3. Pipeline will use cached data.")
    else:
        logger.info("File not in S3. Pipeline should fetch from API.")

    # 2. Run Orchestrator
    orchestrator = GlassdoorOrchestrator()
    
    # Use a limit > 10 to test pagination
    limit = 12 
    logger.info(f"Running pipeline for {ticker} with limit={limit}...")
    
    await orchestrator.run_pipeline(ticker, limit=limit)
    
    # 3. Verify S3
    logger.info("Verifying S3 file creation...")
    if aws_service.file_exists(s3_key):
        logger.info(f"SUCCESS: S3 file found at {s3_key}")
    else:
        logger.error(f"FAILURE: S3 file NOT found at {s3_key}")

    # 4. Verify Snowflake
    logger.info("Verifying Snowflake insertions...")
    
    # Check Reviews
    reviews = await db.fetch_all(f"SELECT * FROM glassdoor_reviews WHERE ticker = '{ticker}' ORDER BY review_date DESC LIMIT 5")
    logger.info(f"Found {len(reviews)} reviews in Snowflake for {ticker} (showing max 5).")
    if reviews:
        logger.info(f"Sample review title: {reviews[0].get('title')}")
    
    # Check Culture Signal
    # Using batch_date = current date
    today = datetime.now().strftime("%Y-%m-%d")
    signal = await db.fetch_all(f"SELECT * FROM culture_scores WHERE ticker = '{ticker}' AND batch_date = '{today}'")
    
    if signal:
        logger.info(f"SUCCESS: Culture Signal found for {ticker} on {today}")
        logger.info(f"Signal Data: {signal[0]}")
    else:
        logger.error(f"FAILURE: No Culture Signal found for {ticker} on {today}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
