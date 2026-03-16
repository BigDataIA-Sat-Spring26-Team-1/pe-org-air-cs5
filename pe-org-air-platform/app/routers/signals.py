from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import List, Optional, Dict, Any
from app.models.signals import SignalCollectionRequest, CompanySignalSummary, ExternalSignal, SignalCategory, SignalEvidence
from app.services.snowflake import db
from app.services.redis_cache import cache
from app.pipelines.external_signals.orchestrator import MasterPipeline
from app.config import settings
import logging
from datetime import datetime, timedelta
import hashlib
import json

from app.pipelines.glassdoor.glassdoor_orchestrator import GlassdoorOrchestrator
from app.pipelines.glassdoor.glassdoor_collector import COMPANY_IDS

router = APIRouter()
logger = logging.getLogger("app")

# Background worker for Glassdoor
async def run_glassdoor_pipeline(ticker: str, limit: int):
    try:
        orch = GlassdoorOrchestrator()
        await orch.run_pipeline(ticker=ticker, limit=limit)
        logger.info(f"Glassdoor pipeline completed for {ticker}")
    except Exception as e:
        logger.error(f"Glassdoor pipeline failed for {ticker}: {e}")

@router.post("/collect/glassdoor", status_code=202)
async def collect_glassdoor_reviews(
    ticker: str, 
    background_tasks: BackgroundTasks,
    limit: int = Query(20, ge=1, le=100)
):
    """Trigger Glassdoor review collection in the background."""
    # Check if we have an ID for this ticker
    gid = COMPANY_IDS.get(ticker.upper())
    if not gid:
        raise HTTPException(status_code=400, detail=f"No Glassdoor ID mapped for ticker {ticker}. Manual mapping required.")

    background_tasks.add_task(run_glassdoor_pipeline, ticker.upper(), limit)
    return {"message": f"Glassdoor collection queued for {ticker}", "status": "queued"}

@router.get("/culture/{ticker}")
async def get_culture_scores(ticker: str):
    """Retrieve latest culture scores for a company."""
    scores = await db.fetch_culture_scores(ticker.upper())
    if not scores:
        return {"message": "No culture scores found for this ticker."}
    
    # Culture scores contains lists of keywords as VARIANT, sometimes need parsing if returned as JSON strings
    s = scores[0]
    if isinstance(s.get('positive_keywords_found'), str):
        s['positive_keywords_found'] = json.loads(s['positive_keywords_found'])
    if isinstance(s.get('negative_keywords_found'), str):
        s['negative_keywords_found'] = json.loads(s['negative_keywords_found'])
        
    return s

@router.get("/culture/reviews/{ticker}")
async def get_glassdoor_reviews(
    ticker: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Retrieve granular Glassdoor reviews for a company."""
    reviews = await db.fetch_glassdoor_reviews(ticker.upper(), limit, offset)
    return reviews

# Active collection tasks
active_tasks = set()

async def resolve_company(ticker: Optional[str] = None, company_name: Optional[str] = None) -> Dict[str, Any]:
    """Look up company by ticker or name."""
    if not ticker and not company_name:
        raise HTTPException(status_code=400, detail="Either 'ticker' or 'company_name' must be provided.")

    company_records = await db.fetch_companies_by_ticker_or_name(ticker, company_name)
    
    if not company_records:
        raise HTTPException(
            status_code=404, 
            detail=f"Company with ticker='{ticker}' or name='{company_name}' not found. Please add the company first."
        )

    # Check for mismatches if both were provided
    if ticker and company_name:
        matching_record = next((r for r in company_records if r['ticker'] == ticker and r['name'] == company_name), None)
        if not matching_record:
            raise HTTPException(
                status_code=400,
                detail=f"Mismatch identified: Ticker '{ticker}' and Name '{company_name}' do not belong to the same company."
            )
        return matching_record
    
    return company_records[0]

async def run_collection_task(request: SignalCollectionRequest):
    """Runs the MasterPipeline and saves results in the background."""
    ticker = request.ticker
    try:
        pipeline = MasterPipeline()
        results = await pipeline.run(
            company_name=request.company_name,
            ticker=request.ticker,
            company_id=request.company_id,
            job_days=request.job_days,
            patent_years=request.patent_years
        )
        
        # Save summary
        await db.upsert_company_signal_summary(results['summary'])
        
        # Prepare signals with deduplication hashes
        signals_to_save = []
        for s in results['signals']:
             if not s.get('signal_hash'):
                 raw_val = s.get('raw_value', '')
                 hash_input = f"{s['company_id']}{s['source']}{raw_val}"
                 s['signal_hash'] = hashlib.sha256(hash_input.encode()).hexdigest()
             signals_to_save.append(s)

        # Bulk save signals (pulse records)
        try:
            await db.create_external_signals_bulk(signals_to_save)
            logger.info(f"Bulk saved {len(signals_to_save)} pulse records for {ticker}")
        except Exception as e:
            logger.warning(f"Bulk signal save failed, falling back to sequential: {e}")
            # Optional: Fallback logic here if needed, but bulk usually works
            pass

        # Bulk save granular evidence
        evidence_list = results.get('evidence', [])
        if evidence_list:
            try:
                await db.create_signal_evidence_bulk(evidence_list)
                logger.info(f"Bulk saved {len(evidence_list)} granular evidence records for {ticker}")
            except Exception as e:
                logger.error(f"Failed to bulk save evidence: {e}")
        
        # Invalidate Redirect Cache
        company_id = request.company_id
        cache.delete(f"signals:summary:{company_id}")
        cache.delete_pattern(f"signals:list:{company_id}:*")
        
        logger.info(f"Successfully completed signal collection for {ticker}")
    except Exception as e:
        logger.error(f"Error in background collection for {ticker}: {e}")
    finally:
        if ticker in active_tasks:
            active_tasks.remove(ticker)

@router.post("/collect", 
             status_code=202,
             summary="Collect signals",
             description="Triggers the orchestrator to collect external signals (jobs, patents, etc.) for a specific company in the background.")
async def collect_signals(request: SignalCollectionRequest, background_tasks: BackgroundTasks):
    """Start background data collection for a company."""
    # Verify company exists
    target_company = await resolve_company(request.ticker, request.company_name)

    # Populate request object with complete data for the orchestrator
    request.company_id = target_company['id']
    request.ticker = target_company['ticker']
    request.company_name = target_company['name']
    
    company_id = request.company_id
    ticker = request.ticker

    # Prevent concurrent runs
    if ticker in active_tasks:
        return {"message": f"Collection task for {ticker} is already in progress.", "status": "active"}
    
    # Check for recent results
    if not request.force_refresh:
        summary_data = await db.fetch_company_signal_summary(company_id)
        if summary_data:
            last_updated = summary_data.get('last_updated')
            if last_updated:
                now = datetime.now(last_updated.tzinfo) if last_updated.tzinfo else datetime.utcnow()
                if last_updated > now - timedelta(hours=24):
                    return {
                        "message": f"Recent data for {ticker} already exists.",
                        "status": "cached",
                        "summary": summary_data
                    }

    # Queue background task
    active_tasks.add(ticker)
    background_tasks.add_task(run_collection_task, request)
    
    return {"message": f"Started initial collection for {ticker} ({request.company_name}) in background.", "status": "started"}

@router.get("/", 
            response_model=List[ExternalSignal],
            summary="List all signals",
            description="Retrieve a paginated list of all external intelligence signals, optionally filtered by company or category.")
async def list_signals(
    ticker: Optional[str] = None,
    company_name: Optional[str] = None,
    company_id: Optional[str] = None,
    category: Optional[SignalCategory] = None,
    limit: int = Query(100, ge=1, le=500, description="Maximum number of signals to return"),
    offset: int = Query(0, ge=0, description="Number of signals to skip")
):
    """Lists granular signals for a company with pagination."""
    if not company_id:
        target_company = await resolve_company(ticker, company_name)
        company_id = target_company['id']

    cache_key = f"signals:list:{company_id}:{category if category else 'all'}:{limit}:{offset}"
    
    # Check cache
    cached = cache.get_list(cache_key, ExternalSignal)
    if cached:
        return cached
        
    # Fetch from DB with pagination
    signals = await db.fetch_external_signals(company_id, category, limit, offset)
    
    signal_models = []
    for s in signals:
        try:
            # Handle Snowflake Date objects
            if hasattr(s.get('signal_date'), 'isoformat'):
                s['signal_date'] = s['signal_date'].isoformat()
            
            # Parse JSON strings if needed
            if isinstance(s.get('metadata'), str):
                s['metadata'] = json.loads(s['metadata'])
                
            signal_models.append(ExternalSignal(**s))
        except Exception as err:
            logger.warning(f"Failed to parse signal: {err}")
            continue
    
    # Cache the results
    cache.set_list(cache_key, signal_models, ttl_seconds=3600)
    return signal_models

@router.get("/evidence", 
            response_model=List[SignalEvidence],
            summary="List all evidence",
            description="Retrieve a paginated list of all granular evidence items (individual job postings, patents, etc.).")
async def list_evidence(
    ticker: Optional[str] = None,
    company_name: Optional[str] = None,
    company_id: Optional[str] = None,
    category: Optional[SignalCategory] = None,
    limit: int = Query(100, ge=1, le=500, description="Maximum number of evidence items to return"),
    offset: int = Query(0, ge=0, description="Number of evidence items to skip")
):
    """Lists granular evidence items (jobs, patents, etc) for a company with pagination."""
    if not company_id:
        target_company = await resolve_company(ticker, company_name)
        company_id = target_company['id']
    
    # Fetch from DB with pagination
    evidence = await db.fetch_signal_evidence(company_id, category, limit, offset)
    
    evidence_models = []
    for e in evidence:
        try:
            # Handle Snowflake Date objects
            if hasattr(e.get('evidence_date'), 'isoformat'):
                e['evidence_date'] = e['evidence_date'].isoformat()
            
            # Ensure metadata and tags are parsed if they come back as strings
            if isinstance(e.get('metadata'), str):
                e['metadata'] = json.loads(e['metadata'])
            if isinstance(e.get('tags'), str):
                e['tags'] = json.loads(e['tags'])
                
            evidence_models.append(SignalEvidence(**e))
        except Exception as err:
            logger.warning(f"Failed to parse evidence: {err}")
            continue
    
    return evidence_models

@router.get("/summary", 
            response_model=CompanySignalSummary,
            summary="Get company summary",
            description="Retrieve the aggregated intelligence summary for a company, including composite scores and category breakdowns.")
async def get_company_summary(
    ticker: Optional[str] = None,
    company_name: Optional[str] = None
):
    """Returns the latest signal summary for a company."""
    target_company = await resolve_company(ticker, company_name)
    company_id = target_company['id']

    cache_key = f"signals:summary:{company_id}"
    
    # Check cache
    cached = cache.get(cache_key, CompanySignalSummary)
    if cached:
        return cached
        
    # Fetch from DB
    summary = await db.fetch_company_signal_summary(company_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found for this company")
    
    # Store in cache
    summary_model = CompanySignalSummary(**summary)
    cache.set(cache_key, summary_model, 86400)
    
    return summary_model

@router.get("/details/{category}", 
            response_model=List[ExternalSignal],
            summary="Get signals by category",
            description="Retrieve all granular signals belonging to a specific intelligence category (e.g., technology_hiring) for a company.")
async def get_signals_by_category(
    category: SignalCategory,
    ticker: Optional[str] = None,
    company_name: Optional[str] = None
):
    """Returns granular signals for a specific category."""
    target_company = await resolve_company(ticker, company_name)
    company_id = target_company['id']

    cache_key = f"signals:list:{company_id}:{category}"
    
    # Check cache
    cached = cache.get_list(cache_key, ExternalSignal)
    if cached:
        return cached
        
    # Fetch from DB
    signals = await db.fetch_external_signals(company_id, category)
    
    if signals:
        signal_models = []
        for s in signals:
            try:
                # Handle Snowflake Date objects
                if hasattr(s.get('signal_date'), 'isoformat'):
                    s['signal_date'] = s['signal_date'].isoformat()
                
                # Parse JSON strings if needed
                if isinstance(s.get('metadata'), str):
                    s['metadata'] = json.loads(s['metadata'])
                    
                signal_models.append(ExternalSignal(**s))
            except Exception as err:
                logger.warning(f"Failed to parse signal in category {category}: {err}")
                continue
        
        cache.set_list(cache_key, signal_models, 86400)
        return signal_models
        
    return []