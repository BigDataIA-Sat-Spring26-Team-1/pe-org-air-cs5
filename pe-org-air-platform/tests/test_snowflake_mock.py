
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.snowflake import SnowflakeService

@pytest.mark.asyncio
async def test_db_close_safe():
    db = SnowflakeService()
    mock_conn = MagicMock()
    db._conn = mock_conn
    await db.close()
    assert mock_conn.close.called
    assert db._conn is None

@pytest.mark.asyncio
async def test_industry_query_mock():
    db = SnowflakeService()
    with patch.object(db, 'fetch_all', new_callable=AsyncMock) as mock_all:
        mock_all.return_value = [{"id": "1", "name": "Tech"}]
        res = await db.fetch_industries()
        assert res[0]["name"] == "Tech"

@pytest.mark.asyncio
async def test_company_query_mock():
    db = SnowflakeService()
    with patch.object(db, 'fetch_all', new_callable=AsyncMock) as mock_all:
        mock_all.return_value = [{"id": "C1", "ticker": "T1"}]
        res = await db.fetch_companies(limit=10, offset=0)
        assert res[0]["ticker"] == "T1"

@pytest.mark.asyncio
async def test_snowflake_execution_mock():
    db = SnowflakeService()
    # Using 'execute_query' or '_execute_update' depending on the underlying implementation used by create_company
    # Looking at main.py, it uses db.execute() which is a thin wrapper.
    with patch.object(db, 'execute', new_callable=AsyncMock) as mock_exec:
        await db.create_industry({"id": "1", "name": "N"})
        assert mock_exec.called
