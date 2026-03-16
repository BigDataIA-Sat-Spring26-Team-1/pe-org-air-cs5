import duckdb

def main():
    csv_path = '/Users/aakashbelide/Aakash/Higher Studies/Course/Sem-4/DAMG 7245/Case Study 3/pe-org-air-cs3/all_reviews.csv'
    
    print("Analyzing Glassdoor reviews with DuckDB...")
    print("=" * 100)
    
    con = duckdb.connect(':memory:')
    
    # Get total count
    total_count = con.execute(f"""
        SELECT COUNT(*) as total
        FROM read_csv_auto('{csv_path}')
    """).fetchone()[0]
    print(f"Total reviews in dataset: {total_count:,}\n")
    
    # More precise search for each company
    print("=" * 100)
    print("COMPANY REVIEW COUNTS:")
    print("=" * 100)
    
    # NVDA - NVIDIA
    print("\nNVDA (NVIDIA):")
    nvda_results = con.execute(f"""
        SELECT firm_link, COUNT(*) as count
        FROM read_csv_auto('{csv_path}')
        WHERE LOWER(firm_link) LIKE '%nvidia%'
        GROUP BY firm_link
        ORDER BY count DESC
    """).fetchdf()
    
    if len(nvda_results) > 0:
        total = nvda_results['count'].sum()
        print(f"  Total reviews: {total:,}")
        for idx, row in nvda_results.iterrows():
            print(f"    - {row['firm_link']}: {row['count']:,}")
    else:
        print(f"  No reviews found")
    
    # JPM - JPMorgan Chase (more specific)
    print("\nJPM (JPMorgan Chase):")
    jpm_results = con.execute(f"""
        SELECT firm_link, COUNT(*) as count
        FROM read_csv_auto('{csv_path}')
        WHERE (LOWER(firm_link) LIKE '%jpmorgan%' 
           OR LOWER(firm_link) LIKE '%jp-morgan%'
           OR LOWER(firm_link) LIKE '%j-p-morgan%')
        GROUP BY firm_link
        ORDER BY count DESC
    """).fetchdf()
    
    if len(jpm_results) > 0:
        total = jpm_results['count'].sum()
        print(f"  Total reviews: {total:,}")
        for idx, row in jpm_results.iterrows():
            print(f"    - {row['firm_link']}: {row['count']:,}")
    else:
        print(f"  No reviews found")
    
    # Also check for Chase separately
    print("\n  Additional search for 'Chase' (may include JPMorgan):")
    chase_results = con.execute(f"""
        SELECT firm_link, COUNT(*) as count
        FROM read_csv_auto('{csv_path}')
        WHERE LOWER(firm_link) LIKE '%chase%'
          AND LOWER(firm_link) NOT LIKE '%lionchase%'
        GROUP BY firm_link
        ORDER BY count DESC
        LIMIT 5
    """).fetchdf()
    
    for idx, row in chase_results.iterrows():
        print(f"    - {row['firm_link']}: {row['count']:,}")
    
    # WMT - Walmart
    print("\nWMT (Walmart):")
    wmt_results = con.execute(f"""
        SELECT firm_link, COUNT(*) as count
        FROM read_csv_auto('{csv_path}')
        WHERE LOWER(firm_link) LIKE '%walmart%'
           OR LOWER(firm_link) LIKE '%wal-mart%'
        GROUP BY firm_link
        ORDER BY count DESC
    """).fetchdf()
    
    if len(wmt_results) > 0:
        total = wmt_results['count'].sum()
        print(f"  Total reviews: {total:,}")
        for idx, row in wmt_results.iterrows():
            print(f"    - {row['firm_link']}: {row['count']:,}")
    else:
        print(f"  No reviews found")
    
    # GE - General Electric (more specific search)
    print("\nGE (General Electric):")
    ge_results = con.execute(f"""
        SELECT firm_link, COUNT(*) as count
        FROM read_csv_auto('{csv_path}')
        WHERE (LOWER(firm_link) LIKE '%general-electric%'
           OR LOWER(firm_link) LIKE '%generalelectric%'
           OR firm_link LIKE '%/GE-%'
           OR firm_link LIKE '%/General-Electric-%')
          AND LOWER(firm_link) NOT LIKE '%portland%'
        GROUP BY firm_link
        ORDER BY count DESC
    """).fetchdf()
    
    if len(ge_results) > 0:
        total = ge_results['count'].sum()
        print(f"  Total reviews: {total:,}")
        for idx, row in ge_results.iterrows():
            print(f"    - {row['firm_link']}: {row['count']:,}")
    else:
        print(f"  No reviews found")
        # Let's search more broadly
        print(f"  Searching for any 'GE' related links...")
        ge_broad = con.execute(f"""
            SELECT firm_link, COUNT(*) as count
            FROM read_csv_auto('{csv_path}')
            WHERE firm_link LIKE '%/GE-%'
               OR firm_link LIKE '%-GE-%'
            GROUP BY firm_link
            ORDER BY count DESC
            LIMIT 10
        """).fetchdf()
        
        if len(ge_broad) > 0:
            print(f"  Found these GE-related companies:")
            for idx, row in ge_broad.iterrows():
                print(f"    - {row['firm_link']}: {row['count']:,}")
    
    # DG - Dollar General
    print("\nDG (Dollar General):")
    dg_results = con.execute(f"""
        SELECT firm_link, COUNT(*) as count
        FROM read_csv_auto('{csv_path}')
        WHERE LOWER(firm_link) LIKE '%dollar-general%'
           OR LOWER(firm_link) LIKE '%dollargeneral%'
        GROUP BY firm_link
        ORDER BY count DESC
    """).fetchdf()
    
    if len(dg_results) > 0:
        total = dg_results['count'].sum()
        print(f"  Total reviews: {total:,}")
        for idx, row in dg_results.iterrows():
            print(f"    - {row['firm_link']}: {row['count']:,}")
    else:
        print(f"  No reviews found")
    
    # Summary
    print("\n" + "=" * 100)
    print("SUMMARY:")
    print("=" * 100)
    print(f"NVDA (NVIDIA):        {nvda_results['count'].sum() if len(nvda_results) > 0 else 0:>10,} reviews")
    print(f"JPM (JPMorgan):       {jpm_results['count'].sum() if len(jpm_results) > 0 else 0:>10,} reviews (excluding generic 'Chase')")
    print(f"WMT (Walmart):        {wmt_results['count'].sum() if len(wmt_results) > 0 else 0:>10,} reviews")
    print(f"GE (General Electric):{ge_results['count'].sum() if len(ge_results) > 0 else 0:>10,} reviews")
    print(f"DG (Dollar General):  {dg_results['count'].sum() if len(dg_results) > 0 else 0:>10,} reviews")
    print("=" * 100)
    
    con.close()

if __name__ == "__main__":
    main()
