import os
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
import pandas as pd
from typing import List, Dict

class SnowflakeClient:
    def __init__(self):
        # Using environment variables or hardcoded for POC (Assuming env vars are set or user will provide)
        # For this POC, let's assume standard connection parameters
        self.user =os.getenv("SNOWFLAKE_USER")
        self.password = os.getenv("SNOWFLAKE_PASSWORD")
        self.account = os.getenv("SNOWFLAKE_ACCOUNT")
        self.warehouse = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
        self.database = os.getenv("SNOWFLAKE_DATABASE", "PE_ORG_AIR_DB")
        self.schema = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC") 
        self.role = os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN")

    def get_connection(self):
        return snowflake.connector.connect(
            user=self.user,
            password=self.password,
            account=self.account,
            warehouse=self.warehouse,
            database=self.database,
            schema=self.schema,
            role=self.role
        )

    def verify_company_ticker(self, search_term: str):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            query = f"""
                SELECT id, name, ticker 
                FROM COMPANIES 
                WHERE name ILIKE '%{search_term}%' OR ticker = '{search_term}'
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            print(f"Checking Company for '{search_term}':")
            for row in rows:
                print(f"  Found: ID={row[0]}, Name={row[1]}, Ticker={row[2]}")
            return rows
        finally:
            conn.close()

    def fetch_job_skills(self, company_identifier: str) -> List[str]:
        """
        Fetch all job descriptions from SIGNAL_EVIDENCE for a given company (ticker or name).
        """
        conn = self.get_connection()
        try:
            # Join SIGNAL_EVIDENCE with COMPANIES to filter by company name/ticker
            # We look for evidence associated with technology hiring or general job signals
            query = f"""
                SELECT se.description
                FROM SIGNAL_EVIDENCE se
                JOIN COMPANIES c ON se.company_id = c.id
                WHERE (c.ticker = '{company_identifier}' OR c.name ILIKE '%{company_identifier}%')
                AND se.category = 'technology_hiring'
                AND se.description IS NOT NULL
                limit 1000
            """
            
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            
            descriptions = [row[0] for row in rows]
            return descriptions
            
        finally:
            conn.close()

if __name__ == "__main__":
    # Test connection
    client = SnowflakeClient()
    try:
        print("Testing Snowflake connection...")
        # skills = client.fetch_job_skills("JPMorgan") # Commented out to avoid running without creds
        # print(f"Found {len(skills)} job descriptions")
        print("Client initialized (execution requires env vars)")
    except Exception as e:
        print(f"Connection failed (expected if no env vars): {e}")
