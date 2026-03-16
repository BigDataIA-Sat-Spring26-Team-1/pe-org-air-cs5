
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.backfill import BackfillService

@pytest.mark.asyncio
async def test_backfill_initial_state():
    service = BackfillService()
    assert service.stats["status"] == "idle"
    assert service.stats["companies"] == 0

@pytest.mark.asyncio
async def test_backfill_running_status():
    service = BackfillService()
    assert not service.is_running()
    service._stats["status"] = "running"
    assert service.is_running()

@pytest.mark.asyncio
async def test_backfill_execution_flow():
    service = BackfillService()
    
    with patch('app.services.snowflake.db.fetch_industries', new_callable=AsyncMock) as mock_industries, \
         patch('app.services.snowflake.db.fetch_company_by_ticker', new_callable=AsyncMock) as mock_fetch_comp, \
         patch('app.services.snowflake.db.create_company', new_callable=AsyncMock) as mock_create_comp, \
         patch('app.pipelines.sec.pipeline.SecPipeline.run', new_callable=AsyncMock) as mock_sec, \
         patch('app.pipelines.external_signals.orchestrator.MasterPipeline.run', new_callable=AsyncMock) as mock_signals, \
         patch('app.services.snowflake.db.upsert_company_signal_summary', new_callable=AsyncMock), \
         patch('app.services.snowflake.db.create_external_signals_bulk', new_callable=AsyncMock), \
         patch('app.services.redis_cache.cache.delete', new_callable=MagicMock):
        
        mock_industries.return_value = [{"id": "1", "name": "Manufacturing"}]
        mock_fetch_comp.return_value = None
        mock_sec.return_value = {"processed": 2}
        mock_signals.return_value = {
            "summary": {"company_id": "123"},
            "signals": [],
            "evidence": []
        }
        
        await service.run_backfill(custom_targets={"CAT": {"name": "Caterpillar", "sector": "Manufacturing"}})
        
        assert service.stats["status"] == "completed"
        assert service.stats["companies"] == 1
        assert service.stats["documents"] == 2
