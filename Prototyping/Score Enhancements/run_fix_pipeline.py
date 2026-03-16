import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables early
load_dotenv('../pe-org-air-platform/.env', override=True)

# Add platform to path
sys.path.append(os.path.abspath('../pe-org-air-platform'))

from app.pipelines.integration_pipeline import IntegrationPipeline
from app.services.snowflake import db

async def run_fix_batch():
    load_dotenv('../pe-org-air-platform/.env')
    pipeline = IntegrationPipeline()
    
    tickers = ['NVDA', 'JPM', 'WMT', 'GE', 'DG']
    print(f"Starting integration pipeline for {tickers}...")
    
    for ticker in tickers:
        try:
            print(f"Processing {ticker}...")
            # run_integration handles the whole flow
            await pipeline.run_integration(ticker)
            print(f"Completed {ticker}")
        except Exception as e:
            print(f"Error processing {ticker}: {e}")

if __name__ == "__main__":
    asyncio.run(run_fix_batch())
