import duckdb
import os

def main():
    base_path = '/Users/aakashbelide/Aakash/Higher Studies/Course/Sem-4/DAMG 7245/Case Study 3/pe-org-air-cs3'
    source_csv = os.path.join(base_path, 'all_reviews.csv')
    output_csv = os.path.join(base_path, 'Prototyping/Glassdoor review analysis/target_company_reviews_strict.csv')
    
    print(f"Source: {source_csv}")
    print(f"Output: {output_csv}")
    
    # STRICT ID MAPPING based ONLY on user provided URLs
    # JPM: 145, NVDA: 7633, WMT: 715, GE: 277, DG: 1342
    ids_map = {
        'NVDA': ['7633'],
        'JPM':  ['145'],
        'WMT':  ['715'],
        'GE':   ['277'],
        'DG':   ['1342']
    }
    
    print("Using Example IDs ONLY: 7633 (NVDA), 145 (JPM), 715 (WMT), 277 (GE), 1342 (DG)")
    print("-" * 50)
    
    con = duckdb.connect(':memory:')
    
    # Constructing the exact same case logic but strictly for these IDs
    case_parts = []
    all_id_patterns = []
    
    for ticker, ids in ids_map.items():
        # IDs are single items list here but good to keep structure generic
        group_pattern = "|".join(ids)
        # Add to the global search pattern
        all_id_patterns.extend(ids)
        # Add to the classifier
        case_parts.append(f"WHEN regexp_matches(firm_link, '.*-E({group_pattern})[._].*') THEN '{ticker}'")
    
    # Join all IDs for the WHERE clause
    full_id_regex = "|".join(all_id_patterns)
    where_clause = f".*-E({full_id_regex})[._].*"
    
    case_statement = "\n".join(case_parts)
    
    query = f"""
        COPY (
            SELECT 
                *,
                CASE 
                    {case_statement}
                    ELSE 'UNKNOWN'
                END as company_ticker
            FROM read_csv_auto('{source_csv}')
            WHERE regexp_matches(firm_link, '{where_clause}')
        ) TO '{output_csv}' (HEADER, DELIMITER ',')
    """
    
    try:
        con.execute(query)
        print("Strict extraction query executed successfully.")
        
        # Verify result counts
        stats = con.execute(f"""
            SELECT company_ticker, COUNT(*) as count 
            FROM read_csv_auto('{output_csv}') 
            GROUP BY company_ticker 
            ORDER BY count DESC
        """).fetchdf()
        
        print("\nStrict Extraction Summary:")
        print(stats.to_string(index=False))
        
        total = stats['count'].sum() if not stats.empty else 0
        print(f"\nTotal extracted rows: {total:,}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        con.close()

if __name__ == "__main__":
    main()
