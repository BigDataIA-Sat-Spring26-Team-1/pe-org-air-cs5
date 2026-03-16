
import asyncio
import sys
import argparse
from app.pipelines.integration_pipeline import integration_pipeline

async def main():
    parser = argparse.ArgumentParser(description="Run Integration Pipeline for Case Study 3")
    parser.add_argument("ticker", help="Company ticker symbol (e.g., NVDA, CAT)")
    args = parser.parse_args()

    print(f"--- Running Integration Pipeline for {args.ticker} ---")
    result = await integration_pipeline.run_integration(args.ticker)
    
    if "error" in result:
        print(f"Error: {result['error']}")
        sys.exit(1)
    
    print("\n--- Results ---")
    print(f"Company ID: {result['company_id']}")
    print(f"Signals Added/Updated: {result['signals_added']}")
    print("\nScores:")
    for key, val in result["scores"].items():
        print(f"  {key}: {float(val):.2f}")
    
    final = result["final_score"]
    print(f"\nFinal Org-AI-R Score: {final['org_air_score']:.2f}")
    print(f"Confidence: {final['confidence']:.2f}")
    print(f"95% CI: [{final['ci_lower']:.2f}, {final['ci_upper']:.2f}]")
    print("---------------------------------------------")

if __name__ == "__main__":
    asyncio.run(main())
