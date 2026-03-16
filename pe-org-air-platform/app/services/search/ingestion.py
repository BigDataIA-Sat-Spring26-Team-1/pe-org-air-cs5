"""Ingestion service for RAG evidence."""
import structlog
from typing import List, Optional
from app.services.snowflake import db
from app.services.search.vector_store import VectorStore
from app.models.rag import CS2Evidence, SourceType, SignalCategory
from app.services.retrieval.dimension_mapper import DimensionMapper
from datetime import datetime
import uuid

logger = structlog.get_logger()

class IngestionService:
    """Handles pulling data from Snowflake and indexing into Vector Store."""

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.dimension_mapper = DimensionMapper()

    async def ingest_company_data(self, ticker: str, limit: int = 200) -> List[CS2Evidence]:
        """
        Pull SEC and External Signal data for a company and index it.
        Returns the list of processed evidence for secondary indexing (sparse).
        """
        logger.info("starting_ingestion", ticker=ticker)
        
        # 1. Fetch Company for proper ID mapping
        company = await db.fetch_company_by_ticker(ticker.upper())
        if not company:
            logger.warning("company_not_found", ticker=ticker)
            return []
            
        company_id = company['id']

        # 2. Fetch SEC Chunks
        sec_chunks = await db.fetch_sec_chunks_by_company(company_id, limit=limit // 2)
        
        # 3. Fetch External Signals
        external_signals = await db.fetch_external_signals(company_id, limit=limit // 2)

        evidence_list: List[CS2Evidence] = []

        # Convert SEC results to CS2Evidence
        # Truncate to ~6000 tokens (≈24000 chars) to stay under the
        # text-embedding-3-small 8192-token context window limit.
        MAX_CHARS = 24_000
        for chunk in sec_chunks:
            content = (chunk.get('chunk_text') or "")[:MAX_CHARS]
            evidence_list.append(CS2Evidence(
                evidence_id=chunk.get('chunk_id') or str(uuid.uuid4()),
                company_id=ticker.upper(),
                source_type=SourceType.SEC_FILING,
                signal_category=SignalCategory.TECHNOLOGY_STACK,
                content=content,
                extracted_at=datetime.now(),
                confidence=1.0
            ))

        # Convert External Signals to CS2Evidence
        for sig in external_signals:
            # Map raw signal source to SourceType
            source_raw = str(sig.get('source', '')).lower()
            src_type = SourceType.SOURCE_NEWS
            if 'glassdoor' in source_raw: src_type = SourceType.GLASSDOOR
            elif 'patent' in source_raw: src_type = SourceType.PATENT
            elif 'job' in source_raw: src_type = SourceType.JOB_POSTING

            # Map category
            cat_raw = str(sig.get('category', '')).lower()
            cat = SignalCategory.GENERAL
            if 'talent' in cat_raw or 'hiring' in cat_raw: cat = SignalCategory.TALENT
            elif 'innovation' in cat_raw: cat = SignalCategory.INNOVATION
            elif 'leadership' in cat_raw: cat = SignalCategory.LEADERSHIP

            evidence_list.append(CS2Evidence(
                evidence_id=sig.get('id') or str(uuid.uuid4()),
                company_id=ticker.upper(),
                source_type=src_type,
                signal_category=cat,
                content=str(sig.get('raw_value', '')),
                extracted_at=datetime.now(),
                confidence=float(sig.get('confidence', 0.8))
            ))

        if not evidence_list:
            logger.info("no_evidence_found_for_ingestion", ticker=ticker)
            return []

        # 4. Index in Vector Store (Dense)
        await self.vector_store.index_cs2_evidence(evidence_list, dimension_mapper=self.dimension_mapper)
        logger.info("ingestion_completed", ticker=ticker, count=len(evidence_list))
        return evidence_list
