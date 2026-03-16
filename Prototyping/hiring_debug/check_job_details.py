import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'TalentAnalyzerPOC')))
from snowflake_client import SnowflakeClient

def main():
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'pe-org-air-platform', '.env'))
    load_dotenv(env_path)
    
    client = SnowflakeClient()
    conn = client.get_connection()
    
    tickers = ["JPM", "WMT"]
    
    print("\n--- Recent Job Titles in Snowflake (SIGNAL_EVIDENCE) ---")
    
    try:
        cursor = conn.cursor()
        for ticker in tickers:
            print(f"\n[{ticker}] Top 10 Latest Job Postings:")
            query = f"""
                SELECT title, evidence_date
                FROM SIGNAL_EVIDENCE se
                JOIN COMPANIES c ON se.company_id = c.id
                WHERE c.ticker = '{ticker}'
                AND se.category = 'technology_hiring'
                ORDER BY evidence_date DESC
                LIMIT 10
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            for row in rows:
                print(f"  - {row[1]}: {row[0]}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
