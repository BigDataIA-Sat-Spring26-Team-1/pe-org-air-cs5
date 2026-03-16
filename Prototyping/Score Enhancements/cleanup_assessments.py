
import os
import snowflake.connector
from dotenv import load_dotenv

def cleanup_cs3_assessments():
    load_dotenv('../pe-org-air-platform/.env')
    
    conn = snowflake.connector.connect(
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA'),
        role=os.getenv('SNOWFLAKE_ROLE'),
        autocommit=True
    )
    
    cursor = conn.cursor()
    tickers = ['NVDA', 'JPM', 'WMT', 'GE', 'DG']
    
    print(f"Cleaning up Integrated CS3 data for {tickers}...")

    # Fetch company IDs
    placeholders = ', '.join(['%s'] * len(tickers))
    cursor.execute(f"SELECT id FROM companies WHERE ticker IN ({placeholders})", tickers)
    company_ids = [row[0] for row in cursor.fetchall()]
    
    if not company_ids:
        print("No companies found. Skipping.")
        conn.close()
        return

    # Fetch assessment IDs
    comp_placeholders = ', '.join(['%s'] * len(company_ids))
    cursor.execute(f"SELECT id FROM assessments WHERE assessment_type = 'INTEGRATED_CS3' AND company_id IN ({comp_placeholders})", company_ids)
    assessment_ids = [row[0] for row in cursor.fetchall()]

    if assessment_ids:
        # 1. Delete Dimension Scores
        asmt_placeholders = ', '.join(['%s'] * len(assessment_ids))
        cursor.execute(f"DELETE FROM dimension_scores WHERE assessment_id IN ({asmt_placeholders})", assessment_ids)
        print(f"Deleted {cursor.rowcount} dimension scores.")

        # 2. Delete Assessments
        cursor.execute(f"DELETE FROM assessments WHERE id IN ({asmt_placeholders})", assessment_ids)
        print(f"Deleted {cursor.rowcount} assessments.")
    else:
        print("No assessments found.")

    # 3. Delete Derived Signals (Preserving backfill)
    cursor.execute(f"DELETE FROM external_signals WHERE source IN ('Talent Scorer', 'Glassdoor Cultural Audit') AND company_id IN ({comp_placeholders})", company_ids)
    print(f"Deleted {cursor.rowcount} derived signals.")

    conn.close()
    print("Cleanup complete. Backfill data remains intact.")

if __name__ == "__main__":
    cleanup_cs3_assessments()
