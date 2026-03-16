import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal
from app.pipelines.integration_pipeline import IntegrationPipeline

@pytest.fixture
def mock_db():
    with patch('app.pipelines.integration_pipeline.db') as mock_db:
        # Defaults
        mock_db.fetch_company_by_ticker.return_value = {"id": "comp-123", "industry_id": "ind-123"}
        mock_db.fetch_industry.return_value = {"sector": "Technology", "h_r_base": 70.0}
        mock_db.fetch_sec_chunks_by_company.return_value = [
            {"chunk_text": "we use machine learning for data. We have strong data governance and ai governance."}
        ]
        mock_db.fetch_culture_scores.return_value = [{"score": 4.5}]
        mock_db.fetch_company_evidence.return_value = [
            {"metadata": '{"github_stars": 500}'}
        ]
        
        # Make them all async
        mock_db.fetch_company_by_ticker = AsyncMock(return_value={"id": "comp-123", "industry_id": "ind-123"})
        mock_db.fetch_industry = AsyncMock(return_value={"sector": "Technology", "h_r_base": 70.0})
        mock_db.fetch_sec_chunks_by_company = AsyncMock(return_value=[
            {"chunk_text": "we use machine learning for data. We have strong data governance and ai governance."}
        ])
        mock_db.fetch_culture_scores = AsyncMock(return_value=[{"score": 4.5}])
        mock_db.fetch_company_evidence = AsyncMock(return_value=[
            {"metadata": '{"github_stars": 500, "followers": 1000, "pull_requests": 20}'}
        ])
        mock_db.fetch_glassdoor_reviews_for_talent = AsyncMock(return_value=[
            {"title": "Great Place", "pros": "nice ai team", "cons": "none"}
        ])
        mock_db.fetch_job_descriptions_for_talent = AsyncMock(return_value=[
            {"description": "machine learning AI research leader role"}
        ])
        
        mock_db.create_assessment = AsyncMock()
        mock_db.update_assessment_scores = AsyncMock()
        mock_db.create_dimension_score = AsyncMock()
        mock_db.create_external_signal = AsyncMock()
        mock_db.fetch_company_signal_summary = AsyncMock(return_value={})
        mock_db.fetch_glassdoor_reviews_for_talent = AsyncMock(return_value=[{"pros": "nice ai team"}])
        mock_db.execute = AsyncMock()
        mock_db._save_signal = AsyncMock()
        yield mock_db

@pytest.mark.asyncio
async def test_integration_pipeline_run_success(mock_db):
    pipeline = IntegrationPipeline()
    with patch.object(pipeline, '_save_signal', new_callable=AsyncMock) as mock_save:
        res = await pipeline.run_integration("AAPL")
        
        assert "final_score" in res
        assert "scores" in res
        
        # Verify db calls
        assert mock_db.fetch_company_by_ticker.called
        assert mock_db.create_assessment.called
        assert mock_db.create_dimension_score.call_count == 7 # For all 7 dimensions
        assert mock_db.execute.called

@pytest.mark.asyncio
async def test_integration_pipeline_run_not_found(mock_db):
    mock_db.fetch_company_by_ticker.return_value = None
    
    pipeline = IntegrationPipeline()
    res = await pipeline.run_integration("UNKNOWN")
    
    assert "error" in res
    assert res["error"] == "Company not found"
