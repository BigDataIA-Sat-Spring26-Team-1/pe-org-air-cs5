
from datetime import datetime, timedelta
from airflow.decorators import dag, task
from airflow.models.param import Param
from airflow.utils.trigger_rule import TriggerRule

default_args = {
    'owner': 'pe-org-air',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
}

@dag(
    dag_id='sec_backfill',
    default_args=default_args,
    description='Manual SEC Filing Backfill Pipeline',
    schedule=None, # Manual Only
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['sec', 'backfill', 'manual'],
    params={
        "tickers": Param(["NVDA"], type="array", description="List of tickers to backfill"),
        "limit": Param(5, type="integer", description="Number of filings per type to download"),
        "filing_types": Param(["10-K", "10-Q"], type="array", description="List of filing types")
    }
)
def sec_backfill_dag_def():
    
    @task
    def get_target_tickers(**context):
        """
        Reads 'tickers' from DAG params.
        """
        params = context["params"]
        tickers = params.get("tickers", ["NVDA"])
        print(f"Backfill Triggered for: {tickers}")
        return tickers

    @task(retries=1)
    def download_filings(ticker: str, **context):
        import asyncio
        from app.pipelines.sec.components import download_ticker_filings
        
        params = context["params"]
        limit = params.get("limit", 5)
        f_types = params.get("filing_types", ["10-K", "10-Q"])
        
        return asyncio.run(download_ticker_filings(ticker, limit=limit, filing_types=f_types))

    @task
    def discover_filings():
        from app.pipelines.sec.components import scan_and_discover_filings
        return scan_and_discover_filings()

    @task(max_active_tis_per_dag=16) 
    def process_filing(filing_meta):
        import asyncio
        import json
        from pathlib import Path
        from app.pipelines.sec.components import process_single_filing
        
        # Returns doc_data or error dict
        # Force S3 upload since backfill implies we want to ensure data presence
        result = asyncio.run(process_single_filing(filing_meta, s3_force_upload=True))
        
        if result.get("status") == "success":
            doc_id = result["doc_data"]["doc_id"]
            out_path = f"/opt/airflow/app_code/data/temp_xcom/backfill/{doc_id}.json"
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w") as f:
                json.dump(result["doc_data"], f)
            return {"status": "success", "data_path": out_path}
            
        return result

    @task
    def save_to_snowflake(process_result):
        import asyncio
        import json
        from app.pipelines.sec.components import save_filing_to_db
        
        if process_result.get("status") == "success":
            data_path = process_result.get("data_path")
            with open(data_path, "r") as f:
                doc_data = json.load(f)
            
            asyncio.run(save_filing_to_db(doc_data))
            return "saved"
        return "skipped"

    @task(trigger_rule=TriggerRule.ALL_DONE)
    def cleanup():
        import shutil
        # Conservative cleanup
        shutil.rmtree("/opt/airflow/app_code/data/sec_downloads/sec-edgar-filings", ignore_errors=True)
        shutil.rmtree("/opt/airflow/app_code/data/temp_xcom/backfill", ignore_errors=True)

    # Workflow
    tickers = get_target_tickers()
    
    downloads = download_filings.expand(ticker=tickers)
    
    filings = discover_filings()
    downloads >> filings
    
    processed = process_filing.expand(filing_meta=filings)
    
    saved = save_to_snowflake.expand(process_result=processed)
    
    saved >> cleanup()

sec_backfill_dag_def()
