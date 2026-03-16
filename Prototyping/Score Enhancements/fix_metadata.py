
import os
import snowflake.connector
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

def fix_metadata():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Ensure industries are correct
            # Add Technology industry if missing
            cursor.execute("SELECT id FROM industries WHERE name = 'Technology'")
            tech_exists = cursor.fetchone()
            if not tech_exists:
                cursor.execute("INSERT INTO industries (id, name, sector, h_r_base) VALUES ('550e8400-e29b-41d4-a716-446655440006', 'Technology', 'Technology', 85.00)")
                tech_id = '550e8400-e29b-41d4-a716-446655440006'
            else:
                tech_id = tech_exists[0]
            
            # 2. Update company assignments and position factors
            updates = [
                ('NVDA', tech_id, 0.9, '0001045810'), # NVIDIA CIK
                ('JPM', '550e8400-e29b-41d4-a716-446655440005', 0.5, '0000019617'), # JPM CIK
                ('WMT', '550e8400-e29b-41d4-a716-446655440004', 0.3, '0000104169'), # Walmart CIK
                ('GE', '550e8400-e29b-41d4-a716-446655440001', 0.0, '0000040545'), # GE CIK
                ('DG', '550e8400-e29b-41d4-a716-446655440004', -0.3, '0000029669') # Dollar General CIK
            ]
            
            for ticker, ind_id, pf, cik in updates:
                cursor.execute("""
                    UPDATE companies 
                    SET industry_id = %s, position_factor = %s, cik = %s
                    WHERE ticker = %s
                """, (ind_id, pf, cik, ticker))
                print(f"Updated {ticker}: Industry={ind_id}, PF={pf}")

            print("Metadata alignment complete.")

    finally:
        conn.close()

if __name__ == "__main__":
    fix_metadata()
