"""
Unit and Integration tests for the RAG & Search system (Case Study 4).
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.retrieval.hybrid import HybridRetriever
from app.services.llm.router import ModelRouter, TaskType
from app.models.rag import RetrievedDocument, Dimension

@pytest.mark.asyncio
async def test_hybrid_retriever_fusion_logic():
    """Unit test for RRF ranking logic in HybridRetriever."""
    mock_vs = MagicMock()
    retriever = HybridRetriever(vector_store=mock_vs, dense_weight=1.0, sparse_weight=1.0, rrf_k=1)
    
    # Mock dense results (Rank 1: doc_a, Rank 2: doc_b)
    dense = [
        RetrievedDocument(doc_id="doc_a", content="A", metadata={}, score=0.9, retrieval_method="dense"),
        RetrievedDocument(doc_id="doc_b", content="B", metadata={}, score=0.8, retrieval_method="dense"),
    ]
    
    # Mock sparse results (Rank 1: doc_b, Rank 2: doc_a)
    sparse = [
        RetrievedDocument(doc_id="doc_b", content="B", metadata={}, score=10.0, retrieval_method="sparse"),
        RetrievedDocument(doc_id="doc_a", content="A", metadata={}, score=5.0, retrieval_method="sparse"),
    ]
    
    # With rrf_k=1:
    # doc_a: 1.0/(1+1) + 1.0/(1+2) = 0.5 + 0.33 = 0.833
    # doc_b: 1.0/(1+2) + 1.0/(1+1) = 0.33 + 0.5 = 0.833
    # They should have roughly equal scores if weights are identical and ranks are swapped.
    
    results = retriever._rrf_fusion(dense, sparse, k=2)
    assert len(results) == 2
    assert results[0].retrieval_method == "hybrid"
    assert results[0].score == pytest.approx(0.833, rel=1e-2)

@pytest.mark.asyncio
async def test_llm_router_fallback_mechanism():
    """Unit test for LiteLLM router fallback logic."""
    router = ModelRouter()
    
    mock_complete = AsyncMock()
    # First call fails, second succeeds
    mock_complete.side_effect = [Exception("Primary Failed"), MagicMock(choices=[MagicMock(message=MagicMock(content="Fallback Work"))])]
    
    with patch("app.services.llm.router.acompletion", mock_complete):
        res = await router.complete(TaskType.CHAT_RESPONSE, [{"role": "user", "content": "hi"}])
        assert res.choices[0].message.content == "Fallback Work"
        assert mock_complete.call_count == 2

@pytest.mark.asyncio
async def test_rag_ingest_endpoint(client):
    """Integration test for company ingestion endpoint."""
    with patch("app.services.search.ingestion.IngestionService.ingest_company_data") as mock_ingest:
        mock_ingest.return_value = [
            MagicMock(evidence_id="1", content="test", company_id="AAPL", source_type=MagicMock(value="sec"), signal_category=MagicMock(value="tech"))
        ]
        
        response = await client.post("/api/v1/rag/ingest?ticker=AAPL")
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["indexed_documents"] == 1

@pytest.mark.asyncio
async def test_rag_query_with_filters(client):
    """Integration test for RAG query with dimension filters."""
    mock_results = [
        RetrievedDocument(doc_id="1", content="Evidence 1", metadata={"company_id": "NVDA", "dimension": "data_infrastructure"}, score=0.9, retrieval_method="hybrid")
    ]
    
    with patch("app.services.retrieval.hybrid.HybridRetriever.retrieve", AsyncMock(return_value=mock_results)):
        with patch("app.services.llm.router.ModelRouter.complete", AsyncMock(return_value=MagicMock(choices=[MagicMock(message=MagicMock(content="Answer based on evidence"))]))):
            
            payload = {
                "ticker": "NVDA",
                "query": "Is there cloud infra?",
                "dimension": "data_infrastructure",
                "min_confidence": 0.5
            }
            response = await client.post("/api/v1/rag/query", json=payload)
            assert response.status_code == 200
            assert "Answer" in response.json()["answer"]
            assert len(response.json()["evidence"]) == 1
            assert response.json()["evidence"][0]["metadata"]["dimension"] == "data_infrastructure"

@pytest.mark.asyncio
async def test_justify_endpoint_integration(client):
    """Integration test for the /justify executive summary flow."""
    mock_pkg = MagicMock()
    mock_pkg.assessment.org_air_score = 75.0
    mock_pkg.model_dump.return_value = {"ticker": "AAPL", "recommendation": "Buy"}
    
    with patch("app.routers.justify._ic_workflow.generate_meeting_package", AsyncMock(return_value=mock_pkg)):
        response = await client.post("/api/v1/rag/justify", json={"ticker": "AAPL", "top_k": 3})
        assert response.status_code == 200
        # Check that it returns the package (partial check since it's a mock)
        assert "recommendation" in response.json()
