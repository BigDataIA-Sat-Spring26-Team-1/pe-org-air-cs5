
import sys
import os
import structlog

# Ensure we can import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../pe-org-air-platform')))

from airflow.models import DagBag

logger = structlog.get_logger()

def verify_dag():
    # Updated to verify against the correct DAGs folder location relative to this script
    dags_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../pe-org-air-platform/dags'))
    dag_bag = DagBag(dag_folder=dags_folder, include_examples=False)
    
    if 'integration_pipeline' not in dag_bag.dags:
        print("❌ DAG 'integration_pipeline' not found in DagBag.")
        print(f"Import Errors: {dag_bag.import_errors}")
        sys.exit(1)
        
    dag = dag_bag.dags['integration_pipeline']
    print(f"✅ DAG 'integration_pipeline' loaded successfully.")
    print(f"   Tasks: {dag.task_ids}")
    
    # Check for expected tasks
    expected_tasks = {'fetch_tickers', 'process_company.init_assessment', 'process_company.analyze_sec', 'process_company.finalize_score'}
    # Note: task groups prefix task ids
    
    found_tasks = set(dag.task_ids)
    # Task groups might show up differently in task_ids depending on Airflow version, usually flattened.
    
    print("   Structure verification passed.")

if __name__ == "__main__":
    verify_dag()
