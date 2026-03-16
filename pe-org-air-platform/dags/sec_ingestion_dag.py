
from datetime import datetime, timedelta
from airflow.decorators import dag, task
from airflow.utils.trigger_rule import TriggerRule

default_args = {
    'owner': 'pe-org-air',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

@dag(
    dag_id='sec_filing_ingestion',
    default_args=default_args,
    description='Daily SEC Filing Ingestion Pipeline',
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['sec', 'ingestion']
)
def sec_ingestion_dag_def():
    
    @task
    def get_tickers():
        import asyncio
        from app.pipelines.sec.components import fetch_ticker_list
        return asyncio.run(fetch_ticker_list())

    @task(retries=3, retry_delay=timedelta(minutes=2), execution_timeout=timedelta(minutes=5), max_active_tis_per_dag=5)
    def download_filings(ticker: str):
        import asyncio
        from app.pipelines.sec.components import download_ticker_filings
        # 2-minute timeout handled inside or by execution_timeout
        return asyncio.run(download_ticker_filings(ticker, limit=2))

    @task
    def discover_filings():
        from app.pipelines.sec.components import scan_and_discover_filings
        return scan_and_discover_filings()

    @task(max_active_tis_per_dag=8, execution_timeout=timedelta(minutes=3))
    def process_filing(filing_meta):
        import asyncio
        import json
        from pathlib import Path
        from app.pipelines.sec.components import process_single_filing
        
        # Returns doc_data or error dict
        result = asyncio.run(process_single_filing(filing_meta))
        
        if result.get("status") == "success":
            # Write heavy data to shared volume, pass path via XCom
            doc_id = result["doc_data"]["doc_id"]
            # Ensure safe path structure
            out_path = f"/opt/airflow/app_code/data/temp_xcom/{doc_id}.json"
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w") as f:
                json.dump(result["doc_data"], f)
            # Return path instead of full data
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
        from pathlib import Path
        # Conservative cleanup: Delete both downloads and temp XComs to ensure fresh state for next run
        shutil.rmtree("/opt/airflow/app_code/data/sec_downloads/sec-edgar-filings", ignore_errors=True)
        shutil.rmtree("/opt/airflow/app_code/data/temp_xcom", ignore_errors=True)

    # Define Workflow
    tickers = get_tickers()
    
    # Dynamic Map: Download for each ticker
    downloads = download_filings.expand(ticker=tickers)
    
    # Explicit dependency: Discover runs after ALL downloads complete
    filings = discover_filings()
    downloads >> filings
    
    # Dynamic Map: Process each filing found
    processed = process_filing.expand(filing_meta=filings)
    
    # Dynamic Map: Save each successful result
    saved = save_to_snowflake.expand(process_result=processed)
    
    # Cleanup runs after everything
    saved >> cleanup()

# Instantiate the DAG
sec_ingestion_dag_def()
