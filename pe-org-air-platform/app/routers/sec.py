from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

from app.pipelines.sec.pipeline import SecPipeline
from app.services.snowflake import db
from app.models.sec import (
    SecCollectRequest, 
    SecDocument, 
    SecDocumentChunk
)

logger = structlog.get_logger()
router = APIRouter()

active_tasks = set()

async def _run_pipeline(tickers: List[str], limit: int) -> None:
    for ticker in tickers:
        try:
            logger.info("pipeline_start", ticker=ticker)
            pipeline = SecPipeline()
            results = await pipeline.run(tickers=[ticker], limit=limit)
            logger.info("pipeline_complete", ticker=ticker, results=str(results))
        except Exception as e:
            logger.error("pipeline_failed", ticker=ticker, error=str(e))
        finally:
            if ticker in active_tasks:
                active_tasks.remove(ticker)


@router.post("/collect",
             summary="Collect SEC filings",
             description="Trigger the SEC pipeline to download, parse, and chunk filings (10-K, 10-Q, etc.) for target companies.")
async def collect_documents(req: SecCollectRequest, background_tasks: BackgroundTasks):
    """
    Trigger document collection for one or more tickers.
    """
    tickers = [t.strip().upper() for t in req.tickers if t and t.strip()]
    if not tickers:
        raise HTTPException(400, "tickers list is empty")

    started_tickers = []
    for t in tickers:
        if t in active_tasks:
            logger.info("task_already_running", ticker=t)
            continue
        
        active_tasks.add(t)
        started_tickers.append(t)
    
    if not started_tickers:
        return {
            "status": "ignored",
            "message": "Jobs for all tickers are already running."
        }

    background_tasks.add_task(_run_pipeline, started_tickers, req.limit)

    return {
        "status": "accepted",
        "tickers": started_tickers,
        "message": f"Collection queued for {len(started_tickers)} tickers"
    }


from app.services.redis_cache import cache

@router.get("", 
            response_model=List[SecDocument],
            summary="List SEC documents",
            description="Retrieve a list of processed SEC documents, filterable by company, ticker, or filing type.")
async def list_documents(
    company: Optional[str] = Query(default=None, description="Filter by ticker or company_name"),
    filing_type: Optional[str] = Query(default=None, description="Filter by filing_type e.g. 10-K"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """
    List documents (filterable).
    """
    # 1. Try Cache
    # Key normalization: treat None as "" to be safe, though str(None) is "None"
    cache_key = f"sec:docs:{company or 'all'}:{filing_type or 'all'}:{limit}:{offset}"
    
    cached_result = cache.get_list(cache_key, SecDocument)
    if cached_result is not None:
        return cached_result
        
    # 2. Fetch from DB
    docs = await db.fetch_sec_documents(company, filing_type, limit, offset)
    results = [SecDocument(**d) for d in docs]
    
    # 3. Set Cache (TTL 5 mins = 300s)
    cache.set_list(cache_key, results, ttl_seconds=300)
    
    return results


@router.get("/{document_id}", 
            response_model=SecDocument,
            summary="Get document details",
            description="Retrieve metadata for a specific SEC document.")
async def get_document(document_id: str):
    """Get document with metadata."""
    cache_key = f"sec:doc:{document_id}"
    
    # 1. Try Cache
    cached_doc = cache.get(cache_key, SecDocument)
    if cached_doc:
        return cached_doc

    # 2. Fetch from DB
    doc_data = await db.fetch_sec_document(document_id)
    if not doc_data:
        raise HTTPException(404, f"Document not found: {document_id}")
    
    result = SecDocument(**doc_data)
    
    # 3. Set Cache (TTL 10 mins = 600s)
    cache.set(cache_key, result, ttl_seconds=600)
    
    return result


@router.get("/{document_id}/chunks", 
            response_model=List[SecDocumentChunk],
            summary="Get document chunks",
            description="Retrieve the text chunks extracted from an SEC document, optionally filtered by section (e.g., 'Item 1. Business').")
async def get_document_chunks(
    document_id: str,
    section: Optional[str] = Query(default=None, description="Filter by section_name"),
    limit: int = Query(default=200, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
):
    """Get document chunks."""
    # Chunk lists can be huge, but caching standard pages helps.
    cache_key = f"sec:chunks:{document_id}:{section or 'all'}:{limit}:{offset}"
    
    cached_chunks = cache.get_list(cache_key, SecDocumentChunk)
    if cached_chunks:
        return cached_chunks

    chunks = await db.fetch_sec_document_chunks(document_id, section, limit, offset)
    results = [SecDocumentChunk(**c) for c in chunks]
    
    # Set Cache (TTL 5 mins)
    cache.set_list(cache_key, results, ttl_seconds=300)
    
    return results

import httpx

class AirflowTriggerResponse(BaseModel):
    status: str
    dag_run_id: Optional[str] = None
    error: Optional[str] = None

@router.post("/collect-airflow", response_model=AirflowTriggerResponse)
async def collect_documents_airflow(req: SecCollectRequest = None):
    """
    Trigger the Airflow sec_filing_ingestion DAG.
    """
    logger.info("Triggering Airflow SEC Ingestion Pipeline")
    
    airflow_url = "http://airflow-webserver:8080/api/v1/dags/sec_filing_ingestion/dagRuns"
    auth = ("airflow", "airflow")
    run_id = f"manual_api_trigger_sec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    payload = {"dag_run_id": run_id}
    
    # If the SEC dag is ever updated to accept conf.tickers, you could do:
    # if req and req.tickers:
    #     payload["conf"] = {"tickers": req.tickers}

    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(airflow_url, json=payload, auth=auth, timeout=10.0)
            if res.status_code in [200, 201]:
                data = res.json()
                return AirflowTriggerResponse(
                    status="success",
                    dag_run_id=data.get("dag_run_id")
                )
            else:
                error_msg = f"Airflow responded with status {res.status_code}: {res.text}"
                logger.error(f"Failed to trigger SEC Airflow: {error_msg}")
                return AirflowTriggerResponse(
                    status="failed",
                    error=error_msg
                )
        except Exception as e:
            logger.error(f"Airflow trigger error for SEC: {str(e)}")
            return AirflowTriggerResponse(
                status="failed",
                error=str(e)
            )