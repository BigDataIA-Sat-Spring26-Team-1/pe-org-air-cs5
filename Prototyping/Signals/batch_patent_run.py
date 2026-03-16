import asyncio
import os
import sys

# Ensure current directory is in path so we can import the pipeline
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from patent_pipeline_v2 import PatentSignalCollectorPatentsView

# Companies from Table 1
COMPANIES = [
    "Caterpillar Inc.",
    "Deere & Company",
    "UnitedHealth Group",
    "HCA Healthcare",
    "Automatic Data Processing",
    "Paychex Inc.",
    "Walmart Inc.",
    "Target Corporation",
    "JPMorgan Chase",
    "Goldman Sachs"
]

async def main():
    if not os.getenv("PATENTSVIEW_API_KEY"):
        print("Error: PATENTSVIEW_API_KEY environment variable not set.")
        return

    collector = PatentSignalCollectorPatentsView()
    
    for company in COMPANIES:
        print(f"\n========================================")
        print(f"Starting collection for: {company}")
        print(f"========================================")
        try:
            await collector.run(company_name=company, years=5)
            print(f"-> Successfully completed {company}")
        except Exception as e:
            print(f"-> Error collecting for {company}: {e}")
            
        # Small buffer
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
