from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict
from datetime import datetime, timezone

from app.services.snowflake import db
from app.services.redis_cache import cache
from app.config import settings
import boto3

router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    dependencies: Dict[str, str]

async def check_snowflake() -> str:
    try:
        await db.execute("SELECT 1")
        return "healthy"
    except Exception:
        return "unhealthy"

async def check_redis() -> str:
    try:
        if cache.client.ping():
            return "healthy"
        return "unhealthy"
    except Exception:
        return "unhealthy"

async def check_s3() -> str:
    # S3 check - returns 'disabled' if not configured to avoid startup issues
    if not settings.S3_BUCKET or not settings.AWS_ACCESS_KEY_ID:
        return "disabled"
        
    try:
        # Extract secret values properly
        access_key = settings.AWS_ACCESS_KEY_ID.get_secret_value() if settings.AWS_ACCESS_KEY_ID else None
        secret_key = settings.AWS_SECRET_ACCESS_KEY.get_secret_value() if settings.AWS_SECRET_ACCESS_KEY else None
        
        if not access_key or not secret_key:
            return "disabled"
        
        s3 = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=settings.AWS_REGION
        )
        # Verify connectivity with a quick timeout
        s3.head_bucket(Bucket=settings.S3_BUCKET)
        return "healthy"
    except Exception as e:
        # If configured but fails, return unhealthy
        return "unhealthy"

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check health of all dependencies.
    Returns 200 if all healthy, 503 if any unhealthy.
    """
    
    dependencies = {
        "snowflake": await check_snowflake(),
        "redis": await check_redis(),
        "s3": await check_s3()
    }
    
    # Check if all critical dependencies are healthy
    # Filter out 'disabled' services from health check
    critical_statuses = [v for k, v in dependencies.items() if v != "disabled"]
    all_healthy = all(v == "healthy" for v in critical_statuses)
    
    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        timestamp=datetime.now(timezone.utc),
        version=settings.APP_VERSION,
        dependencies=dependencies
    )
