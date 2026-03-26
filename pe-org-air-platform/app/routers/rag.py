from datetime import datetime
import asyncio
import httpx
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel, Field
import structlog

from app.models.enums import Dimension
from app.services.integration.cs1_client import CS1Client
from app.services.integration.cs2_client import CS2Client
from app.services.integration.cs3_client import CS3Client
from app.services.justification.generator import JustificationGenerator

from app.models.rag import TaskType, RetrievedDocument
from app.services.llm.router import ModelRouter
from app.services.search.vector_store import VectorStore
from app.services.search.ingestion import IngestionService
from app.services.retrieval.hybrid import HybridRetriever
from app.services.retrieval.hyde import HyDEGenerator
from app.services.collection.analyst_notes import AnalystNotesCollector, NoteInput
from app.services.retrieval.dimension_mapper import DimensionMapper

logger = structlog.get_logger()
router = APIRouter()

# Initialize services
# Using the mounted shared data volume for persistence
CHROMA_PERSIST_DIR = "/opt/airflow/app_code/data/chroma"
vector_store = VectorStore(persist_dir=CHROMA_PERSIST_DIR)
ingestion_service = IngestionService(vector_store=vector_store)
llm_router = ModelRouter()
hyde_gen = HyDEGenerator(llm_router=llm_router)
retriever = HybridRetriever(vector_store=vector_store, hyde_generator=hyde_gen)
dimension_mapper = DimensionMapper()
notes_collector = AnalystNotesCollector(vector_store=vector_store, dimension_mapper=dimension_mapper)

class RagQueryRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10, description="Company stock ticker")
    query: str = Field(..., min_length=3, description="RAG search query")
    use_hyde: bool = True
    top_k: int = Field(5, ge=1, le=20)
    dimension: Optional[str] = None
    min_confidence: float = Field(0.0, ge=0.0, le=1.0)

class RagQueryResponse(BaseModel):
    ticker: str
    query: str
    answer: str
    evidence: List[RetrievedDocument]

@router.post("/ingest", tags=["RAG"])
async def ingest_company(ticker: str = Query(..., min_length=1, description="Ticker to pull from Snowflake")):
    """
    Experimental: Pull data from Snowflake for a specific ticker and index it into the local Vector DB.
    Required before running /query for new companies.
    """
    evidence_list = await ingestion_service.ingest_company_data(ticker)
    if not evidence_list:
        raise HTTPException(status_code=404, detail=f"No real evidence found in Snowflake for {ticker}")
    
    # Update the sparse index (BM25) immediately
    # We must format the evidence correctly for the retriever
    retriever_formatted = []
    for e in evidence_list:
        primary_dim = dimension_mapper.get_primary_dimension(e.signal_category, e.source_type)
        retriever_formatted.append({
            "doc_id": e.evidence_id,
            "content": e.content,
            "metadata": {
                "company_id": e.company_id,
                "source_type": e.source_type.value,
                "signal_category": e.signal_category.value,
                "dimension": primary_dim.value,
                "confidence": e.confidence
            }
        })
    
    await retriever.index_documents(retriever_formatted)
    
    return {
        "status": "success", 
        "indexed_documents": len(evidence_list), 
        "ticker": ticker.upper(),
        "storage": "persistent_volume"
    }

@router.post("/query", response_model=RagQueryResponse, tags=["RAG"])
async def query_rag(request: RagQueryRequest):
    """
    Perform a RAG query for a specific company ticker.
    Make sure to run /ingest?ticker=XYZ first to load data.
    """
    try:
        # 1. Retrieve Evidence
        filter_meta = {
            "company_id": request.ticker.upper(),
            "dimension": request.dimension,
            "min_confidence": request.min_confidence
        }
        evidence = await retriever.retrieve(
            query=request.query,
            k=request.top_k,
            filter_metadata=filter_meta,
            use_hyde=request.use_hyde
        )

        if not evidence:
            raise HTTPException(
                status_code=400, 
                detail=f"No indexed data found for {request.ticker}. Please run /ingest first."
            )

        # 2. Generate Answer using LLM Router
        evidence_text = "\n".join([f"[{i+1}] {d.content}" for i, d in enumerate(evidence)])
        
        system_prompt = "You are a Private Equity AI Analyst. Answer the user's query based ONLY on the provided evidence. Cite sources using [N]."
        user_prompt = f"Query: {request.query}\n\nEvidence:\n{evidence_text}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        llm_response = await llm_router.complete(
            task=TaskType.CHAT_RESPONSE,
            messages=messages
        )

        answer = llm_response.choices[0].message.content

        return RagQueryResponse(
            ticker=request.ticker,
            query=request.query,
            answer=answer,
            evidence=evidence
        )

    except Exception as e:
        logger.error("rag_query_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def rag_health():
    """Check status of RAG infra."""
    return {
        "status": "active",
        "services": {
            "llm_router": "ready",
            "vector_store": "ready",
            "retriever": "hybrid_active",
            "notes_collector": "ready"
        }
    }


# ---------------------------------------------------------------------------
# Analyst Notes endpoints
# ---------------------------------------------------------------------------

class NotesIngestRequest(BaseModel):
    ticker: str
    note: NoteInput

class NotesBatchRequest(BaseModel):
    ticker: str
    notes: List[NoteInput]

@router.post("/notes/ingest", tags=["RAG"])
async def ingest_analyst_note(request: NotesIngestRequest):
    """
    Ingest a single analyst note (interview transcript, data-room doc, or DD finding)
    into the RAG vector store for a given company ticker.
    """
    try:
        evidence = await notes_collector.ingest_note(
            ticker=request.ticker,
            note=request.note,
        )
        return {
            "status": "success",
            "ticker": request.ticker.upper(),
            "indexed_documents": 1,
            "evidence_id": evidence.evidence_id,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("notes_ingest_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notes/batch", tags=["RAG"])
async def ingest_analyst_notes_batch(request: NotesBatchRequest):
    """
    Batch-ingest multiple analyst notes for a company.
    """
    try:
        evidence_list = await notes_collector.ingest_batch(
            ticker=request.ticker,
            notes=request.notes,
        )
        return {
            "status": "success",
            "ticker": request.ticker.upper(),
            "indexed_documents": len(evidence_list),
            "evidence_ids": [e.evidence_id for e in evidence_list],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("notes_batch_ingest_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notes/{ticker}", tags=["RAG"])
async def list_analyst_notes(
    ticker: str,
    limit: int = Query(50, ge=1, le=200),
):
    """
    List all analyst notes indexed for a specific company ticker.
    """
    try:
        notes = await notes_collector.list_notes(ticker=ticker, limit=limit)
        return {
            "ticker": ticker.upper(),
            "count": len(notes),
            "notes": notes,
        }
    except Exception as e:
        logger.error("notes_list_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/index-airflow", tags=["RAG"])
async def trigger_evidence_indexing_dag():
    """
    Trigger the Airflow evidence_indexing DAG to sync new CS2 evidence into RAG.
    """
    airflow_url = "http://airflow-webserver:8080/api/v1/dags/pe_evidence_indexing/dagRuns"
    auth = ("airflow", "airflow")
    
    async with httpx.AsyncClient() as client:
        try:
            run_id = f"manual_api_trigger_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            payload = {"dag_run_id": run_id}
            res = await client.post(airflow_url, json=payload, auth=auth, timeout=10.0)
            
            if res.status_code in [200, 201]:
                return {"status": "success", "dag_run_id": run_id}
            else:
                raise HTTPException(status_code=res.status_code, detail=f"Airflow error: {res.text}")
        except Exception as e:
            logger.error("airflow_trigger_failed", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))

@router.post("/complete-pipeline", tags=["RAG"])
async def run_complete_analysis_pipeline(
    ticker: str = Query(..., description="Ticker to analyze (e.g. NVDA)"),
    dimension: Dimension = Query(Dimension.DATA_INFRASTRUCTURE, description="Dimension to justify")
):
    """
    Run the end-to-end RAG analysis pipeline: CS1 Meta -> CS3 Score -> CS2 Evidence -> Justification.
    Matches the 'Complete Pipeline' exercise requirement.
    """
    cs1 = CS1Client()
    cs2 = CS2Client()
    cs3 = CS3Client()
    
    try:
        # 1. Company Meta
        company_data = await cs1.get_company(ticker)
        
        # 2. CS3 Score
        score_obj = await cs3.get_dimension_score(ticker, dimension)
        
        # 3. CS2 Evidence (for indexing context)
        # Note: We assume /ingest was run or we run it now
        evidence_list = await ingestion_service.ingest_company_data(ticker)
        logger.info("ingestion_completed_for_pipeline", ticker=ticker, count=len(evidence_list))

        # 4. Retrieve specifically for the dimension to justify
        evidence = await retriever.retrieve(
            query=f"AI maturity in {dimension.value}",
            k=5,
            filter_metadata={"company_id": ticker.upper(), "dimension": dimension.value}
        )

        # 5. Generate Justification
        generator = JustificationGenerator(llm_router=llm_router)
        justification = await generator.generate(
            company_id=ticker,
            dimension=dimension,
            score=score_obj.score,
            evidence=evidence
        )
        
        return {
            "ticker": ticker.upper(),
            "dimension": dimension.value,
            "company_name": company_data.get("name"),
            "score": justification.score,
            "level": justification.level_name,
            "summary": justification.generated_summary,
            "citations": [e.content[:100] + "..." for e in justification.supporting_evidence],
            "gaps": justification.gaps_identified
        }
    except Exception as e:
        logger.error("complete_pipeline_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        pass
