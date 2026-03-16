"""
Tests for AnalystNotesCollector — Teammate B Task 3.

Mocks the VectorStore to avoid needing ChromaDB / embeddings at test time.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.collection.analyst_notes import (
    AnalystNotesCollector,
    NoteInput,
    NOTE_TYPE_TO_SOURCE,
)
from app.services.retrieval.dimension_mapper import DimensionMapper
from app.models.rag import SourceType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_vector_store():
    vs = MagicMock()
    vs.index_cs2_evidence = AsyncMock(return_value=1)
    vs.search = AsyncMock(return_value=[])
    return vs


@pytest.fixture
def collector(mock_vector_store):
    return AnalystNotesCollector(
        vector_store=mock_vector_store,
        dimension_mapper=DimensionMapper(),
    )


# ---------------------------------------------------------------------------
# ingest_note
# ---------------------------------------------------------------------------

class TestIngestNote:

    @pytest.mark.asyncio
    async def test_ingest_interview_note(self, collector, mock_vector_store):
        """Single interview note is indexed with correct source type."""
        note = NoteInput(
            title="CTO Interview",
            note_type="interview",
            content="Strong emphasis on LLM-based automation.",
        )
        evidence = await collector.ingest_note("NVDA", note)

        assert evidence.source_type == SourceType.ANALYST_INTERVIEW
        assert evidence.company_id == "NVDA"
        assert "CTO Interview" in evidence.content
        mock_vector_store.index_cs2_evidence.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ingest_data_room_note(self, collector, mock_vector_store):
        """Data-room note maps to DD_DATA_ROOM source type."""
        note = NoteInput(
            title="Annual Revenue Data",
            note_type="data_room",
            content="Revenue grew 30% YoY.",
        )
        evidence = await collector.ingest_note("JPM", note)

        assert evidence.source_type == SourceType.DD_DATA_ROOM
        assert evidence.company_id == "JPM"

    @pytest.mark.asyncio
    async def test_ingest_dd_finding_note(self, collector, mock_vector_store):
        """DD finding note maps to DD_FINDING."""
        note = NoteInput(
            title="Compliance Gap",
            note_type="dd_finding",
            content="Missing SOC-2 certification.",
        )
        evidence = await collector.ingest_note("GE", note)

        assert evidence.source_type == SourceType.DD_FINDING

    @pytest.mark.asyncio
    async def test_ingest_note_ticker_uppercased(self, collector, mock_vector_store):
        """Company ID should always be uppercase."""
        note = NoteInput(title="Test", note_type="interview", content="Test content.")
        evidence = await collector.ingest_note("nvda", note)

        assert evidence.company_id == "NVDA"

    @pytest.mark.asyncio
    async def test_ingest_note_has_high_confidence(self, collector, mock_vector_store):
        """Analyst notes get 0.9 confidence (manually provided = trusted)."""
        note = NoteInput(title="Test", note_type="interview", content="Testing content.")
        evidence = await collector.ingest_note("NVDA", note)

        assert evidence.confidence == 0.9


# ---------------------------------------------------------------------------
# ingest_batch
# ---------------------------------------------------------------------------

class TestIngestBatch:

    @pytest.mark.asyncio
    async def test_batch_ingest_multiple_notes(self, collector, mock_vector_store):
        """Batch ingest indexes all notes at once."""
        notes = [
            NoteInput(title="Note 1", note_type="interview", content="Content 1."),
            NoteInput(title="Note 2", note_type="data_room", content="Content 2."),
            NoteInput(title="Note 3", note_type="dd_finding", content="Content 3."),
        ]
        result = await collector.ingest_batch("NVDA", notes)

        assert len(result) == 3
        assert result[0].source_type == SourceType.ANALYST_INTERVIEW
        assert result[1].source_type == SourceType.DD_DATA_ROOM
        assert result[2].source_type == SourceType.DD_FINDING
        mock_vector_store.index_cs2_evidence.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_batch_ingest_empty_list(self, collector, mock_vector_store):
        """Empty batch returns empty list and does not call vector store."""
        result = await collector.ingest_batch("NVDA", [])

        assert result == []
        mock_vector_store.index_cs2_evidence.assert_not_awaited()


# ---------------------------------------------------------------------------
# list_notes
# ---------------------------------------------------------------------------

class TestListNotes:

    @pytest.mark.asyncio
    async def test_list_notes_filters_by_source_type(self, collector, mock_vector_store):
        """Only documents with analyst source types are returned."""
        # Mock search results — mix of analyst notes and SEC chunks
        mock_results = [
            MagicMock(
                doc_id="1",
                content="Interview content",
                score=0.95,
                metadata={"source_type": "analyst_interview", "company_id": "NVDA"},
            ),
            MagicMock(
                doc_id="2",
                content="SEC chunk",
                score=0.90,
                metadata={"source_type": "sec_filing", "company_id": "NVDA"},
            ),
            MagicMock(
                doc_id="3",
                content="Data room doc",
                score=0.85,
                metadata={"source_type": "dd_data_room", "company_id": "NVDA"},
            ),
        ]
        mock_vector_store.search.return_value = mock_results

        notes = await collector.list_notes("NVDA")

        # Should only return analyst_interview and dd_data_room
        assert len(notes) == 2
        assert notes[0]["metadata"]["source_type"] == "analyst_interview"
        assert notes[1]["metadata"]["source_type"] == "dd_data_room"


# ---------------------------------------------------------------------------
# NoteInput validation
# ---------------------------------------------------------------------------

class TestNoteInputValidation:

    def test_valid_note_input(self):
        """Basic valid NoteInput."""
        note = NoteInput(
            title="Test Note",
            note_type="interview",
            content="Some content.",
        )
        assert note.title == "Test Note"
        assert note.note_type == "interview"

    def test_note_type_mapping_completeness(self):
        """Every valid note_type has a corresponding SourceType."""
        for note_type in ["interview", "data_room", "dd_finding"]:
            assert note_type in NOTE_TYPE_TO_SOURCE
            assert isinstance(NOTE_TYPE_TO_SOURCE[note_type], SourceType)

    def test_note_input_optional_fields_default(self):
        """Optional fields default correctly."""
        note = NoteInput(title="T", note_type="interview", content="C.")
        assert note.analyst_name is None
        assert note.date is None
        assert note.tags == []
