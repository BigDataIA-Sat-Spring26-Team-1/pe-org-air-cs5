"""ChromaDB vector store with CS2 evidence metadata."""
import chromadb
from chromadb.config import Settings
import litellm
from typing import List, Dict, Any, Optional
import asyncio
import os
import structlog

from app.models.rag import CS2Evidence, SearchResult

logger = structlog.get_logger()

class VectorStore:
    """Vector store preserving CS2 evidence metadata."""

    def __init__(self, persist_dir: str = "./chroma_data"):
        # Ensure the directory exists
        if not os.path.exists(persist_dir):
            os.makedirs(persist_dir)
            
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Initialize the collection
        self.collection = self.client.get_or_create_collection(
            name="pe_evidence",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Use LiteLLM for remote embeddings (Faster build, less memory)
        self.embedding_model = "text-embedding-3-small"
        logger.info("vector_store_initialized", persist_dir=persist_dir, model=self.embedding_model)

    async def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings using LiteLLM."""
        try:
            response = await litellm.aembedding(
                model=self.embedding_model,
                input=texts
            )
            return [r["embedding"] for r in response["data"]]
        except Exception as e:
            logger.error("embedding_failed", error=str(e))
            raise e

    async def upsert_documents(self, documents: List[Dict[str, Any]]) -> int:
        """Generic upsert for documents (used by hybrid retriever)."""
        if not documents:
            return 0
            
        ids = [d["doc_id"] for d in documents]
        contents = [d["content"] for d in documents]
        metadatas = [d.get("metadata", {}) for d in documents]
        
        embeddings = await self._get_embeddings(contents)
        
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=metadatas
        )
        return len(ids)

    async def index_cs2_evidence(
        self, 
        evidence_list: List[CS2Evidence], 
        dimension_mapper: Any = None
    ) -> int:
        """
        Index CS2 evidence with dimension mapping.
        Preserves: source_type, signal_category, confidence, company_id, dimension.
        """
        if not evidence_list:
            return 0

        ids, contents, metadatas = [], [], []

        for e in evidence_list:
            # Determine mapping if dimension_mapper is provided
            primary_dim = "unknown"
            if dimension_mapper:
                try:
                    primary_dim = dimension_mapper.get_primary_dimension(
                        e.signal_category, 
                        e.source_type
                    ).value
                except Exception:
                    pass

            ids.append(e.evidence_id)
            contents.append(e.content)
            
            # Metadata schema follows evidence standards
            metadata = {
                "company_id": e.company_id,
                "source_type": e.source_type.value,
                "signal_category": e.signal_category.value,
                "dimension": primary_dim,
                "confidence": float(e.confidence),
                "fiscal_year": e.fiscal_year or 0,
                "source_url": e.source_url or ""
            }
            metadatas.append(metadata)

        # Generate embeddings using LiteLLM
        logger.info("generating_embeddings", count=len(contents))
        embeddings = await self._get_embeddings(contents)

        # Upsert in ChromaDB
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=metadatas
        )
        
        logger.info("evidence_indexed_successfully", count=len(ids))
        return len(ids)

    async def search(
        self, 
        query: str, 
        top_k: int = 10, 
        company_id: Optional[str] = None,
        dimension: Optional[str] = None,
        min_confidence: float = 0.0
    ) -> List[SearchResult]:
        """Search with metadata filters."""
        # Build ChromaDB 'where' clause with standard filters
        where_params = []
        
        if company_id:
            where_params.append({"company_id": company_id})
        if dimension:
            where_params.append({"dimension": dimension})
        if min_confidence > 0:
            where_params.append({"confidence": {"$gte": min_confidence}})

        # Simplified logic for combining multiple filters
        where_clause = None
        if len(where_params) == 1:
            where_clause = where_params[0]
        elif len(where_params) > 1:
            where_clause = {"$and": where_params}

        # Encode query using LiteLLM
        query_embeddings = await self._get_embeddings([query])
        query_embedding = query_embeddings[0]

        # Execute search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause
        )

        # Parse results into SearchResult models
        formatted_results = []
        if not results["ids"] or not results["ids"][0]:
            return []

        for i in range(len(results["ids"][0])):
            formatted_results.append(SearchResult(
                doc_id=results["ids"][0][i],
                content=results["documents"][0][i],
                score=1.0 - results["distances"][0][i], # Convert distance to similarity score
                metadata=results["metadatas"][0][i]
            ))

        return formatted_results
