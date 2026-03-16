from fastapi import APIRouter
from typing import List
from app.models.industry import IndustryResponse
from app.services.snowflake import db
from app.services.redis_cache import cache

router = APIRouter()

@router.get("/", 
            response_model=List[IndustryResponse],
            summary="List industries",
            description="Retrieve a list of all supported industries and their associated baseline risk factors.")
async def list_industries():
    # Cache key for all industries (list is static-ish)
    cache_key = "industries:list"
    
    # Try cache
    cached_data = cache.client.get(cache_key)
    if cached_data:
        import json
        data = json.loads(cached_data)
        return [IndustryResponse.model_validate(item) for item in data]

    # Fetch from DB
    industries = await db.fetch_industries()
    response = [IndustryResponse.model_validate(i) for i in industries]
    
    # Cache for 1 hour
    import json
    cache.client.setex(
        cache_key,
        3600,
        json.dumps([m.model_dump(mode='json') for m in response])
    )
    
    return response
