
import os
import json
import asyncio
from datetime import datetime
from decimal import Decimal
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

def fetch_data():
    conn = get_connection()
    tickers = ['NVDA', 'JPM', 'WMT', 'GE', 'DG']
    results = {}
    
    try:
        with conn.cursor(DictCursor) as cursor:
            # 1. Get companies
            cursor.execute("SELECT id, ticker, name, industry_id, position_factor, cik FROM companies WHERE ticker IN (%s, %s, %s, %s, %s)", tuple(tickers))
            companies = cursor.fetchall()
            
            for company in companies:
                ticker = company['TICKER']
                cid = company['ID']
                
                # 2. Get latest assessment
                cursor.execute("""
                    SELECT * FROM assessments 
                    WHERE company_id = %s AND assessment_type = 'INTEGRATED_CS3'
                    ORDER BY assessment_date DESC, created_at DESC LIMIT 1
                """, (cid,))
                assessment = cursor.fetchone()
                
                # 3. Get latest signal summary
                cursor.execute("SELECT * FROM company_signal_summaries WHERE company_id = %s", (cid,))
                summary = cursor.fetchone()
                
                # 4. Get dimension scores
                dim_scores = []
                if assessment:
                    cursor.execute("SELECT dimension, score, weight FROM dimension_scores WHERE assessment_id = %s", (assessment['ID'],))
                    dim_scores = cursor.fetchall()
                
                # 5. Get signals count by category
                cursor.execute("SELECT category, COUNT(*) as cnt FROM external_signals WHERE company_id = %s GROUP BY category", (cid,))
                signals = cursor.fetchall()
                
                results[ticker] = {
                    "company": dict(company),
                    "assessment": dict(assessment) if assessment else None,
                    "summary": dict(summary) if summary else None,
                    "dimension_scores": [dict(d) for d in dim_scores],
                    "signals": [dict(s) for s in signals]
                }
    finally:
        conn.close()
    
    return results

if __name__ == "__main__":
    data = fetch_data()
    print(json.dumps(data, indent=2, default=str))
