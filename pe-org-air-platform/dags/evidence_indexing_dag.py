"""
Automated evidence indexing pipeline.
Airflow DAG as per Case Study 4 Bonus Extensions (Page 32-33).
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import structlog

logger = structlog.get_logger()

default_args = {
    "owner": "pe-analytics",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
}

dag = DAG(
    dag_id="pe_evidence_indexing",
    default_args=default_args,
    description="Automated evidence indexing nightly pipeline",
    schedule_interval="0 2 * * *",  # 2 AM daily
    start_date=datetime(2026, 2, 20),
    catchup=False,
    tags=["RAG", "Indexing"],
)

def fetch_new_evidence(**context):
    """
    Fetch unindexed evidence from CS2.
    """
    import httpx
    import asyncio

    # In Airflow we use sync wrapper for simplicity or run in event loop
    async def run():
        # Using service-discovery name from docker-compose
        url = "http://api:8000/api/v1/evidence"
        async with httpx.AsyncClient() as client:
            # Fetch evidence marked as not yet indexed in CS4
            res = await client.get(url, params={"indexed": False})
            res.raise_for_status()
            evidence = res.json()
            context["ti"].xcom_push(key="evidence", value=evidence)
            return len(evidence)

    return asyncio.run(run())

def index_evidence_in_cs4(**context):
    """
    Index fetched evidence into the vector store.
    """
    import asyncio
    from app.services.retrieval.hybrid import HybridRetriever
    from app.services.retrieval.dimension_mapper import DimensionMapper
    from app.services.search.vector_store import VectorStore

    evidence = context["ti"].xcom_pull(key="evidence", task_ids="fetch_evidence_task")
    if not evidence:
        logger.info("no_new_evidence_to_index")
        return 0

    async def run():
        import asyncio
        from services.retrieval.hybrid import HybridRetriever
        from services.retrieval.dimension_mapper import DimensionMapper
        from services.search.vector_store import VectorStore

        # Setup services
        persist_dir = "/opt/airflow/app_code/data/chroma"
        vstore = VectorStore(persist_dir=persist_dir)
        retriever = HybridRetriever(vector_store=vstore)
        mapper = DimensionMapper()

        docs = []
        for e in evidence:
            # Use mapper and model format
            dim = mapper.get_primary_dimension(e.get("signal_category"), e.get("source_type"))
            docs.append({
                "doc_id": e["evidence_id"],
                "content": e["content"],
                "metadata": {
                    "company_id": e["company_id"],
                    "source_type": e["source_type"],
                    "dimension": dim.value,
                    "confidence": e["confidence"],
                }
            })
        
        count = await retriever.index_documents(docs)
        logger.info("indexing_completed", count=count)

        # Mark as indexed via API (Teammate B requirement)
        import httpx
        url = "http://api:8000/api/v1/evidence/mark-indexed"
        async with httpx.AsyncClient() as client:
            await client.post(url, json={"evidence_ids": [e["evidence_id"] for e in evidence]})
        
        return count

    return asyncio.run(run())

fetch_task = PythonOperator(
    task_id="fetch_evidence_task",
    python_callable=fetch_new_evidence,
    dag=dag,
)

index_task = PythonOperator(
    task_id="index_evidence_task",
    python_callable=index_evidence_in_cs4,
    dag=dag,
)

fetch_task >> index_task
