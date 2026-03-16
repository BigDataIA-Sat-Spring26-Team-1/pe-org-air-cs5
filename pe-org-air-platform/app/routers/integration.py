
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import structlog
import httpx
from datetime import datetime
from app.pipelines.integration_pipeline import integration_pipeline

router = APIRouter(prefix="/integration")
logger = structlog.get_logger(__name__)

class IntegrationRequest(BaseModel):
    ticker: Optional[str] = None
    tickers: Optional[List[str]] = None

class IntegrationResult(BaseModel):
    status: str
    ticker: str
    company_id: Optional[str] = None
    final_score: Optional[float] = None
    v_r: Optional[float] = None
    h_r: Optional[float] = None
    synergy: Optional[float] = None
    confidence: Optional[float] = None
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    dimension_scores: Optional[Dict[str, float]] = None
    signals_added: Optional[int] = None
    assessment_id: Optional[str] = None
    error: Optional[str] = None

class BatchIntegrationResponse(BaseModel):
    results: List[IntegrationResult]
    total: int
    successful: int
    failed: int

@router.post("/run", response_model=BatchIntegrationResponse)
async def run_integration(request: IntegrationRequest):
    """
    This fetches data from Snowflake and recalculates deep analytical scores for one or more tickers.
    """
    tickers = []
    if request.ticker:
        tickers.append(request.ticker)
    if request.tickers:
        tickers.extend([t for t in request.tickers if t not in tickers])
    
    if not tickers:
        raise HTTPException(status_code=400, detail="No tickers provided")

    logger.info(f"API Triggered Batch Integration Pipeline for {tickers}")
    
    responses = []
    successful = 0
    failed = 0
    
    for ticker in tickers:
        try:
            results = await integration_pipeline.run_integration(ticker)
            
            if "error" in results:
                responses.append(IntegrationResult(
                    status="failed",
                    ticker=ticker,
                    error=results["error"]
                ))
                failed += 1
                continue
            
            final = results["final_score"]
            responses.append(IntegrationResult(
                status="success",
                ticker=ticker,
                company_id=results["company_id"],
                final_score=float(final["org_air_score"]),
                v_r=float(final["v_r"]),
                h_r=float(final["h_r"]),
                synergy=float(final["synergy"]),
                confidence=float(final["confidence"]),
                ci_lower=float(final["ci_lower"]),
                ci_upper=float(final["ci_upper"]),
                dimension_scores={k: float(v) for k, v in results["scores"].items()},
                signals_added=results["signals_added"],
                assessment_id=results["assessment_id"]
            ))
            successful += 1
            
        except Exception as e:
            logger.error(f"Integration failed for {ticker}: {str(e)}", exc_info=True)
            responses.append(IntegrationResult(
                status="failed",
                ticker=ticker,
                error=str(e)
            ))
            failed += 1

    return BatchIntegrationResponse(
        results=responses,
        total=len(tickers),
        successful=successful,
        failed=failed
    )

class AirflowTriggerResult(BaseModel):
    status: str
    ticker: str
    dag_run_id: Optional[str] = None
    error: Optional[str] = None

class BatchAirflowTriggerResponse(BaseModel):
    results: List[AirflowTriggerResult]
    total: int
    successful: int
    failed: int

@router.post("/run-airflow", response_model=BatchAirflowTriggerResponse)
async def run_integration_airflow(request: IntegrationRequest):
    """
    Trigger the Airflow integration_pipeline DAG for the provided tickers.
    """
    tickers = []
    if request.ticker:
        tickers.append(request.ticker)
    if request.tickers:
        tickers.extend([t for t in request.tickers if t not in tickers])
    
    if not tickers:
        raise HTTPException(status_code=400, detail="No tickers provided")

    logger.info(f"Triggering Airflow Integration Pipeline for {tickers}")
    
    responses = []
    successful = 0
    failed = 0
    
    # The Airflow Webserver is typically running internally on port 8080.
    airflow_url = "http://airflow-webserver:8080/api/v1/dags/integration_pipeline/dagRuns"
    auth = ("airflow", "airflow")
    
    async with httpx.AsyncClient() as client:
        for ticker in tickers:
            try:
                run_id = f"manual_api_trigger_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                payload = {
                    "dag_run_id": run_id,
                    "conf": {
                        "ticker": ticker
                    }
                }
                
                res = await client.post(airflow_url, json=payload, auth=auth, timeout=10.0)
                
                if res.status_code in [200, 201]:
                    data = res.json()
                    responses.append(AirflowTriggerResult(
                        status="success",
                        ticker=ticker,
                        dag_run_id=data.get("dag_run_id")
                    ))
                    successful += 1
                else:
                    error_msg = f"Airflow responded with status {res.status_code}: {res.text}"
                    logger.error(f"Failed to trigger Airflow for {ticker}: {error_msg}")
                    responses.append(AirflowTriggerResult(
                        status="failed",
                        ticker=ticker,
                        error=error_msg
                    ))
                    failed += 1
                    
            except Exception as e:
                logger.error(f"Airflow trigger error for {ticker}: {str(e)}")
                responses.append(AirflowTriggerResult(
                    status="failed",
                    ticker=ticker,
                    error=str(e)
                ))
                failed += 1

    return BatchAirflowTriggerResponse(
        results=responses,
        total=len(tickers),
        successful=successful,
        failed=failed
    )
