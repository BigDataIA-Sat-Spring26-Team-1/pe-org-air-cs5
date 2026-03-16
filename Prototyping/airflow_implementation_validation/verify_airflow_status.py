
import urllib.request
import urllib.error
import base64
import json

AIRFLOW_URL = "http://localhost:8080/api/v1"
AUTH = base64.b64encode(b"airflow:airflow").decode("ascii")

def get_json(url, params=None):
    if params:
        query_string = urllib.parse.urlencode(params)
        url = f"{url}?{query_string}"
    
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Basic {AUTH}")
    
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.URLError as e:
        print(f"Failed request to {url}: {e}")
        return {}

def check_dag_runs(dag_id, limit=5):
    print(f"\n--- Checking Runs for {dag_id} ---")
    url = f"{AIRFLOW_URL}/dags/{dag_id}/dagRuns"
    data = get_json(url, {"limit": limit, "order_by": "-execution_date"})
    
    runs = data.get('dag_runs', [])
    if not runs:
        print("No runs found.")
        return

    for run in runs:
        state = run['state']
        run_id = run['dag_run_id']
        start_date = run['start_date']
        print(f"Run ID: {run_id} | State: {state} | Start: {start_date}")
        
        if state == 'failed':
            check_task_failures(dag_id, run_id)

def check_task_failures(dag_id, run_id):
    url = f"{AIRFLOW_URL}/dags/{dag_id}/dagRuns/{run_id}/taskInstances"
    try:
        data = get_json(url)
        tasks = data.get('task_instances', [])
        
        failures = [t for t in tasks if t['state'] == 'failed']
        for f in failures:
            print(f"  -> FAILED TASK: {f['task_id']} (Try {f['try_number']})")
            
    except Exception as e:
        print(f"Error checking tasks: {e}")

if __name__ == "__main__":
    check_dag_runs("sec_filing_ingestion")
    check_dag_runs("sec_backfill")
    check_dag_runs("sec_quality_monitor")
