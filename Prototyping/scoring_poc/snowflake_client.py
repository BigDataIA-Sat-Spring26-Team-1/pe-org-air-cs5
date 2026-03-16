import snowflake.connector
import os
from decimal import Decimal
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load .env from the platform directory
load_dotenv("/Users/aakashbelide/Aakash/Higher Studies/Course/Sem-4/DAMG 7245/Case Study 3/pe-org-air-cs3/pe-org-air-platform/.env")

class SnowflakeClient:
    def __init__(self):
        self.conn_params = {
            "user": os.getenv("SNOWFLAKE_USER"),
            "password": os.getenv("SNOWFLAKE_PASSWORD"),
            "account": os.getenv("SNOWFLAKE_ACCOUNT"),
            "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
            "database": os.getenv("SNOWFLAKE_DATABASE"),
            "schema": os.getenv("SNOWFLAKE_SCHEMA"),
            "role": os.getenv("SNOWFLAKE_ROLE")
        }

    def get_connection(self):
        return snowflake.connector.connect(**self.conn_params)

    def fetch_all(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor(snowflake.connector.DictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchall()

    def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor(snowflake.connector.DictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchone()

    def fetch_company_by_ticker(self, ticker: str) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM companies WHERE ticker = %s"
        return self.fetch_one(query, (ticker,))

    def fetch_external_signals(self, company_id: str) -> List[Dict[str, Any]]:
        query = "SELECT * FROM external_signals WHERE company_id = %s"
        return self.fetch_all(query, (company_id,))
