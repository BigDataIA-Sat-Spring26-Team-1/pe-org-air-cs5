import duckdb

def main():
    csv_path = '/Users/aakashbelide/Aakash/Higher Studies/Course/Sem-4/DAMG 7245/Case Study 3/pe-org-air-cs3/all_reviews.csv'
    
    # Map of Company Name -> Glassdoor ID
    # Patterns to match: "-E{id}." (end of ID, start of extension) or "-E{id}_" (end of ID, start of pagination/filter)
    target_companies = {
        'JPM (J.P. Morgan)': '145',
        'NVDA (NVIDIA)': '7633',
        'WMT (Walmart)': '715',
        'GE (General Electric)': '277',
        'DG (Dollar General)': '1342'
    }
    
    print("Analyzing Glassdoor reviews using Company IDs with DuckDB...")
    print("=" * 100)
    
    con = duckdb.connect(':memory:')
    
    # Get total count first
    total_count = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{csv_path}')").fetchone()[0]
    print(f"Total reviews in dataset: {total_count:,}\n")
    
    print("=" * 100)
    print("RESULTS BY COMPANY ID:")
    print("=" * 100)
    
    for company, cid in target_companies.items():
        print(f"\nAnalyzing {company} (ID: E{cid})...")
        
        # We look for the ID preceded by 'E' and followed by either '.' or '_'
        # This prevents E145 from matching E1450, E1459, etc.
        query = f"""
            SELECT 
                firm_link,
                COUNT(*) as count
            FROM read_csv_auto('{csv_path}')
            WHERE firm_link LIKE '%-E{cid}.%' 
               OR firm_link LIKE '%-E{cid}_%'
            GROUP BY firm_link
            ORDER BY count DESC
        """
        
        results = con.execute(query).fetchdf()
        
        total_company_reviews = results['count'].sum() if not results.empty else 0
        print(f"  Total Reviews Found: {total_company_reviews:,}")
        
        if not results.empty:
            print("  Top 5 URL patterns found:")
            for idx, row in results.head(5).iterrows():
                print(f"    - {row['firm_link']} ({row['count']:,} reviews)")
        else:
            print("  No reviews found with this ID.")

    con.close()
    print("\n" + "=" * 100)
    print("Analysis complete!")

if __name__ == "__main__":
    main()
