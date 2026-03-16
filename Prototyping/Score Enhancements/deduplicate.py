
import os
import snowflake.connector
from snowflake.connector import DictCursor
from dotenv import load_dotenv

# Load environment variables from the platform folder
load_dotenv('../pe-org-air-platform/.env')

def get_connection():
    return snowflake.connector.connect(
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA'),
        role=os.getenv('SNOWFLAKE_ROLE'),
        autocommit=True
    )

def deduplicate():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            print("Cleaning up duplicated external_signals...")
            # Keep the latest signal for each company/category/source/signal_hash
            # If signal_hash is null, we can't reliably dedup without logic, but let's try MIN(id)
            cursor.execute("""
                DELETE FROM external_signals 
                WHERE id NOT IN (
                    SELECT MIN(id) 
                    FROM external_signals 
                    GROUP BY company_id, category, source, signal_hash
                )
            """)
            print(f"Deleted {cursor.rowcount} duplicate signals.")

            print("Cleaning up signal_evidence...")
            # Keep only evidence linked to existing signals
            cursor.execute("""
                DELETE FROM signal_evidence 
                WHERE signal_id NOT IN (SELECT id FROM external_signals)
            """)
            print(f"Deleted {cursor.rowcount} orphaned evidence items.")

            # Optional: Deduplicate evidence itself if titles are identical for same ID
            cursor.execute("""
                DELETE FROM signal_evidence
                WHERE id NOT IN (
                    SELECT MIN(id)
                    FROM signal_evidence
                    GROUP BY signal_id, title, description
                )
            """)
            print(f"Deleted {cursor.rowcount} duplicate evidence items.")

            print("Cleaning up assessments...")
            # Keep only the latest assessment for each company
            cursor.execute("""
                DELETE FROM assessments
                WHERE id NOT IN (
                    SELECT id FROM (
                        SELECT id, ROW_NUMBER() OVER (PARTITION BY company_id, assessment_type ORDER BY created_at DESC) as rn
                        FROM assessments
                    ) WHERE rn = 1
                )
            """)
            print(f"Deleted {cursor.rowcount} old assessments.")

            print("Cleaning up dimension_scores...")
            # Remove scores for deleted assessments
            cursor.execute("""
                DELETE FROM dimension_scores
                WHERE assessment_id NOT IN (SELECT id FROM assessments)
            """)
            print(f"Deleted {cursor.rowcount} orphaned dimension scores.")

    finally:
        conn.close()

if __name__ == "__main__":
    deduplicate()
