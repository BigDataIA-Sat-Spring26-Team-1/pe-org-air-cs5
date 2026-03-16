from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional, List
from uuid import UUID, uuid4
import json
from app.models.company import CompanyCreate, CompanyResponse
from app.models.signals import ExternalSignal, SignalCategory, SignalEvidence
from app.models.common import PaginatedResponse
from app.routers.routers_utils import create_paginated_response, get_offset
from app.services.snowflake import db
from app.services.redis_cache import cache

router = APIRouter()

@router.post("/", 
             response_model=CompanyResponse, 
             status_code=status.HTTP_201_CREATED,
             summary="Create a new company",
             description="Register a new company in the system for intelligence tracking.")
async def create_company(company: CompanyCreate):
    new_id = uuid4()
    company_data = company.model_dump()
    company_data['id'] = new_id
    
    await db.create_company(company_data)
    
    # Invalidate list cache
    cache.delete_pattern("companies:list:*")
    
    # Fetch back to get timestamps
    created_company = await db.fetch_company(str(new_id))
    if not created_company:
        raise HTTPException(status_code=500, detail="Failed to retrieve created company")
        
    return created_company

@router.get("/", 
            response_model=PaginatedResponse[CompanyResponse],
            summary="List companies",
            description="Retrieve a paginated list of companies, optionally filtered by industry.")
async def list_companies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    industry_id: Optional[UUID] = None
):
    # Cache key based on params
    cache_key = f"companies:list:{page}:{page_size}:{industry_id}"
    cached = cache.get(cache_key, PaginatedResponse[CompanyResponse])
    if cached:
        return cached

    offset = get_offset(page, page_size)
    companies = await db.fetch_companies(limit=page_size, offset=offset, industry_id=str(industry_id) if industry_id else None)
    total_count = await db.count_companies(industry_id=str(industry_id) if industry_id else None)
    
    response = create_paginated_response(
        items=[CompanyResponse.model_validate(c) for c in companies],
        total=total_count,
        page=page,
        page_size=page_size
    )
    
    # Cache for 60 seconds
    cache.set(cache_key, response, ttl_seconds=60)
    
    return response

@router.get("/{company_id}", 
            response_model=CompanyResponse,
            summary="Get company details",
            description="Retrieve detailed information about a specific company by its ID or ticker symbol.")
async def get_company(company_id: str):
    cache_key = f"company:{company_id}"
    
    # Try cache first
    cached = cache.get(cache_key, CompanyResponse)
    if cached:
        return cached
    
    # Fetch from DB - Try ID first
    company = await db.fetch_company(company_id)
    
    # If not found by ID, try fetching by ticker
    if not company:
        company = await db.fetch_company_by_ticker(company_id.upper())
        
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    company_model = CompanyResponse.model_validate(company)
    
    # Cache for 5 minutes
    cache.set(cache_key, company_model, ttl_seconds=300)
    
    return company_model

@router.put("/{company_id}", 
            response_model=CompanyResponse,
            summary="Update company",
            description="Update the information for an existing company.")
async def update_company(company_id: UUID, company_update: CompanyCreate):
    # Check existence
    existing = await db.fetch_company(str(company_id))
    if not existing:
        raise HTTPException(status_code=404, detail="Company not found")
    
    update_data = company_update.model_dump()
    await db.update_company(str(company_id), update_data)
    
    # Invalidate caches
    cache.delete(f"company:{company_id}")
    cache.delete_pattern("companies:list:*")
    
    updated = await db.fetch_company(str(company_id))
    return updated

@router.delete("/{company_id}", 
               status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete company",
               description="Mark a company as deleted in the system.")
async def delete_company(company_id: UUID):
    # Check existence
    existing = await db.fetch_company(str(company_id))
    if not existing:
        raise HTTPException(status_code=404, detail="Company not found")
        
    await db.delete_company(str(company_id))
    
    # Invalidate caches
    cache.delete(f"company:{company_id}")
    cache.delete_pattern("companies:list:*")

@router.get("/{company_id}/signals/{category}", 
            response_model=List[ExternalSignal],
            summary="Get signals by category",
            description="Retrieve external intelligence signals for a company by ID or ticker within a specific category.")
async def get_signals_by_company_category(company_id: str, category: SignalCategory):
    """Get signals by category for a specific company"""
    # Check existence - Try ID first
    company = await db.fetch_company(company_id)
    
    # Try Ticker fallback
    if not company:
        company = await db.fetch_company_by_ticker(company_id.upper())
        
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    actual_id = company['id']
    signals = await db.fetch_external_signals(actual_id, category)
    
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
        except Exception:
            continue
            
    return signal_models

@router.get("/{company_id}/evidence", 
            response_model=List[SignalEvidence],
            summary="Get company evidence",
            description="Retrieve all granular evidence items (jobs, patents, etc.) for a specific company by ID or ticker.")
async def get_company_evidence(company_id: str):
    """Get all evidence for a company"""
    # Check existence - Try ID first
    company = await db.fetch_company(company_id)
    
    # Try Ticker fallback
    if not company:
        company = await db.fetch_company_by_ticker(company_id.upper())
        
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    actual_id = company['id']
    evidence = await db.fetch_signal_evidence(actual_id)
    
    evidence_models = []
    for e in evidence:
        try:
            # Handle Snowflake Date objects
            if hasattr(e.get('evidence_date'), 'isoformat'):
                e['evidence_date'] = e['evidence_date'].isoformat()
            
            # Ensure metadata and tags are parsed
            if isinstance(e.get('metadata'), str):
                e['metadata'] = json.loads(e['metadata'])
            if isinstance(e.get('tags'), str):
                e['tags'] = json.loads(e['tags'])
                
            evidence_models.append(SignalEvidence(**e))
        except Exception:
            continue
            
    return evidence_models