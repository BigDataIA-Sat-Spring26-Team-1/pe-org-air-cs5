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
    
    companies = {
        "JPM": "JPM",
        "WMT": "WMT",
        "GE": "GE",
        "DG": "DG", # Dollar General
        "NVDA": "NVDA"
    }
    
    print("\n--- Snowflake Job Post Counts (SIGNAL_EVIDENCE) ---")
    print(f"{'Ticker':<8} | {'Count':<8} | {'Latest Date':<12} | {'Category'}")
    print("-" * 65)
    
    try:
        cursor = conn.cursor()
        for ticker, label in companies.items():
            # Query for count and max date
            query = f"""
                SELECT COUNT(*), MAX(evidence_date)
                FROM SIGNAL_EVIDENCE se
                JOIN COMPANIES c ON se.company_id = c.id
                WHERE (c.ticker = '{ticker}' OR c.name ILIKE '%{label}%')
                AND se.category = 'technology_hiring'
            """
            cursor.execute(query)
            row = cursor.fetchone()
            count = row[0]
            latest_date = str(row[1]) if row[1] else "N/A"
            print(f"{label:<8} | {count:<8} | {latest_date:<12} | technology_hiring")
            
    except Exception as e:
        print(f"Error querying Snowflake: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
