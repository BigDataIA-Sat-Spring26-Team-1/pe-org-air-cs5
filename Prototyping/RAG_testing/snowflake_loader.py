import snowflake.connector
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

def get_snowflake_client():
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        role=os.getenv("SNOWFLAKE_ROLE")
    )

def fetch_evidence_from_snowflake(ticker: str, limit: int = 100):
    """
    Fetches real 'CS2 Evidence' from Snowflake.
    Combines SEC chunks and External Signals.
    """
    conn = get_snowflake_client()
    try:
        # 1. Fetch SEC Chunks
        sec_query = f"""
        SELECT 
            CHUNK_ID as evidence_id, 
            CHUNK_TEXT as content, 
            COALESCE(SECTION_NAME, 'SEC-Filing') as source_type,
            'SEC_FILING' as signal_category,
            1.0 as confidence
        FROM document_chunks SC
        JOIN documents SD ON SC.DOCUMENT_ID = SD.DOCUMENT_ID
        WHERE SD.CIK IN (SELECT CIK FROM companies WHERE TICKER = '{ticker.upper()}')
        ORDER BY SC.CREATED_AT DESC
        LIMIT {limit // 2}
        """
        sec_df = pd.read_sql(sec_query, conn)
        
        # 2. Fetch External Signals
        # Using a more robust query for signals
        signal_query = f"""
        SELECT 
            ID as evidence_id, 
            RAW_VALUE as content,
            SOURCE as source_type,
            CATEGORY as signal_category,
            CONFIDENCE as confidence
        FROM EXTERNAL_SIGNALS
        WHERE COMPANY_ID IN (SELECT ID FROM companies WHERE TICKER = '{ticker.upper()}')
        ORDER BY CREATED_AT DESC
        LIMIT {limit // 2}
        """
        signal_df = pd.read_sql(signal_query, conn)
        
        # Clean columns to ensure case consistency
        sec_df.columns = [c.upper() for c in sec_df.columns]
        signal_df.columns = [c.upper() for c in signal_df.columns]

        # Combine results
        combined_df = pd.concat([sec_df, signal_df], ignore_index=True)
        return combined_df
    finally:
        conn.close()

if __name__ == "__main__":
    # Test fetch
    print("Testing Snowflake Fetch for NVDA...")
    data = fetch_evidence_from_snowflake("NVDA", limit=5)
    print(data.head())
