"""
Tests for app/services/memory/mem0_client.py — CS5 Mem0 Platform API integration.

Covers:
  - _extract_memories() normalisation (dict vs list response)
  - add_memory() success and graceful failure
  - search_memory() platform-API dict response and list response
  - search_memory() graceful failure (returns [])
  - get_all_memories() success and graceful failure
  - Singleton reset between tests
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── helpers ───────────────────────────────────────────────────────────────────
def _make_memory_item(text: str) -> dict:
    return {"id": "abc123", "memory": text, "score": 0.9}


def _reset_singleton():
    """Force the lazy singleton back to None so each test starts fresh."""
    import app.services.memory.mem0_client as mod
    mod._mem0_instance = None


# ═══════════════════════════════════════════════════════════════════════════════
# _extract_memories
# ═══════════════════════════════════════════════════════════════════════════════
class TestExtractMemories:
    def setup_method(self):
        _reset_singleton()

    def test_extracts_from_dict_with_results_key(self):
        from app.services.memory.mem0_client import _extract_memories
        raw = {"results": [_make_memory_item("AI governance is strong"), _make_memory_item("Score was 78")]}
        result = _extract_memories(raw)
        assert result == ["AI governance is strong", "Score was 78"]

    def test_extracts_from_plain_list(self):
        from app.services.memory.mem0_client import _extract_memories
        raw = [_make_memory_item("talent score 85"), _make_memory_item("data infra weak")]
        result = _extract_memories(raw)
        assert result == ["talent score 85", "data infra weak"]

    def test_skips_items_without_memory_key(self):
        from app.services.memory.mem0_client import _extract_memories
        raw = [{"id": "x"}, _make_memory_item("valid item"), {"memory": None}]
        result = _extract_memories(raw)
        assert result == ["valid item"]

    def test_returns_empty_list_for_empty_results(self):
        from app.services.memory.mem0_client import _extract_memories
        assert _extract_memories({"results": []}) == []
        assert _extract_memories([]) == []

    def test_handles_dict_with_empty_results_key(self):
        from app.services.memory.mem0_client import _extract_memories
        assert _extract_memories({"results": []}) == []

    def test_handles_non_dict_items_in_list(self):
        from app.services.memory.mem0_client import _extract_memories
        raw = ["string_item", None, _make_memory_item("ok")]
        result = _extract_memories(raw)
        assert result == ["ok"]


# ═══════════════════════════════════════════════════════════════════════════════
# add_memory
# ═══════════════════════════════════════════════════════════════════════════════
class TestAddMemory:
    def setup_method(self):
        _reset_singleton()

    async def test_add_memory_success(self):
        mock_client = MagicMock()
        mock_client.add = MagicMock(return_value={"id": "new_mem"})
        with patch("app.services.memory.mem0_client._get_mem0", return_value=mock_client):
            from app.services.memory.mem0_client import add_memory
            await add_memory("NVDA scored 78 on Org-AI-R", company_id="NVDA")
        mock_client.add.assert_called_once()
        call_kwargs = mock_client.add.call_args
        assert call_kwargs.kwargs.get("user_id") == "NVDA"

    async def test_add_memory_with_metadata(self):
        mock_client = MagicMock()
        mock_client.add = MagicMock(return_value={})
        with patch("app.services.memory.mem0_client._get_mem0", return_value=mock_client):
            from app.services.memory.mem0_client import add_memory
            await add_memory(
                "SEC analysis complete",
                company_id="AAPL",
                metadata={"agent": "sec_analyst", "assessment_type": "full"},
            )
        call_kwargs = mock_client.add.call_args.kwargs
        assert call_kwargs["metadata"]["agent"] == "sec_analyst"

    async def test_add_memory_graceful_failure(self):
        """mem0 failure must never raise — workflow must continue."""
        mock_client = MagicMock()
        mock_client.add = MagicMock(side_effect=Exception("Connection refused"))
        with patch("app.services.memory.mem0_client._get_mem0", return_value=mock_client):
            from app.services.memory.mem0_client import add_memory
            # should not raise
            await add_memory("some content", company_id="MSFT")

    async def test_add_memory_formats_message_correctly(self):
        """Messages list must be [{'role': 'assistant', 'content': ...}]."""
        mock_client = MagicMock()
        mock_client.add = MagicMock(return_value={})
        with patch("app.services.memory.mem0_client._get_mem0", return_value=mock_client):
            from app.services.memory.mem0_client import add_memory
            await add_memory("test content", company_id="TSLA")
        messages_arg = mock_client.add.call_args.args[0]
        assert messages_arg == [{"role": "assistant", "content": "test content"}]


# ═══════════════════════════════════════════════════════════════════════════════
# search_memory
# ═══════════════════════════════════════════════════════════════════════════════
class TestSearchMemory:
    def setup_method(self):
        _reset_singleton()

    async def test_search_returns_memories_from_dict_response(self):
        mock_client = MagicMock()
        mock_client.search = MagicMock(return_value={
            "results": [
                _make_memory_item("Prior Org-AI-R score: 78.5"),
                _make_memory_item("SEC analysis found 12 evidence items"),
            ]
        })
        with patch("app.services.memory.mem0_client._get_mem0", return_value=mock_client):
            from app.services.memory.mem0_client import search_memory
            result = await search_memory("Org-AI-R score", company_id="NVDA")
        assert len(result) == 2
        assert "Prior Org-AI-R score: 78.5" in result

    async def test_search_returns_memories_from_list_response(self):
        """Backward-compatible with local Memory API which returns a list directly."""
        mock_client = MagicMock()
        mock_client.search = MagicMock(return_value=[
            _make_memory_item("EBITDA impact 4.2%"),
        ])
        with patch("app.services.memory.mem0_client._get_mem0", return_value=mock_client):
            from app.services.memory.mem0_client import search_memory
            result = await search_memory("EBITDA", company_id="AAPL")
        assert result == ["EBITDA impact 4.2%"]

    async def test_search_passes_user_id_and_limit(self):
        mock_client = MagicMock()
        mock_client.search = MagicMock(return_value={"results": []})
        with patch("app.services.memory.mem0_client._get_mem0", return_value=mock_client):
            from app.services.memory.mem0_client import search_memory
            await search_memory("talent signals", company_id="GOOG", limit=3)
        mock_client.search.assert_called_once_with(
            "talent signals", user_id="GOOG", limit=3
        )

    async def test_search_graceful_failure_returns_empty_list(self):
        mock_client = MagicMock()
        mock_client.search = MagicMock(side_effect=RuntimeError("mem0 API timeout"))
        with patch("app.services.memory.mem0_client._get_mem0", return_value=mock_client):
            from app.services.memory.mem0_client import search_memory
            result = await search_memory("any query", company_id="MSFT")
        assert result == []

    async def test_search_returns_empty_for_no_results(self):
        mock_client = MagicMock()
        mock_client.search = MagicMock(return_value={"results": []})
        with patch("app.services.memory.mem0_client._get_mem0", return_value=mock_client):
            from app.services.memory.mem0_client import search_memory
            result = await search_memory("unknown company", company_id="XYZ")
        assert result == []

    async def test_search_default_limit_is_five(self):
        mock_client = MagicMock()
        mock_client.search = MagicMock(return_value={"results": []})
        with patch("app.services.memory.mem0_client._get_mem0", return_value=mock_client):
            from app.services.memory.mem0_client import search_memory
            await search_memory("query", company_id="NVDA")
        _, kwargs = mock_client.search.call_args
        assert kwargs["limit"] == 5


# ═══════════════════════════════════════════════════════════════════════════════
# get_all_memories
# ═══════════════════════════════════════════════════════════════════════════════
class TestGetAllMemories:
    def setup_method(self):
        _reset_singleton()

    async def test_get_all_returns_all_memories(self):
        mock_client = MagicMock()
        mock_client.get_all = MagicMock(return_value={
            "results": [
                _make_memory_item("First assessment"),
                _make_memory_item("Second assessment"),
                _make_memory_item("Third assessment"),
            ]
        })
        with patch("app.services.memory.mem0_client._get_mem0", return_value=mock_client):
            from app.services.memory.mem0_client import get_all_memories
            result = await get_all_memories("NVDA")
        assert len(result) == 3
        assert "First assessment" in result

    async def test_get_all_passes_user_id(self):
        mock_client = MagicMock()
        mock_client.get_all = MagicMock(return_value={"results": []})
        with patch("app.services.memory.mem0_client._get_mem0", return_value=mock_client):
            from app.services.memory.mem0_client import get_all_memories
            await get_all_memories("AAPL")
        mock_client.get_all.assert_called_once_with(user_id="AAPL")

    async def test_get_all_graceful_failure(self):
        mock_client = MagicMock()
        mock_client.get_all = MagicMock(side_effect=Exception("Network error"))
        with patch("app.services.memory.mem0_client._get_mem0", return_value=mock_client):
            from app.services.memory.mem0_client import get_all_memories
            result = await get_all_memories("TSLA")
        assert result == []


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton / _get_mem0
# ═══════════════════════════════════════════════════════════════════════════════
class TestSingleton:
    def setup_method(self):
        _reset_singleton()

    def test_singleton_is_created_with_api_key(self):
        """_get_mem0() instantiates MemoryClient with the env API key."""
        import app.services.memory.mem0_client as mod
        mock_client = MagicMock()
        mock_mem0_module = MagicMock()
        mock_mem0_module.MemoryClient = MagicMock(return_value=mock_client)
        with patch.dict("os.environ", {"MEM0_API_KEY": "test-key-123"}), \
             patch.dict("sys.modules", {"mem0": mock_mem0_module}):
            mod._mem0_instance = None
            result = mod._get_mem0()
        mock_mem0_module.MemoryClient.assert_called_once_with(api_key="test-key-123")
        assert result is mock_client

    def test_singleton_returns_same_instance_on_second_call(self):
        """Second call to _get_mem0() returns the cached instance without re-initialising."""
        import app.services.memory.mem0_client as mod
        mock_client = MagicMock()
        mock_mem0_module = MagicMock()
        mock_mem0_module.MemoryClient = MagicMock(return_value=mock_client)
        with patch.dict("sys.modules", {"mem0": mock_mem0_module}):
            mod._mem0_instance = None
            first = mod._get_mem0()
            second = mod._get_mem0()
        assert first is second
        assert mock_mem0_module.MemoryClient.call_count == 1
