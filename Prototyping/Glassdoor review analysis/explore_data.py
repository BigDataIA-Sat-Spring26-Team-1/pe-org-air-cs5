import pandas as pd

def main():
    # Read the CSV file
    print("Loading CSV file...")
    csv_path = '/Users/aakashbelide/Aakash/Higher Studies/Course/Sem-4/DAMG 7245/Case Study 3/pe-org-air-cs3/all_reviews.csv'
    df = pd.read_csv(csv_path, low_memory=False)
    
    print(f"\nTotal rows: {len(df):,}")
    print(f"Total columns: {len(df.columns)}")
    
    # Let's look at more sample rows to understand the firm_link pattern
    print("\n" + "=" * 100)
    print("EXAMINING FIRM_LINK PATTERNS (20 random samples):")
    print("=" * 100)
    
    sample_links = df['firm_link'].dropna().sample(min(20, len(df)), random_state=42)
    for i, link in enumerate(sample_links, 1):
        print(f"{i:2d}. {link}")
    
    # Let's search for potential company names that might match our tickers
    # NVDA = NVIDIA, JPM = JPMorgan Chase, WMT = Walmart, GE = General Electric, DG = Dollar General
    
    print("\n" + "=" * 100)
    print("SEARCHING FOR TARGET COMPANIES:")
    print("=" * 100)
    
    companies_to_find = {
        'NVDA': ['nvidia', 'nvda'],
        'JPM': ['jpmorgan', 'jp morgan', 'jpm', 'chase'],
        'WMT': ['walmart', 'wal-mart', 'wmt'],
        'GE': ['general electric', 'ge-'],
        'DG': ['dollar general', 'dollargeneral', 'dg-']
    }
    
    for ticker, search_terms in companies_to_find.items():
        print(f"\n{ticker}:")
        found = False
        for term in search_terms:
            # Search in firm_link (case insensitive)
            matches = df[df['firm_link'].str.contains(term, case=False, na=False)]
            if len(matches) > 0:
                found = True
                print(f"  Found {len(matches):,} reviews matching '{term}'")
                # Show a few sample firm_links
                sample_firm_links = matches['firm_link'].unique()[:3]
                for link in sample_firm_links:
                    print(f"    Sample: {link}")
        
        if not found:
            print(f"  No matches found for any search terms: {search_terms}")
    
    # Let's also check what the most common firm_links are
    print("\n" + "=" * 100)
    print("TOP 20 COMPANIES BY REVIEW COUNT:")
    print("=" * 100)
    top_companies = df['firm_link'].value_counts().head(20)
    for i, (firm, count) in enumerate(top_companies.items(), 1):
        print(f"{i:2d}. {firm}: {count:,} reviews")

if __name__ == "__main__":
    main()
