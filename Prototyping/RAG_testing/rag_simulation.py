import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import litellm
from litellm import completion
import os
from typing import List, Dict, Any
from collections import defaultdict
from rank_bm25 import BM25Okapi
import pandas as pd
from snowflake_loader import fetch_evidence_from_snowflake

# SETUP
os.environ["LITELLM_LOG"] = "INFO"

class EnhancedSimulationRAG:
    def __init__(self, persist_dir="./chroma_db"):
        self.chroma_client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.chroma_client.get_or_create_collection(name="sim_evidence_v2")
        self.encoder = SentenceTransformer("all-MiniLM-L6-v2")
        self._bm25 = None
        self._corpus = []
        self._doc_ids = []
        self._metadata = []
        self.rrf_k = 60

    def index_data(self, df: pd.DataFrame):
        """Indexes data for both Dense and Sparse retrieval."""
        # Clear old data for a fresh run
        self._corpus, self._doc_ids, self._metadata = [], [], []
        
        ids = df['EVIDENCE_ID'].tolist()
        contents = df['CONTENT'].tolist()
        metadatas = [
            {
                "source": str(row['SOURCE_TYPE']), 
                "conf": float(row['CONFIDENCE']),
                "category": str(row['SIGNAL_CATEGORY'])
            } for _, row in df.iterrows()
        ]

        # 1. Dense Indexing (ChromaDB)
        embeddings = self.encoder.encode(contents).tolist()
        self.collection.add(ids=ids, embeddings=embeddings, documents=contents, metadatas=metadatas)

        # 2. Sparse Indexing (BM25)
        self._corpus = contents
        self._doc_ids = ids
        self._metadata = metadatas
        tokenized_corpus = [c.lower().split() for c in contents]
        self._bm25 = BM25Okapi(tokenized_corpus)
        print(f"Indexed {len(ids)} documents into hybrid store.")

    async def generate_hyde_query(self, query: str) -> str:
        """Task 8.1: HyDE Enhancement."""
        prompt = f"Generate a technical paragraph from an SEC filing or job post that answers this: {query}"
        try:
            # Multi-model fallback logic simulation
            response = completion(
                model="gpt-4o", 
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception:
            return query

    async def hybrid_search(self, query: str, k: int = 5) -> List[Dict]:
        """Task 8.1: Hybrid Retrieval with RRF Fusion."""
        # 1. Dense (Chroma)
        q_emb = self.encoder.encode([query]).tolist()
        dense_results = self.collection.query(query_embeddings=q_emb, n_results=k*2)
        
        # 2. Sparse (BM25)
        tokenized_query = query.lower().split()
        bm25_scores = self._bm25.get_scores(tokenized_query)
        top_sparse_idx = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:k*2]

        # 3. RRF Fusion Logic (PDF Page 21)
        scores = defaultdict(float)
        doc_map = {}

        for rank, did in enumerate(dense_results['ids'][0]):
            scores[did] += 0.6 / (self.rrf_k + rank + 1)
            doc_map[did] = {
                "id": did,
                "content": dense_results['documents'][0][rank],
                "metadata": dense_results['metadatas'][0][rank],
                "method": "dense"
            }

        for rank, idx in enumerate(top_sparse_idx):
            did = self._doc_ids[idx]
            scores[did] += 0.4 / (self.rrf_k + rank + 1)
            if did not in doc_map:
                doc_map[did] = {
                    "id": did,
                    "content": self._corpus[idx],
                    "metadata": self._metadata[idx],
                    "method": "sparse"
                }

        # Sort and return top k
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:k]
        return [doc_map[did] for did in sorted_ids]

    def generate_justification(self, query: str, context: List[Dict]):
        """Task 8.0b: Score Justification Generator."""
        evidence_text = ""
        for i, c in enumerate(context):
            evidence_text += f"\n[{i+1}] Source: {c['metadata']['source']} (Conf: {c['metadata']['conf']})\nContent: {c['content']}\n"
        
        prompt = f"""
        You are a PE AI Investment Analyst.
        Query: {query}
        
        EVIDENCE TRIALS:
        {evidence_text}
        
        Task: Write a justification memo (150-200 words).
        1. State why the evidence supports AI readiness.
        2. Cite specific sources using [Source Name].
        3. Identify GAPS (what is missing for a 'perfect' score).
        4. Assess evidence strength (Strong/Moderate/Weak).
        
        Format as a professional investment memo.
        """
        
        # Test fallback: Try gpt-4o, if fails, use a secondary model
        models = ["gpt-4o", "gpt-4o-mini"]
        for model in models:
            try:
                response = completion(model=model, messages=[{"role": "user", "content": prompt}], temperature=0.2)
                return response.choices[0].message.content
            except Exception as e:
                print(f"Model {model} failed, trying fallback...")
                continue
        return "Critical Error: All models failed."

async def run_enhanced_simulation():
    companies_to_test = [
        {"ticker": "NVDA", "query": "What is NVIDIA's competitive advantage in AI training hardware?"}
    ]
    
    sim = EnhancedSimulationRAG()
    
    for company in companies_to_test:
        print(f"\nENHANCED RUN: {company['ticker']}")
        df = fetch_evidence_from_snowflake(company['ticker'])
        if df.empty: continue

        sim.index_data(df)
        
        print("--- Step 1: HyDE Enhancement ---")
        hypo_query = await sim.generate_hyde_query(company['query'])
        print(f"Hypothetical Document Generated: {hypo_query[:100]}...")

        print("--- Step 2: Hybrid RRF Search ---")
        results = await sim.hybrid_search(hypo_query, k=5)
        
        print("--- Step 3: Peer-Reviewed Justification ---")
        memo = sim.generate_justification(company['query'], results)
        print("\nPE MEMO V2 (HYBRID + HYDE):\n")
        print(memo)

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_enhanced_simulation())
