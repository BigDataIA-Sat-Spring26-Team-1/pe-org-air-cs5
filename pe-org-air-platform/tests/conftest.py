import pytest
import pytest_asyncio
import httpx

# Shared test configuration
BASE_URL = "http://localhost:8000"
TIMEOUT = 30.0  # Increased timeout for Snowflake connection delays

@pytest_asyncio.fixture
async def client():
    """Provide an async HTTP client hitting the app directly for coverage tracking."""
    from app.main import app
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client
