import duckdb

def main():
    csv_path = '/Users/aakashbelide/Aakash/Higher Studies/Course/Sem-4/DAMG 7245/Case Study 3/pe-org-air-cs3/all_reviews.csv'
    
    print("Connecting to CSV with DuckDB (this is much faster!)...")
    print("=" * 100)
    
    # DuckDB can query CSV files directly without loading into memory
    con = duckdb.connect(':memory:')
    
    # First, let's peek at the structure
    print("\nSample data (first 10 rows):")
    print("=" * 100)
    sample = con.execute(f"""
        SELECT firm_link, title, rating, date, job
        FROM read_csv_auto('{csv_path}')
        LIMIT 10
    """).fetchdf()
    print(sample.to_string())
    
    # Get total count
    print("\n" + "=" * 100)
    total_count = con.execute(f"""
        SELECT COUNT(*) as total
        FROM read_csv_auto('{csv_path}')
    """).fetchone()[0]
    print(f"Total reviews in dataset: {total_count:,}")
    
    # Search for target companies
    print("\n" + "=" * 100)
    print("SEARCHING FOR TARGET COMPANIES:")
    print("=" * 100)
    
    companies = {
        'NVDA': ['nvidia', 'nvda'],
        'JPM': ['jpmorgan', 'jp-morgan', 'jpm', 'jpmorgan-chase', 'chase'],
        'WMT': ['walmart', 'wal-mart', 'wmt'],
        'GE': ['general-electric', 'generalelectric'],
        'DG': ['dollar-general', 'dollargeneral']
    }
    
    for ticker, search_terms in companies.items():
        print(f"\n{ticker}:")
        
        # Build SQL condition for all search terms
        conditions = " OR ".join([f"LOWER(firm_link) LIKE '%{term.lower()}%'" for term in search_terms])
        
        query = f"""
            SELECT 
                COUNT(*) as count,
                firm_link
            FROM read_csv_auto('{csv_path}')
            WHERE {conditions}
            GROUP BY firm_link
            ORDER BY count DESC
        """
        
        results = con.execute(query).fetchdf()
        
        if len(results) > 0:
            total = results['count'].sum()
            print(f"  Total reviews: {total:,}")
            print(f"  Unique firm_links: {len(results)}")
            print(f"  Sample firm_links:")
            for idx, row in results.head(5).iterrows():
                print(f"    - {row['firm_link']} ({row['count']:,} reviews)")
        else:
            print(f"  No reviews found")
    
    # Also show top 10 companies by review count
    print("\n" + "=" * 100)
    print("TOP 10 COMPANIES BY REVIEW COUNT:")
    print("=" * 100)
    
    top_companies = con.execute(f"""
        SELECT firm_link, COUNT(*) as review_count
        FROM read_csv_auto('{csv_path}')
        GROUP BY firm_link
        ORDER BY review_count DESC
        LIMIT 10
    """).fetchdf()
    
    for idx, row in top_companies.iterrows():
        print(f"{idx+1:2d}. {row['firm_link']}: {row['review_count']:,} reviews")
    
    con.close()
    print("\n" + "=" * 100)
    print("Analysis complete!")

if __name__ == "__main__":
    main()
