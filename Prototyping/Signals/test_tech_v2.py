import asyncio
import logging
from pipelines_v2.tech_stack_collector import TechStackCollector

logging.basicConfig(level=logging.INFO)

async def test_tech():
    collector = TechStackCollector()
    # Test for Caterpillar which has markers
    res = await collector.collect("Caterpillar Inc.")
    print(f"Score: {res.normalized_score}")
    print(f"Stack: {res.metadata.get('stack')}")
    print(f"Record: {res.raw_value}")

if __name__ == "__main__":
    asyncio.run(test_tech())
