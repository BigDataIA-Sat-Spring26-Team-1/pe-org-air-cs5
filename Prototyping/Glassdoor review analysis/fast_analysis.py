import pandas as pd
from collections import defaultdict

def main():
    csv_path = '/Users/aakashbelide/Aakash/Higher Studies/Course/Sem-4/DAMG 7245/Case Study 3/pe-org-air-cs3/all_reviews.csv'
    
    # First, let's just peek at the first 1000 rows to understand the data structure
    print("Reading first 1000 rows to understand data structure...")
    sample_df = pd.read_csv(csv_path, nrows=1000)
    
    print("\n" + "=" * 100)
    print("SAMPLE FIRM_LINKS (first 50 unique):")
    print("=" * 100)
    unique_links = sample_df['firm_link'].unique()[:50]
    for i, link in enumerate(unique_links, 1):
        print(f"{i:2d}. {link}")
    
    # Now let's search for our target companies more efficiently
    # Only reading the firm_link column
    print("\n" + "=" * 100)
    print("Searching for target companies (reading only firm_link column)...")
    print("=" * 100)
    
    companies_to_find = {
        'NVDA': ['nvidia', 'nvda'],
        'JPM': ['jpmorgan', 'jp-morgan', 'jpm', 'chase'],
        'WMT': ['walmart', 'wal-mart', 'wmt'],
        'GE': ['general-electric', 'generalelectric', 'ge-'],
        'DG': ['dollar-general', 'dollargeneral', 'dg-']
    }
    
    # Count matches using chunking for efficiency
    chunk_size = 500000  # Process 500k rows at a time
    company_counts = defaultdict(int)
    total_rows = 0
    chunk_num = 0
    
    print("\nProcessing file in chunks...")
    for chunk in pd.read_csv(csv_path, usecols=['firm_link'], chunksize=chunk_size, low_memory=False):
        chunk_num += 1
        total_rows += len(chunk)
        print(f"  Processing chunk {chunk_num} ({total_rows:,} rows processed so far)...", end='\r')
        
        for ticker, search_terms in companies_to_find.items():
            for term in search_terms:
                matches = chunk[chunk['firm_link'].str.contains(term, case=False, na=False)]
                if len(matches) > 0:
                    company_counts[ticker] += len(matches)
                    # Store sample links for the first match
                    if f"{ticker}_samples" not in company_counts:
                        company_counts[f"{ticker}_samples"] = matches['firm_link'].unique()[:5].tolist()
    
    print(f"\n\nTotal rows processed: {total_rows:,}")
    
    # Display results
    print("\n" + "=" * 100)
    print("RESULTS - REVIEW COUNTS BY COMPANY:")
    print("=" * 100)
    
    target_tickers = ['NVDA', 'JPM', 'WMT', 'GE', 'DG']
    for ticker in target_tickers:
        count = company_counts.get(ticker, 0)
        print(f"\n{ticker}: {count:,} reviews")
        
        if count > 0:
            samples = company_counts.get(f"{ticker}_samples", [])
            if samples:
                print(f"  Sample firm_links:")
                for sample in samples:
                    print(f"    - {sample}")
        else:
            print(f"  No reviews found")
    
    print("\n" + "=" * 100)

if __name__ == "__main__":
    main()
