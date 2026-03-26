"""
Mem0 semantic memory client for agent cross-session recall.

Each portfolio company gets its own memory namespace (keyed by company_id).
Agents write findings after each run and read prior context before starting,
so repeated assessments of the same company accumulate institutional memory.

Mem0 uses OpenAI embeddings under the hood — OPENAI_API_KEY must be set.
Falls back gracefully (empty results / silent writes) if Mem0 is unavailable,
so the rest of the workflow is never blocked by a memory failure.
"""
import asyncio
from functools import partial
from typing import List, Dict, Any

import structlog

logger = structlog.get_logger()

# Lazy singleton — instantiated on first use so import never fails
_mem0_instance = None


def _get_mem0():
    global _mem0_instance
    if _mem0_instance is None:
        from mem0 import Memory
        _mem0_instance = Memory()
    return _mem0_instance


async def _run_sync(fn, *args, **kwargs):
    """Run a synchronous Mem0 call in a thread pool to keep the event loop free."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(fn, *args, **kwargs))


async def add_memory(content: str, company_id: str, metadata: Dict[str, Any] = None) -> None:
    """
    Persist a finding to Mem0 under the company's memory namespace.

    content    — plain-text summary of what the agent found
    company_id — used as the Mem0 user_id / namespace
    metadata   — optional dict (agent name, assessment type, etc.)
    """
    try:
        mem = _get_mem0()
        messages = [{"role": "assistant", "content": content}]
        kwargs = {"user_id": company_id}
        if metadata:
            kwargs["metadata"] = metadata
        await _run_sync(mem.add, messages, **kwargs)
        logger.info("mem0_memory_added", company_id=company_id)
    except Exception as exc:
        logger.warning("mem0_add_failed", company_id=company_id, error=str(exc))


async def search_memory(query: str, company_id: str, limit: int = 5) -> List[str]:
    """
    Retrieve the most relevant prior memories for a company.

    Returns a list of plain-text memory strings (empty list on any failure).
    """
    try:
        mem = _get_mem0()
        results = await _run_sync(mem.search, query, user_id=company_id, limit=limit)
        # mem0 returns a list of dicts with a 'memory' key
        return [r["memory"] for r in results if isinstance(r, dict) and "memory" in r]
    except Exception as exc:
        logger.warning("mem0_search_failed", company_id=company_id, error=str(exc))
        return []


async def get_all_memories(company_id: str) -> List[str]:
    """Return every stored memory for a company (useful for audit / debugging)."""
    try:
        mem = _get_mem0()
        results = await _run_sync(mem.get_all, user_id=company_id)
        return [r["memory"] for r in results if isinstance(r, dict) and "memory" in r]
    except Exception as exc:
        logger.warning("mem0_get_all_failed", company_id=company_id, error=str(exc))
        return []
