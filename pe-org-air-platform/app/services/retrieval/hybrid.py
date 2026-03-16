"""Hybrid retrieval with RRF fusion (Dense + Sparse)."""
from typing import List, Dict, Any, Optional
from collections import defaultdict
from rank_bm25 import BM25Okapi
import structlog

from app.models.rag import RetrievedDocument
from app.services.search.vector_store import VectorStore

logger = structlog.get_logger()

class HybridRetriever:
    """Hybrid retrieval combining dense (ChromaDB) and sparse (BM25) search."""

    def __init__(
        self, 
        vector_store: VectorStore,
        hyde_generator: Any = None,
        dense_weight: float = 0.6, 
        sparse_weight: float = 0.4, 
        rrf_k: int = 60
    ):
        self.vector_store = vector_store
        self.hyde_generator = hyde_generator
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.rrf_k = rrf_k
        
        # State for BM25
        self._bm25 = None
        self._corpus = []
        self._doc_ids = []
        self._metadata = []
        
    async def index_documents(self, documents: List[Dict[str, Any]]) -> int:
        """
        Index documents for BOTH sparse (BM25) and dense (ChromaDB) retrieval.
        """
        if not documents:
            return 0
            
        # 1. Sparse Indexing
        new_contents = [d["content"] for d in documents]
        new_ids = [d["doc_id"] for d in documents]
        new_metadatas = [d.get("metadata", {}) for d in documents]
        
        self._corpus.extend(new_contents)
        self._doc_ids.extend(new_ids)
        self._metadata.extend(new_metadatas)
        
        tokenized_corpus = [c.lower().split() for c in self._corpus]
        self._bm25 = BM25Okapi(tokenized_corpus)
        
        # 2. Dense Indexing (Task 6.1 verified)
        await self.vector_store.upsert_documents(documents)
        
        logger.info("hybrid_index_updated", count=len(documents))
        return len(documents)

    async def retrieve(
        self, 
        query: str, 
        k: int = 10, 
        filter_metadata: Optional[Dict] = None,
        use_hyde: bool = True
    ) -> List[RetrievedDocument]:
        """Execute hybrid search using RRF Fusion with optional HyDE enhancement."""
        search_query = query
        
        # 1. Option HyDE Enhancement (Task 8.1)
        if use_hyde and hasattr(self, 'hyde_generator') and self.hyde_generator:
            search_query = await self.hyde_generator.generate_hypothetical_document(query)
            logger.info("hyde_enhanced_query_used", original=query[:50])

        # Increase internal k for better fusion candidates
        n = k * 3 
        
        # 2. Dense retrieval
        raw_dense = await self.vector_store.search(
            query=search_query, 
            top_k=n, 
            company_id=filter_metadata.get("company_id") if filter_metadata else None,
            dimension=filter_metadata.get("dimension") if filter_metadata else None,
            min_confidence=filter_metadata.get("min_confidence", 0.0) if filter_metadata else 0.0
        )
        
        dense_results = [
            RetrievedDocument(
                doc_id=d.doc_id,
                content=d.content,
                metadata=d.metadata,
                score=d.score,
                retrieval_method="dense"
            ) for d in raw_dense
        ]

        # 2. Sparse retrieval (BM25)
        sparse_results = []
        if self._bm25:
            tokenized_query = query.lower().split()
            bm25_scores = self._bm25.get_scores(tokenized_query)
            
            # Rank and pick top n
            top_indices = sorted(
                range(len(bm25_scores)), 
                key=lambda i: bm25_scores[i], 
                reverse=True
            )[:n]
            
            for i in top_indices:
                # Basic metadata filtering for BM25
                skip = False
                if filter_metadata:
                    for key, val in filter_metadata.items():
                        if val is None: continue
                        
                        # Special case for confidence
                        if key == "min_confidence":
                            if float(self._metadata[i].get("confidence", 0)) < float(val):
                                skip = True
                                break
                            continue

                        if self._metadata[i].get(key) != val:
                            skip = True
                            break
                if skip: continue

                sparse_results.append(RetrievedDocument(
                    doc_id=self._doc_ids[i],
                    content=self._corpus[i],
                    metadata=self._metadata[i],
                    score=float(bm25_scores[i]),
                    retrieval_method="sparse"
                ))

        # 4. RRF Fusion
        # PDF Page 21: Combine using Reciprocal Rank Fusion
        # Re-rank based on weighted rank sum
        return self._rrf_fusion(dense_results, sparse_results, k)

    def _rrf_fusion(
        self, 
        dense: List[RetrievedDocument], 
        sparse: List[RetrievedDocument], 
        k: int
    ) -> List[RetrievedDocument]:
        """Rank fusion algorithm as per CS4 PDF Page 21."""
        scores = defaultdict(float)
        doc_map = {}

        # Fuse Dense
        for rank, doc in enumerate(dense):
            scores[doc.doc_id] += self.dense_weight / (self.rrf_k + rank + 1)
            doc_map[doc.doc_id] = doc

        # Fuse Sparse
        for rank, doc in enumerate(sparse):
            scores[doc.doc_id] += self.sparse_weight / (self.rrf_k + rank + 1)
            if doc.doc_id not in doc_map:
                doc_map[doc.doc_id] = doc

        # Sort by fused score
        sorted_ids = sorted(
            scores.keys(), 
            key=lambda did: scores[did], 
            reverse=True
        )[:k]

        final_results = []
        for did in sorted_ids:
            doc = doc_map[did]
            # Create a new document with the fused score
            doc_data = doc.model_dump()
            doc_data["score"] = scores[did]
            doc_data["retrieval_method"] = "hybrid"
            final_results.append(RetrievedDocument(**doc_data))

        logger.info("hybrid_search_completed", candidates=len(doc_map), top_k=len(final_results))
        return final_results
