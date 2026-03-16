import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from snowflake_client import SnowflakeClient

def main():
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'pe-org-air-platform', '.env'))
    load_dotenv(env_path)
    
    client = SnowflakeClient()
    try:
        client.verify_company_ticker("NVDA")
        client.verify_company_ticker("NVIDIA")
        client.verify_company_ticker("GE")
        client.verify_company_ticker("General Electric")
        client.verify_company_ticker("DG")
        client.verify_company_ticker("Dollar General")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
