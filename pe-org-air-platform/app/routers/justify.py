"""
/justify router — Frontend-facing trigger for IC Meeting Package synthesis.

Exposes a single POST endpoint that orchestrates the full IC preparation
workflow: per-dimension evidence retrieval, score justification generation,
and executive memo synthesis.

The router shares the ``vector_store``, ``retriever``, and ``llm_router``
singletons that are already initialised in ``app/routers/rag.py``, avoiding
duplicate heavyweight initialisation.
"""
from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.models.rag import ICMeetingPackage, TaskType
from app.services.justification.generator import JustificationGenerator
from app.services.llm.router import ModelRouter
from app.services.retrieval.hybrid import HybridRetriever
from app.services.retrieval.hyde import HyDEGenerator
from app.services.search.vector_store import VectorStore
from app.services.workflows.ic_prep import ICPrepWorkflow

logger = structlog.get_logger()
router = APIRouter()

# ---------------------------------------------------------------------------
# Shared service singletons
# (Use the same persist dir as the existing RAG router for index parity)
# ---------------------------------------------------------------------------

CHROMA_PERSIST_DIR = "/opt/airflow/app_code/data/chroma"

_vector_store = VectorStore(persist_dir=CHROMA_PERSIST_DIR)
_llm_router = ModelRouter()
_hyde_gen = HyDEGenerator(llm_router=_llm_router)
_retriever = HybridRetriever(vector_store=_vector_store, hyde_generator=_hyde_gen)
_justification_gen = JustificationGenerator(llm_router=_llm_router)
_ic_workflow = ICPrepWorkflow(
    retriever=_retriever,
    justification_generator=_justification_gen,
    llm_router=_llm_router,
)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class JustifyRequest(BaseModel):
    """Request body for the /justify endpoint."""

    ticker: str = Field(
        ...,
        description="Company stock ticker (e.g. AAPL). Must be ingested first via /rag/ingest.",
        examples=["AAPL"],
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum evidence documents to retrieve per dimension.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "ticker": "AAPL",
                "top_k": 5,
            }
        }
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/justify",
    response_model=ICMeetingPackage,
    summary="Generate IC Meeting Package",
    tags=["RAG"],
)
async def generate_ic_package(request: JustifyRequest) -> ICMeetingPackage:
    """
    Produce a full Investment Committee Meeting Package for a target company.

    This endpoint orchestrates the complete IC preparation workflow:

    1. **Evidence retrieval** — for each of the 7 AI maturity dimensions,
       relevant evidence is retrieved from the indexed vector store using
       hybrid (dense + sparse) search.
    2. **Score justification** — each dimension receives a ~150-word
       PE-style investment memo paragraph with inline citations.
    3. **Executive synthesis** — a consolidated summary, key strengths,
       identified gaps, risk factors, and a Buy / Hold / Pass recommendation
       are generated.

    **Pre-requisite**: run ``POST /api/v1/rag/ingest?ticker=<TICKER>`` first
    to index the company's evidence into the vector store.

    Returns a fully populated ``ICMeetingPackage``.
    """
    try:
        package = await _ic_workflow.generate_meeting_package(
            ticker=request.ticker,
            top_k=request.top_k,
        )
        logger.info(
            "ic_package_generated",
            ticker=request.ticker,
            org_air_score=package.assessment.org_air_score,
        )
        return package

    except ValueError as exc:
        # No evidence found — caller needs to /ingest first
        raise HTTPException(status_code=400, detail=str(exc))

    except Exception as exc:
        logger.error(
            "ic_package_generation_failed",
            ticker=request.ticker,
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/justify/health",
    summary="Justify service health check",
    tags=["RAG"],
)
async def justify_health() -> dict:
    """Check readiness of the IC prep workflow services."""
    return {
        "status": "active",
        "services": {
            "llm_router": "ready",
            "vector_store": "ready",
            "retriever": "hybrid_active",
            "justification_generator": "ready",
            "ic_prep_workflow": "ready",
        },
    }
