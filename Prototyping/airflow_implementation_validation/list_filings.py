
import os
from collections import defaultdict

XCOM_DIR = "/Users/AbhinavPiyush/Desktop/BigData/BigDataProjects/pe-org-air-cs3/pe-org-air-platform/data/temp_xcom"

def list_processed_filings():
    if not os.path.exists(XCOM_DIR):
        print(f"Directory not found: {XCOM_DIR}")
        print("Note: If running inside Docker, this path might be different.")
        return

    files = [f for f in os.listdir(XCOM_DIR) if f.endswith('.json')]
    
    if not files:
        print("No processed filing data found in temp_xcom.")
        return

    company_counts = defaultdict(int)
    print(f"\n--- Processed Filings ({len(files)} total) ---")
    
    for f in files:
        # Filename format: TICKER_ACCESSION.json
        parts = f.split('_')
        if len(parts) >= 2:
            ticker = parts[0]
            accession = parts[1].replace('.json', '')
            company_counts[ticker] += 1
            # print(f"  - {ticker}: {accession}") # Uncomment to list every single file
            
    print("\n--- Summary by Company ---")
    for ticker, count in sorted(company_counts.items()):
        print(f"{ticker}: {count} filings")

if __name__ == "__main__":
    list_processed_filings()
