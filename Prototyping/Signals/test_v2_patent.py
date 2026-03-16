import asyncio
import logging
import os
from pipelines_v2.patent_collector import PatentCollector

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

async def test_patent_collector():
    # PatentsView key should be in env
    api_key = os.getenv("PATENTSVIEW_API_KEY")
    if not api_key:
        logger.error("PATENTSVIEW_API_KEY not found in environment")
        return

    # In pipelines_v2, PatentCollector now uses PatentsView
    collector = PatentCollector(project_id="dummy-project")
    
    company = "Caterpillar Inc."
    logger.info(f"Testing PatentCollector (V2 with PatentsView) for {company}...")
    
    result = await collector.collect(company)
    
    print("\n--- TEST RESULT ---")
    print(f"Category: {result.category}")
    print(f"Score: {result.normalized_score}")
    print(f"Confidence: {result.confidence}")
    print(f"Source: {result.source}")
    print(f"Raw Value: {result.raw_value}")
    print(f"Metadata Summary: {list(result.metadata.keys())}")
    if "representative_patents" in result.metadata:
        print(f"Sample Patent: {result.metadata['representative_patents'][0] if result.metadata['representative_patents'] else 'None'}")
    print("-------------------\n")

if __name__ == "__main__":
    asyncio.run(test_patent_collector())
