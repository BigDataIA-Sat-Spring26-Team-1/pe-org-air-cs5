from fastapi import APIRouter, BackgroundTasks
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from app.services.backfill import backfill_service

router = APIRouter()

class CompanyInput(BaseModel):
    ticker: str = Field(..., description="Company stock ticker symbol")
    name: Optional[str] = Field(None, description="Formal company name (defaults to ticker)")
    sector: Optional[str] = Field("Technology", description="Industry or sector name")

class BatchCollectRequest(BaseModel):
    targets: Optional[List[CompanyInput]] = Field(None, description="Optional list of companies. If null or empty, defaults to target_companies.")

@router.post("/collect",
             status_code=202,
             summary="Targeted batch collection",
             description="Starts a background process to collect SEC data and signals for a custom list of companies.")
async def batch_collect_endpoint(request: BatchCollectRequest, background_tasks: BackgroundTasks):
    """Run interactive collection for specific companies"""
    if backfill_service.is_running():
        return {
            "message": "A collection process is already in progress", 
            "status": backfill_service.stats["status"]
        }
    
    # Transform list to the dict format service expects: {ticker: {name, sector}}
    custom_targets: Optional[Dict[str, Dict[str, str]]] = None
    if request.targets:
        custom_targets = {}
        for t in request.targets:
            custom_targets[t.ticker.upper()] = {
                "name": t.name or t.ticker.upper(),
                "sector": t.sector or "Technology"
            }
        
    background_tasks.add_task(backfill_service.run_backfill, custom_targets)
    
    msg = f"Custom collection started for {len(custom_targets)} targets" if custom_targets else "Full portfolio backfill started"
    
    return {
        "message": msg,
        "status": "started",
        "targets": list(custom_targets.keys()) if custom_targets else backfill_service.target_companies
    }

@router.post("/backfill", 
             status_code=202,
             summary="Run full backfill",
             description="Starts a background process to collect external evidence (SEC data, signals). If targets are provided, it only processes those.")
async def backfill_evidence_endpoint(background_tasks: BackgroundTasks, request: Optional[BatchCollectRequest] = None):
    """Backfill evidence for targets (defaults to all 10 companies)"""
    if backfill_service.is_running():
        return {
            "message": "Backfill already in progress", 
            "status": backfill_service.stats["status"]
        }
    
    # Process optional targets
    custom_targets: Optional[Dict[str, Dict[str, str]]] = None
    if request and request.targets:
        custom_targets = {}
        for t in request.targets:
            custom_targets[t.ticker.upper()] = {
                "name": t.name or t.ticker.upper(),
                "sector": t.sector or "Technology"
            }
        
    background_tasks.add_task(backfill_service.run_backfill, custom_targets)
    
    msg = f"Backfill started for {len(custom_targets)} companies" if custom_targets else "Backfill started for standard portfolio (10 companies)"
    
    return {
        "message": msg,
        "status": "started",
        "targets": list(custom_targets.keys()) if custom_targets else backfill_service.target_companies
    }

@router.get("",
            summary="List evidence",
            description="Fetch evidence items with optional filtering by indexing status.")
async def list_evidence(indexed: Optional[bool] = None, limit: int = 100):
    """List evidence items from CS2."""
    from app.services.snowflake import db
    if indexed is False:
        return await db.fetch_unindexed_evidence(limit=limit)
    
    # Generic fetch (not strictly required by DAG but good for API)
    query = "SELECT * FROM signal_evidence ORDER BY created_at DESC LIMIT %s"
    return await db.fetch_all(query, (limit,))

class MarkIndexedRequest(BaseModel):
    evidence_ids: List[str]

@router.post("/mark-indexed",
             summary="Mark evidence as indexed",
             description="Updates the indexed_in_cs4 flag for the given evidence IDs.")
async def mark_evidence_indexed(request: MarkIndexedRequest):
    """Mark evidence as indexed in CS4."""
    from app.services.snowflake import db
    await db.mark_evidence_indexed(request.evidence_ids)
    return {"status": "success", "count": len(request.evidence_ids)}

@router.get("/stats",
            summary="Get backfill stats",
            description="Retrieve progress statistics and status of the current or most recent backfill operation.")
async def get_evidence_stats():
    """Get evidence collection statistics"""
    stats = backfill_service.stats.copy()
    
    # If idle, fetch actual historical stats from DB to show on dashboard
    if stats["status"] == "idle" or stats["status"] == "completed":
        from app.services.snowflake import db
        company_metrics = await db.fetch_company_metrics()
        stats["companies"] = len(company_metrics)
        stats["signals"] = sum(c['signals'] for c in company_metrics)
        stats["documents"] = sum(c['filings'] for c in company_metrics)
        # Fetch culture signal count if method exists, or just rely on backfill_service stats
        # For now, let's just ensure culture_data is present in the returned stats
    
    return stats
