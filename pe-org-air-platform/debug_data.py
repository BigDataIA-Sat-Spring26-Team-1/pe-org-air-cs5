
import os
import asyncio
from dotenv import load_dotenv
from app.services.snowflake import db

async def check_data():
    load_dotenv()
    await db.connect()
    try:
        print("--- Companies ---")
        companies = await db.fetch_all("SELECT id, name, ticker, cik FROM companies WHERE is_deleted = FALSE")
        for c in companies:
            print(f"ID: {c['id']}, Name: {c['name']}, Ticker: {c['ticker']}, CIK: {c['cik']}")
        
        print("\n--- Documents (First 20) ---")
        docs = await db.fetch_all("SELECT document_id, cik, company_name, filing_type FROM documents LIMIT 20")
        for d in docs:
            print(f"DocID: {d['document_id']}, CIK: {d['cik']}, Company: {d['company_name']}, Type: {d['filing_type']}")
            
        print("\n--- Join Test (JPM) ---")
        jpm_test = await db.fetch_all("""
            SELECT c.ticker, d.document_id, d.cik as doc_cik, d.filing_type
            FROM companies c
            LEFT JOIN documents d ON (
                UPPER(d.cik) = UPPER(c.cik) OR 
                UPPER(d.cik) = UPPER(c.ticker) OR 
                UPPER(d.company_name) = UPPER(c.name) OR 
                UPPER(d.company_name) = UPPER(c.ticker)
            )
            WHERE c.ticker = 'JPM'
        """)
        print(f"Found {len([r for r in jpm_test if r['document_id']])} documents for JPM")
        for r in jpm_test[:5]:
             print(f"Match: {r['ticker']} -> {r['doc_cik']} ({r['filing_type']})")

    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(check_data())
