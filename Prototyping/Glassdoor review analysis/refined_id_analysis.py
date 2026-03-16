import duckdb

def main():
    csv_path = '/Users/aakashbelide/Aakash/Higher Studies/Course/Sem-4/DAMG 7245/Case Study 3/pe-org-air-cs3/all_reviews.csv'
    
    # We will use REGEX to ensure we match the exact ID boundary
    # Pattern: -E{id} followed by either a dot (.) or underscore (_) or end of string
    
    # Target 1: The IDs provided by the user
    requested_companies = {
        'JPM (User ID)': {'id': '145', 'name': 'J.P. Morgan'},
        'NVDA (User ID)': {'id': '7633', 'name': 'NVIDIA'},
        'WMT (User ID)': {'id': '715', 'name': 'Walmart'},
        'GE (User ID)': {'id': '277', 'name': 'General Electric'},
        'DG (User ID)': {'id': '1342', 'name': 'Dollar General'}
    }

    # Target 2: IDs discovered in previous steps (for comparison/completeness)
    discovered_companies = {
        'NVDA (Dataset ID)': {'id': '936493', 'name': 'NVIDIA'},
        'WMT (Dataset ID)': {'id': '395425', 'name': 'Walmart'},
        'GE (Dataset ID)': {'id': '614436', 'name': 'General Electric'},
        'JPM (Dataset ID)': {'id': '690765', 'name': 'Chase (JPM)'}
    }
    
    print("Refined Analysis with Strict ID Matching (DuckDB)...")
    print("=" * 100)
    
    con = duckdb.connect(':memory:')
    
    # 1. Analyze User-Provided IDs
    print(f"\n{' COMPANY (USER REQUESTED IDs) ':~^80}")
    for key, info in requested_companies.items():
        cid = info['id']
        name = info['name']
        
        # Strict Regex: URL must contain "-E" followed by the ID, followed by "." or "_"
        # Note: We use string formatting to insert the ID into the regex pattern
        query = f"""
            SELECT 
                firm_link,
                COUNT(*) as count
            FROM read_csv_auto('{csv_path}')
            WHERE regexp_matches(firm_link, '.*-E{cid}[._].*')
            GROUP BY firm_link
            ORDER BY count DESC
        """
        
        results = con.execute(query).fetchdf()
        total = results['count'].sum() if not results.empty else 0
        
        print(f"\n{name} (ID: {cid}) -> Total: {total:,}")
        if not results.empty:
            print("  Top 3 matches:")
            for idx, row in results.head(3).iterrows():
                print(f"    - {row['firm_link']} ({row['count']:,})")

    # 2. Analyze Discovered IDs (to help explain discrepancies)
    print(f"\n{' COMPANY (DATASET ALTERNATIVE IDs) ':~^80}")
    for key, info in discovered_companies.items():
        cid = info['id']
        name = info['name']
        
        query = f"""
            SELECT 
                firm_link,
                COUNT(*) as count
            FROM read_csv_auto('{csv_path}')
            WHERE regexp_matches(firm_link, '.*-E{cid}[._].*')
            GROUP BY firm_link
            ORDER BY count DESC
        """
        
        results = con.execute(query).fetchdf()
        total = results['count'].sum() if not results.empty else 0
        
        print(f"\n{name} (ID: {cid}) -> Total: {total:,}")
        if not results.empty:
            print("  Top 3 matches:")
            for idx, row in results.head(3).iterrows():
                print(f"    - {row['firm_link']} ({row['count']:,})")

    con.close()
    print("\n" + "=" * 100)
    print("Analysis complete!")

if __name__ == "__main__":
    main()
