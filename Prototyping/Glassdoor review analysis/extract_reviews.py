import duckdb
import os

def main():
    base_path = '/Users/aakashbelide/Aakash/Higher Studies/Course/Sem-4/DAMG 7245/Case Study 3/pe-org-air-cs3'
    source_csv = os.path.join(base_path, 'all_reviews.csv')
    output_csv = os.path.join(base_path, 'Prototyping/Glassdoor review analysis/target_company_reviews.csv')
    
    print(f"Source: {source_csv}")
    print(f"Output: {output_csv}")
    
    # Define Target IDs based on our previous analysis
    ids_map = {
        'NVDA': ['936493'],              # Dataset ID for NVIDIA
        'JPM':  ['145', '690765'],       # J.P. Morgan & Chase
        'WMT':  ['715', '395425'],       # Walmart User ID & Dataset ID
        'GE':   ['277', '614436'],       # General Electric User ID & Dataset ID
        'DG':   ['1342']                 # Dollar General
    }
    
    # Flatten all IDs for the main WHERE clause
    all_ids = []
    for ids in ids_map.values():
        all_ids.extend(ids)
    
    # Create the regex pattern for the WHERE clause: .*-E(id1|id2|...)[._].*
    # This matches string ending with -E{id} followed by . or _
    id_group = "|".join(all_ids)
    where_pattern = f".*-E({id_group})[._].*"
    
    print(f"Extracting reviews for {len(all_ids)} distinct Company IDs...")
    print("-" * 50)
    
    con = duckdb.connect(':memory:')
    
    # query to select data and add a ticker column
    # We construct a CASE statement to label the ticker
    case_parts = []
    for ticker, ids in ids_map.items():
        # strict regex for each ticker group
        group_pattern = "|".join(ids)
        case_parts.append(f"WHEN regexp_matches(firm_link, '.*-E({group_pattern})[._].*') THEN '{ticker}'")
    
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
            WHERE regexp_matches(firm_link, '{where_pattern}')
        ) TO '{output_csv}' (HEADER, DELIMITER ',')
    """
    
    try:
        con.execute(query)
        print("Extraction query executed successfully.")
        
        # Verify the output
        result_stats = con.execute(f"""
            SELECT company_ticker, COUNT(*) as count 
            FROM read_csv_auto('{output_csv}') 
            GROUP BY company_ticker 
            ORDER BY count DESC
        """).fetchdf()
        
        print("\nExtraction Summary:")
        print(result_stats.to_string(index=False))
        
        total_rows = result_stats['count'].sum()
        print(f"\nTotal extracted rows: {total_rows:,}")
        
    except Exception as e:
        print(f"Error during extraction: {e}")
    finally:
        con.close()

if __name__ == "__main__":
    main()
