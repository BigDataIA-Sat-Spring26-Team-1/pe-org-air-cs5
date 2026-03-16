from fastapi import APIRouter
from app.models.dimension import DIMENSION_WEIGHTS
from app.services.redis_cache import cache
from app.config import settings
import json

router = APIRouter()

@router.get("/vars")
async def get_config_vars():
    """
    Expose non-sensitive configuration variables for the platform.
    """
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.APP_ENV,
        "snowflake": {
            "account": settings.SNOWFLAKE_ACCOUNT,
            "database": settings.SNOWFLAKE_DATABASE,
            "schema": settings.SNOWFLAKE_SCHEMA,
            "warehouse": settings.SNOWFLAKE_WAREHOUSE
        },
        "redis": {
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT
        },
        "features": {
            "patentsview_enabled": bool(settings.PATENTSVIEW_API_KEY),
            "s3_enabled": bool(settings.S3_BUCKET)
        }
    }

@router.get("/dimension-weights")
async def get_dimension_weights():
    cache_key = "config:dimension_weights"
    
    # Try cache
    cached = cache.client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # "Fetch" weights
    weights = DIMENSION_WEIGHTS
    
    # Cache for 24 hours (86400 seconds)
    cache.client.setex(cache_key, 86400, json.dumps(weights))
    
    return weights