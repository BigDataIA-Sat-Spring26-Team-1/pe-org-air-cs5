import snowflake.connector
import os
from decimal import Decimal
from typing import List, Dict, Any
from dotenv import load_dotenv

class SnowflakeClient:
    def __init__(self, env_path: str):
        load_dotenv(env_path)
        self.conn = snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema=os.getenv("SNOWFLAKE_SCHEMA"),
            role=os.getenv("SNOWFLAKE_ROLE")
        )

    def fetch_company(self, ticker: str) -> Dict:
        cursor = self.conn.cursor(snowflake.connector.DictCursor)
        cursor.execute("SELECT id, name, ticker, industry_id, position_factor, cik FROM companies WHERE ticker = %s", (ticker,))
        return cursor.fetchone()

    def fetch_evidence(self, company_id: str) -> List[Dict]:
        cursor = self.conn.cursor(snowflake.connector.DictCursor)
        cursor.execute("SELECT category, source, normalized_score, confidence FROM external_signals WHERE company_id = %s", (company_id,))
        return cursor.fetchall()

    def fetch_culture_scores(self, ticker: str) -> Dict:
        cursor = self.conn.cursor(snowflake.connector.DictCursor)
        cursor.execute("SELECT * FROM culture_scores WHERE ticker = %s ORDER BY batch_date DESC LIMIT 1", (ticker,))
        return cursor.fetchone()
    
    def fetch_job_descriptions(self, company_id: str) -> List[Dict]:
        cursor = self.conn.cursor(snowflake.connector.DictCursor)
        cursor.execute("SELECT title, description FROM signal_evidence WHERE company_id = %s AND category = 'technology_hiring'", (company_id,))
        return cursor.fetchall()

    def fetch_glassdoor_reviews(self, ticker: str) -> List[Dict]:
        cursor = self.conn.cursor(snowflake.connector.DictCursor)
        cursor.execute("SELECT title, pros, cons FROM glassdoor_reviews WHERE ticker = %s", (ticker,))
        return cursor.fetchall()

    def fetch_sec_chunks(self, ticker: str, limit: int = 10) -> List[Dict]:
        """Fetch SEC document chunks associated with the ticker/company."""
        cursor = self.conn.cursor(snowflake.connector.DictCursor)
        # We join documents and document_chunks. We match by ticker or company name.
        cursor.execute("""
            SELECT dc.section_name, dc.chunk_text 
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.document_id
            JOIN companies c ON (UPPER(d.cik) = UPPER(c.cik) OR UPPER(d.company_name) = UPPER(c.name) OR UPPER(d.company_name) = UPPER(c.ticker))
            WHERE c.ticker = %s
            LIMIT %s
        """, (ticker, limit))
        return cursor.fetchall()

    def close(self):
        self.conn.close()
