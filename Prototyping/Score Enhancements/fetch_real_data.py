
import os
import json
import asyncio
from datetime import datetime
from decimal import Decimal
import snowflake.connector
from snowflake.connector import DictCursor
from dotenv import load_dotenv

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

def fetch_real_evidence_and_metrics():
    conn = get_connection()
    tickers = ['NVDA', 'JPM', 'WMT', 'GE', 'DG']
    results = {}
    
    try:
        with conn.cursor(DictCursor) as cursor:
            # 1. Get companies
            cursor.execute("SELECT id, ticker, name, industry_id, position_factor FROM companies WHERE ticker IN (%s, %s, %s, %s, %s)", tuple(tickers))
            companies = cursor.fetchall()
            
            for company in companies:
                ticker = company['TICKER']
                cid = company['ID']
                
                # 2. Get SEC Chunks (Evidence Text) - Use the exact join logic from the API
                cursor.execute("""
                    SELECT dc.chunk_text
                    FROM document_chunks dc
                    JOIN documents d ON dc.document_id = d.document_id
                    JOIN companies c ON (
                        UPPER(d.cik) = UPPER(c.cik) OR 
                        UPPER(d.cik) = UPPER(c.ticker) OR 
                        UPPER(d.company_name) = UPPER(c.name) OR 
                        UPPER(d.company_name) = UPPER(c.ticker)
                    )
                    WHERE c.id = %s
                    ORDER BY d.created_at DESC, dc.chunk_index ASC
                    LIMIT 200
                """, (cid,))
                chunks = cursor.fetchall()
                full_text = "\n".join([c['CHUNK_TEXT'] for c in chunks if c['CHUNK_TEXT']])
                
                # 3. Get Signal Summary (Real Scores)
                cursor.execute("SELECT * FROM company_signal_summaries WHERE company_id = %s", (cid,))
                summary = cursor.fetchone()
                
                # 4. Get Signal Counts
                cursor.execute("SELECT COUNT(*) as cnt FROM external_signals WHERE company_id = %s", (cid,))
                sig_count = cursor.fetchone()
                
                results[ticker] = {
                    "company_id": cid,
                    "pf_current": float(company['POSITION_FACTOR']),
                    "sec_text_sample": full_text,
                    "signals": dict(summary) if summary else {},
                    "total_signals": sig_count['CNT'] if sig_count else 0
                }
                print(f"Fetched real data for {ticker}. Text length: {len(full_text)}")
    finally:
        conn.close()
    
    return results

if __name__ == "__main__":
    data = fetch_real_evidence_and_metrics()
    with open('real_snowflake_data.json', 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print("Saved real_snowflake_data.json")
