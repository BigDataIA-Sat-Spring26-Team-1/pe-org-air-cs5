"""HyDE (Hypothetical Document Embeddings) generation service."""
import structlog
from typing import Any
from app.models.rag import TaskType

logger = structlog.get_logger()

class HyDEGenerator:
    """Generates hypothetical answers to expand scientific/equity queries."""

    def __init__(self, llm_router: Any):
        self.llm_router = llm_router

    async def generate_hypothetical_document(self, query: str) -> str:
        """
        Generate a fake 'ideal' document for the query.
        This improves zero-shot retrieval by matching vs 'answer-like' text.
        """
        system_prompt = (
            "You are a Private Equity Analyst. Given a user query, "
            "generate a short, hypothetical snippet of a company's SEC filing or "
            "news article that would perfectly answer this query. "
            "Do not include any introductory text, just the hypothetical fact-filled snippet."
        )
        
        try:
            response = await self.llm_router.complete(
                task=TaskType.CHAT_RESPONSE,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Query: {query}"}
                ]
            )
            hyde_doc = response.choices[0].message.content
            logger.info("hyde_doc_generated", original_query=query[:50])
            return f"{query} {hyde_doc}" # Expand query with the hypothetical doc
        except Exception as e:
            logger.warning("hyde_generation_failed", error=str(e))
            return query # Fallback to original query
