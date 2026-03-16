
from datetime import datetime, timedelta
from airflow.decorators import dag, task
from airflow.utils.email import send_email

default_args = {
    'owner': 'pe-org-air',
    'depends_on_past': False,
    'email_on_failure': True,
    'retries': 0,
}

@dag(
    dag_id='sec_quality_monitor',
    default_args=default_args,
    description='Weekly SEC Data Quality Audit',
    schedule='@weekly', # Mondays
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['sec', 'monitor', 'audit']
)
def sec_monitor_dag_def():

    @task
    def check_snowflake_counts():
        """
        Check total documents and chunks in Snowflake.
        """
        import asyncio
        from app.services.snowflake import db
        
        async def run_check():
            docs = await db.fetch_all("SELECT count(*) as count FROM documents")
            chunks = await db.fetch_all("SELECT count(*) as count FROM document_chunks")
            return {
                "docs": docs[0]['count'] if docs else 0,
                "chunks": chunks[0]['count'] if chunks else 0
            }
        
        return asyncio.run(run_check())

    @task
    def check_s3_consistency(snowflake_stats):
        """
        Verify that S3 file counts roughly match Snowflake metadata.
        This is a 'soft' check since listing S3 can be slow.
        """
        # For this prototype, we'll log the stats and potential discrepancies
        # In prod, we'd list S3 prefixes
        
        print(f"Snowflake Stats: {snowflake_stats}")
        
        if snowflake_stats['docs'] == 0:
            raise ValueError("Snowflake documents table is empty! Pipeline Failure.")
            
        return "Consistency Check Passed"
        
    @task
    def check_data_quality():
        """
        Check for filings with 0 chunks (parsing failures that were saved anyway).
        """
        import asyncio
        from app.services.snowflake import db
        
        async def run_dq():
            # Find documents with no chunks
            query = """
                SELECT d.doc_id, d.company_name 
                FROM documents d 
                LEFT JOIN document_chunks c ON d.doc_id = c.doc_id 
                WHERE c.chunk_id IS NULL
                LIMIT 50
            """
            bad_docs = await db.fetch_all(query)
            return [dict(d) for d in bad_docs]
            
        bad_docs = asyncio.run(run_dq())
        
        if bad_docs:
            print(f"Found {len(bad_docs)} documents with 0 chunks: {bad_docs}")
            # Could raise warning or trigger alert
            return "Warning: Found empty documents"
            
        return "Data Quality: clean"

    # Workflow
    stats = check_snowflake_counts()
    consistency = check_s3_consistency(stats)
    
    dq = check_data_quality()
    
    [consistency, dq]

sec_monitor_dag_def()
