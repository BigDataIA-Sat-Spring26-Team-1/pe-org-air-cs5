
import sys
import asyncio
from unittest.mock import MagicMock, AsyncMock
import datetime
from decimal import Decimal

# MOCK DEPENDENCIES BEFORE IMPORTING APP MODULES
sys.modules["structlog"] = MagicMock()
sys.modules["airflow"] = MagicMock()
sys.modules["boto3"] = MagicMock()
sys.modules["botocore"] = MagicMock()
sys.modules["botocore.exceptions"] = MagicMock()
sys.modules["pandas"] = MagicMock()
sys.modules["pdfkit"] = MagicMock()
sys.modules["httpx"] = MagicMock()
sys.modules["numpy"] = MagicMock()
sys.modules["tenacity"] = MagicMock()
sys.modules["sklearn"] = MagicMock()
sys.modules["nltk"] = MagicMock()
sys.modules["bs4"] = MagicMock()
sys.modules["lxml"] = MagicMock()
sys.modules["requests"] = MagicMock()
sys.modules["fastapi"] = MagicMock()
sys.modules["uvicorn"] = MagicMock()

# Mock Pydantic
pydantic_mock = MagicMock()
pydantic_mock.BaseModel = type("BaseModel", (object,), {})
pydantic_mock.Field = MagicMock(return_value=None)
sys.modules["pydantic"] = pydantic_mock
sys.modules["pydantic_settings"] = MagicMock()
sys.modules["pydantic_settings"].BaseSettings = type("BaseSettings", (object,), {})
sys.modules["pydantic_settings"].SettingsConfigDict = MagicMock()

# Mock DB and Cache
mock_db = AsyncMock()
sys.modules["app.services.snowflake"] = MagicMock()
sys.modules["app.services.snowflake"].db = mock_db

sys.modules["app.services.redis_cache"] = MagicMock()
sys.modules["app.services.redis_cache"].cache = AsyncMock()

# Now import the pipeline
# We need to make sure we can import local modules
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../pe-org-air-platform')))

from app.pipelines.integration_pipeline import IntegrationPipeline

async def test_pipeline():
    print("🚀 Starting Manual Integration Pipeline Test...")
    
    pipeline = IntegrationPipeline()
    
    # --- Mock Data Setup ---
    ticker = "TEST"
    company_id = "test-uuid"
    
    # Mock db.fetch_company_by_ticker
    mock_db.fetch_company_by_ticker.return_value = {
        "id": company_id,
        "ticker": ticker,
        "sector": "Technology",
        "position_factor": 0.5
    }
    
    # Mock db.fetch_company_signal_summary
    mock_db.fetch_company_signal_summary.return_value = {
        "digital_presence_score": 60.0,
        "technology_hiring_score": 70.0,
        "leadership_signals_score": 80.0,
        "innovation_activity_score": 90.0
    }
    
    # Mock SEC chunks
    mock_db.fetch_sec_chunks_by_company.return_value = [
        {"chunk_text": "We are investing heavily in AI and machine learning."}
    ]
    
    # Mock Board Data (via board_analyzer which calls DB/API)
    # We'll mock the internal board_analyzer method instead of DB for this
    pipeline.board_analyzer.fetch_board_data = MagicMock(return_value=([], []))
    pipeline.board_analyzer.analyze_board = MagicMock()
    pipeline.board_analyzer.analyze_board.return_value.governance_score = Decimal("85.0")
    pipeline.board_analyzer.analyze_board.return_value.confidence = Decimal("0.9")
    pipeline.board_analyzer.analyze_board.return_value.independent_ratio = 0.8
    
    # Mock Talent
    pipeline.talent_calculator.get_company_talent_risk = AsyncMock(return_value={
        "talent_concentration_score": 0.2,
        "talent_risk_adjustment": 0.95,
        "breakdown": {}
    })
    
    # Mock Glassdoor
    mock_db.fetch_glassdoor_reviews_for_talent.return_value = [] # Return empty to skip complex parsing logic for now
    
    # --- Execute Steps ---
    
    # 1. Init
    print("\n[Step 1] Initializing...")
    context = await pipeline.init_company_assessment(ticker)
    print(f"✅ Context: {context}")
    assert context["ticker"] == ticker
    assert context["company_id"] == company_id
    
    # 2. SEC
    print("\n[Step 2] Analyzing SEC...")
    # Mock rubric scorer result
    pipeline.rubric_scorer.score_dimension = MagicMock()
    pipeline.rubric_scorer.score_dimension.return_value.score = 75.0
    pipeline.rubric_scorer.score_dimension.return_value.confidence = 0.8
    pipeline.rubric_scorer.score_dimension.return_value.rationale = "Good AI"
    pipeline.rubric_scorer.score_dimension.return_value.level.name = "LEVEL_3"
    
    sec_res = await pipeline.analyze_sec_rubric(context)
    print(f"✅ SEC Result: {sec_res}")
    
    # 3. Board
    print("\n[Step 3] Analyzing Board...")
    board_res = await pipeline.analyze_board(context)
    print(f"✅ Board Result: {board_res}")
    
    # 4. Talent
    print("\n[Step 4] Analyzing Talent...")
    talent_res = await pipeline.analyze_talent(context)
    print(f"✅ Talent Result: {talent_res}")
    
    # 5. Culture
    print("\n[Step 5] Analyzing Culture...")
    culture_res = await pipeline.analyze_culture(context)
    print(f"✅ Culture Result: {culture_res}")
    
    # 6. Finalize
    print("\n[Step 6] Calculating Final Score...")
    final_res = await pipeline.calculate_final_score(context, sec_res, board_res, talent_res, culture_res)
    print(f"✅ Final Result: {final_res}")
    
    print("\n🎉 Test Completed Successfully!")

if __name__ == "__main__":
    asyncio.run(test_pipeline())
