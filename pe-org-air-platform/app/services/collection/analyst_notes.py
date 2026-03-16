"""
Analyst Notes Collector — Teammate B Task 3.

Ingestion service for **manual** due-diligence data:
  * Interview transcripts
  * Site-visit notes
  * Data-room summaries

Notes are converted to ``CS2Evidence`` objects and indexed into
ChromaDB alongside SEC filings, making them searchable via the
existing RAG ``/query`` endpoint.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

import structlog
from pydantic import BaseModel, Field

from app.models.rag import CS2Evidence, SignalCategory, SourceType
from app.services.search.vector_store import VectorStore
from app.services.retrieval.dimension_mapper import DimensionMapper

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------

NOTE_TYPE_TO_SOURCE: Dict[str, SourceType] = {
    "interview":  SourceType.ANALYST_INTERVIEW,
    "data_room":  SourceType.DD_DATA_ROOM,
    "dd_finding": SourceType.DD_FINDING,
}


class NoteInput(BaseModel):
    """Schema for a single analyst note ingestion request."""

    title: str = Field(..., min_length=1, max_length=500, description="Brief title for the note")
    note_type: Literal["interview", "data_room", "dd_finding"] = Field(
        ...,
        description="Type of analyst note: interview transcript, data-room doc, or DD finding",
    )
    content: str = Field(..., min_length=1, description="Full text content of the note")
    analyst_name: Optional[str] = Field(None, description="Name of the analyst who wrote the note")
    date: Optional[str] = Field(None, description="ISO-format date (e.g. 2026-03-09)")
    tags: List[str] = Field(default_factory=list, description="Free-form tags for filtering")

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "CTO Interview — AI Strategy",
                "note_type": "interview",
                "content": "The CTO emphasized a strong push toward LLM-based automation...",
                "analyst_name": "J. Smith",
                "date": "2026-03-09",
                "tags": ["ai", "strategy", "leadership"],
            }
        }
    }


# ---------------------------------------------------------------------------
# Collector service
# ---------------------------------------------------------------------------

class AnalystNotesCollector:
    """
    Ingests analyst notes into the RAG vector store.

    Each note is wrapped as a ``CS2Evidence`` object, dimension-mapped
    via ``DimensionMapper``, and stored in ChromaDB.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        dimension_mapper: Optional[DimensionMapper] = None,
    ):
        self.vector_store = vector_store
        self.dimension_mapper = dimension_mapper or DimensionMapper()

    # -- Single note --------------------------------------------------------

    async def ingest_note(
        self,
        ticker: str,
        note: NoteInput,
    ) -> CS2Evidence:
        """
        Ingest a single analyst note.

        Returns the ``CS2Evidence`` object that was indexed.
        """
        source_type = NOTE_TYPE_TO_SOURCE.get(note.note_type)
        if source_type is None:
            raise ValueError(f"Unknown note_type: {note.note_type}")

        evidence = CS2Evidence(
            evidence_id=str(uuid4()),
            company_id=ticker.upper(),
            source_type=source_type,
            signal_category=SignalCategory.GENERAL,
            content=f"[{note.title}] {note.content}",
            extracted_at=datetime.now(),
            confidence=0.9,  # analyst-provided data is high-confidence
            fiscal_year=None,
            source_url=None,
        )

        # Index into ChromaDB with dimension mapping
        await self.vector_store.index_cs2_evidence(
            [evidence],
            dimension_mapper=self.dimension_mapper,
        )

        logger.info(
            "analyst_note_ingested",
            ticker=ticker,
            note_type=note.note_type,
            evidence_id=evidence.evidence_id,
        )
        return evidence

    # -- Batch ingest -------------------------------------------------------

    async def ingest_batch(
        self,
        ticker: str,
        notes: List[NoteInput],
    ) -> List[CS2Evidence]:
        """
        Ingest multiple analyst notes at once.

        Returns list of indexed ``CS2Evidence`` objects.
        """
        if not notes:
            return []

        evidence_list: List[CS2Evidence] = []
        for note in notes:
            source_type = NOTE_TYPE_TO_SOURCE.get(note.note_type)
            if source_type is None:
                raise ValueError(f"Unknown note_type: {note.note_type}")

            evidence_list.append(
                CS2Evidence(
                    evidence_id=str(uuid4()),
                    company_id=ticker.upper(),
                    source_type=source_type,
                    signal_category=SignalCategory.GENERAL,
                    content=f"[{note.title}] {note.content}",
                    extracted_at=datetime.now(),
                    confidence=0.9,
                    fiscal_year=None,
                    source_url=None,
                )
            )

        # Batch-index all at once
        await self.vector_store.index_cs2_evidence(
            evidence_list,
            dimension_mapper=self.dimension_mapper,
        )

        logger.info(
            "analyst_notes_batch_ingested",
            ticker=ticker,
            count=len(evidence_list),
        )
        return evidence_list

    # -- List notes ---------------------------------------------------------

    async def list_notes(self, ticker: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Return indexed analyst notes for a company.

        Queries ChromaDB metadata for documents where
        ``source_type`` is one of the analyst note types..
        """
        analyst_source_types = [st.value for st in NOTE_TYPE_TO_SOURCE.values()]
        results = await self.vector_store.search(
            query=f"analyst notes for {ticker}",
            top_k=limit,
            company_id=ticker.upper(),
        )
        # Filter to analyst-sourced documents only
        filtered = [
            {
                "doc_id": r.doc_id,
                "content": r.content,
                "score": r.score,
                "metadata": r.metadata,
            }
            for r in results
            if r.metadata.get("source_type") in analyst_source_types
        ]
        return filtered
