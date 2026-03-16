
from datetime import datetime, timedelta
from airflow import DAG
from airflow.decorators import task, task_group
from airflow.models.param import Param
from airflow.utils.trigger_rule import TriggerRule
import asyncio
import structlog
import logging

# Import the refactored pipeline
from app.pipelines.integration_pipeline import integration_pipeline

logger = structlog.get_logger()

# Default arguments
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "integration_pipeline",
    default_args=default_args,
    description="Orchestrates the full PE Org-AI-R Integration Pipeline",
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["integration", "scoring", "core"],
    params={
        "ticker": Param(None, type=["null", "string"], description="Specific ticker to process (optional)"),
    }
) as dag:

    @task
    def fetch_tickers(**context):
        """
        Get list of companies to process.
        """
        target_ticker = context["params"].get("ticker")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        if target_ticker:
            logger.info(f"Manual run for single ticker: {target_ticker}")
            return [target_ticker]
        else:
            tickers = loop.run_until_complete(integration_pipeline.get_active_tickers())
            logger.info(f"Scheduled run for {len(tickers)} companies: {tickers}")
            return tickers

    @task
    def init_assessment(ticker: str):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(integration_pipeline.init_company_assessment(ticker))

    @task
    def analyze_sec(context: dict):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(integration_pipeline.analyze_sec_rubric(context))

    @task
    def analyze_board(context: dict):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(integration_pipeline.analyze_board(context))

    @task
    def analyze_talent(context: dict):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(integration_pipeline.analyze_talent(context))

    @task
    def analyze_culture(context: dict):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(integration_pipeline.analyze_culture(context))

    @task(trigger_rule=TriggerRule.ALL_DONE)
    def finalize_score(context: dict, sec_res: dict, board_res: dict, talent_res: dict, culture_res: dict):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        sec_res = sec_res or {}
        board_res = board_res or {}
        talent_res = talent_res or {}
        culture_res = culture_res or {}
        
        return loop.run_until_complete(
            integration_pipeline.calculate_final_score(context, sec_res, board_res, talent_res, culture_res)
        )

    # --- Mapped Task Group ---
    @task_group(group_id="process_company")
    def process_company_group(ticker: str):
        # 1. Initialize Context
        context = init_assessment(ticker)
        
        # 2. Parallel Analysis
        sec_res = analyze_sec(context)
        board_res = analyze_board(context)
        talent_res = analyze_talent(context)
        culture_res = analyze_culture(context)
        
        # 3. Finalize (Implicitly waits for all 4 inputs)
        finalize_score(
            context=context,
            sec_res=sec_res,
            board_res=board_res,
            talent_res=talent_res,
            culture_res=culture_res
        )

    # --- Workflow Execution ---
    tickers = fetch_tickers()
    process_company_group.expand(ticker=tickers)
