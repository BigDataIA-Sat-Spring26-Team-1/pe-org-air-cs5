"""
Tests for CS5 LangGraph agent workflow.

Covers:
  - supervisor_node routing (all 7 branches)
  - sec_analyst_node — evidence fetch + mem0 search/add
  - scorer_node — HITL trigger conditions
  - evidence_node — justifications for 3 dimensions
  - value_creator_node — gap analysis + HITL on high EBITDA
  - hitl_approval_node — auto-approve
  - complete_node — timestamp + message
  - Full quick/full workflow integration (mocked MCP + mem0)

Note: langgraph and langchain are only available inside Docker.
      This file is auto-skipped locally and fully executed inside the container.

Patching strategy
-----------------
supervisor.py imports from ``agents.specialists`` (PYTHONPATH: /opt/airflow/app),
while this test file imports ``app.agents.specialists`` (PYTHONPATH: /opt/airflow).
Both resolve to the same .py file but Python loads them as two *separate* module
objects — so patching a name in one module's __dict__ has no effect on the other.

Resolution: instead of replacing module-level tool names, we patch
``mcp_client.call_tool`` **on the instance** that the agent methods actually
call through.  mem0_client patches continue to work because both module copies
import the same object from app.services.memory (shared reference).
"""
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# Skip entire module if langgraph is not installed (local Poetry env)
pytest.importorskip("langgraph", reason="langgraph not installed locally — run inside Docker")
pytest.importorskip("langchain_openai", reason="langchain_openai not installed locally")

# Import BOTH module aliases so we hold references to the right objects.
# app.agents.supervisor triggers loading of agents.specialists (the one actually
# used by supervisor.py), so agents.specialists is already in sys.modules here.
import app.agents.specialists   # noqa: E402
import app.agents.supervisor    # noqa: E402
import agents.specialists as _specs  # noqa: E402  — the module supervisor.py imported from


# ── helpers ───────────────────────────────────────────────────────────────────
def _mcp_mock(**responses) -> AsyncMock:
    """
    Return an AsyncMock for mcp_client.call_tool that dispatches by tool name.

    Keyword args map MCP tool names to return values (dicts are JSON-encoded).
    Unrecognised tool names return "{}".

    MCP tool names used by specialists.py:
      calculate_org_air_score  get_company_evidence
      generate_justification   run_gap_analysis
    """
    async def _dispatch(tool_name: str, args: dict) -> str:
        if tool_name in responses:
            val = responses[tool_name]
            return val if isinstance(val, str) else json.dumps(val)
        return "{}"
    return AsyncMock(side_effect=_dispatch)


# ── state builder ─────────────────────────────────────────────────────────────
def _base_state(**overrides) -> dict:
    state = {
        "company_id": "NVDA",
        "assessment_type": "full",
        "requested_by": "analyst",
        "messages": [],
        "sec_analysis": None,
        "talent_analysis": None,
        "scoring_result": None,
        "evidence_justifications": None,
        "value_creation_plan": None,
        "next_agent": None,
        "requires_approval": False,
        "approval_reason": None,
        "approval_status": None,
        "approved_by": None,
        "started_at": datetime.now(timezone.utc),
        "completed_at": None,
        "total_tokens": 0,
        "error": None,
    }
    state.update(overrides)
    return state


def _score_data(org_air: float = 78.5) -> dict:
    return {"company_id": "NVDA", "org_air": org_air, "vr_score": 82.0, "hr_score": 75.0}


def _gap_data(ebitda_pct: float = 3.8) -> dict:
    return {
        "company_id": "NVDA",
        "current_score": 78.5,
        "target_score": 85.0,
        "projected_ebitda_pct": ebitda_pct,
        "gaps": [{"dimension": "ai_governance", "gap": 3.0}, {"dimension": "culture", "gap": 2.5}],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# supervisor_node routing
# ═══════════════════════════════════════════════════════════════════════════════
class TestSupervisorNode:
    async def test_routes_to_sec_analyst_when_no_sec_analysis(self):
        from app.agents.supervisor import supervisor_node
        result = await supervisor_node(_base_state())
        assert result["next_agent"] == "sec_analyst"

    async def test_routes_to_scorer_after_sec_analysis(self):
        from app.agents.supervisor import supervisor_node
        result = await supervisor_node(_base_state(sec_analysis={"findings": []}))
        assert result["next_agent"] == "scorer"

    async def test_routes_to_evidence_after_scoring(self):
        from app.agents.supervisor import supervisor_node
        result = await supervisor_node(
            _base_state(sec_analysis={"findings": []}, scoring_result=_score_data())
        )
        assert result["next_agent"] == "evidence_agent"

    async def test_routes_to_value_creator_for_full_mode(self):
        from app.agents.supervisor import supervisor_node
        result = await supervisor_node(_base_state(
            sec_analysis={"findings": []},
            scoring_result=_score_data(),
            evidence_justifications={"justifications": {}},
            assessment_type="full",
        ))
        assert result["next_agent"] == "value_creator"

    async def test_skips_value_creator_for_quick_mode(self):
        from app.agents.supervisor import supervisor_node
        result = await supervisor_node(_base_state(
            sec_analysis={"findings": []},
            scoring_result=_score_data(),
            evidence_justifications={"justifications": {}},
            assessment_type="quick",
        ))
        assert result["next_agent"] == "complete"

    async def test_routes_to_hitl_when_approval_pending(self):
        from app.agents.supervisor import supervisor_node
        result = await supervisor_node(_base_state(requires_approval=True, approval_status="pending"))
        assert result["next_agent"] == "hitl_approval"

    async def test_routes_to_complete_when_all_done(self):
        from app.agents.supervisor import supervisor_node
        result = await supervisor_node(_base_state(
            sec_analysis={"findings": []},
            scoring_result=_score_data(),
            evidence_justifications={"justifications": {}},
            value_creation_plan={"gap_analysis": {}},
        ))
        assert result["next_agent"] == "complete"


# ═══════════════════════════════════════════════════════════════════════════════
# sec_analyst_node
# ═══════════════════════════════════════════════════════════════════════════════
class TestSECAnalystNode:
    async def test_returns_sec_analysis_with_findings(self):
        evidence = [{"dimension": "talent", "content": "Strong hiring data"}]
        with patch.object(_specs.mcp_client, "call_tool",
                          _mcp_mock(get_company_evidence=evidence)), \
             patch.object(_specs.mem0_client, "search_memory",
                          new_callable=AsyncMock, return_value=[]), \
             patch.object(_specs.mem0_client, "add_memory",
                          new_callable=AsyncMock):
            from app.agents.supervisor import sec_analyst_node
            result = await sec_analyst_node(_base_state())
        assert result["sec_analysis"]["company_id"] == "NVDA"
        assert len(result["sec_analysis"]["findings"]) == 1

    async def test_appends_message_with_agent_name(self):
        with patch.object(_specs.mcp_client, "call_tool",
                          _mcp_mock(get_company_evidence=[])), \
             patch.object(_specs.mem0_client, "search_memory",
                          new_callable=AsyncMock, return_value=[]), \
             patch.object(_specs.mem0_client, "add_memory",
                          new_callable=AsyncMock):
            from app.agents.supervisor import sec_analyst_node
            result = await sec_analyst_node(_base_state())
        assert result["messages"][0]["agent_name"] == "sec_analyst"

    async def test_injects_prior_context_from_mem0(self):
        prior = ["Prior: Org-AI-R was 75.0 last run"]
        with patch.object(_specs.mcp_client, "call_tool",
                          _mcp_mock(get_company_evidence=[])), \
             patch.object(_specs.mem0_client, "search_memory",
                          new_callable=AsyncMock, return_value=prior), \
             patch.object(_specs.mem0_client, "add_memory",
                          new_callable=AsyncMock):
            from app.agents.supervisor import sec_analyst_node
            result = await sec_analyst_node(_base_state())
        assert result["sec_analysis"]["prior_context"] == prior

    async def test_persists_findings_to_mem0(self):
        with patch.object(_specs.mcp_client, "call_tool",
                          _mcp_mock(get_company_evidence=[])), \
             patch.object(_specs.mem0_client, "search_memory",
                          new_callable=AsyncMock, return_value=[]), \
             patch.object(_specs.mem0_client, "add_memory",
                          new_callable=AsyncMock) as mock_add:
            from app.agents.supervisor import sec_analyst_node
            await sec_analyst_node(_base_state())
        mock_add.assert_awaited_once()
        assert mock_add.call_args.kwargs["company_id"] == "NVDA"


# ═══════════════════════════════════════════════════════════════════════════════
# scorer_node — HITL trigger conditions
# HITL logic: requires_approval = org_air > 85 OR org_air < 40
# ═══════════════════════════════════════════════════════════════════════════════
class TestScorerNode:
    async def _run_scorer(self, org_air: float):
        with patch.object(_specs.mcp_client, "call_tool",
                          _mcp_mock(calculate_org_air_score=_score_data(org_air))), \
             patch.object(_specs.mem0_client, "search_memory",
                          new_callable=AsyncMock, return_value=[]), \
             patch.object(_specs.mem0_client, "add_memory",
                          new_callable=AsyncMock):
            from app.agents.supervisor import scorer_node
            return await scorer_node(_base_state(sec_analysis={"findings": []}))

    async def test_normal_score_no_hitl(self):
        result = await self._run_scorer(org_air=72.0)
        assert result["requires_approval"] is False
        assert result["approval_status"] is None

    async def test_high_score_triggers_hitl(self):
        result = await self._run_scorer(org_air=88.0)
        assert result["requires_approval"] is True
        assert result["approval_status"] == "pending"

    async def test_low_score_triggers_hitl(self):
        result = await self._run_scorer(org_air=35.0)
        assert result["requires_approval"] is True
        assert result["approval_status"] == "pending"

    async def test_boundary_score_above_85_triggers_hitl(self):
        # code uses strict >85, so 85.1 triggers HITL
        result = await self._run_scorer(org_air=85.1)
        assert result["requires_approval"] is True

    async def test_boundary_score_exactly_85_no_hitl(self):
        # 85.0 is NOT > 85 — should be within range
        result = await self._run_scorer(org_air=85.0)
        assert result["requires_approval"] is False

    async def test_boundary_score_84_no_hitl(self):
        result = await self._run_scorer(org_air=84.9)
        assert result["requires_approval"] is False

    async def test_score_stored_in_scoring_result(self):
        result = await self._run_scorer(org_air=72.0)
        assert result["scoring_result"]["org_air"] == 72.0

    async def test_approval_reason_set_on_hitl(self):
        result = await self._run_scorer(org_air=92.0)
        assert result["approval_reason"] is not None


# ═══════════════════════════════════════════════════════════════════════════════
# evidence_node
# ═══════════════════════════════════════════════════════════════════════════════
class TestEvidenceNode:
    async def test_generates_justifications_for_three_dimensions(self):
        just = {"score": 82.0, "justification": "Strong talent pipeline."}
        with patch.object(_specs.mcp_client, "call_tool",
                          _mcp_mock(generate_justification=just)), \
             patch.object(_specs.mem0_client, "search_memory",
                          new_callable=AsyncMock, return_value=[]), \
             patch.object(_specs.mem0_client, "add_memory",
                          new_callable=AsyncMock):
            from app.agents.supervisor import evidence_node
            result = await evidence_node(_base_state())
        justifications = result["evidence_justifications"]["justifications"]
        assert "data_infrastructure" in justifications
        assert "talent" in justifications
        assert "use_case_portfolio" in justifications

    async def test_appends_evidence_message(self):
        just = {"score": 75.0, "justification": "Moderate."}
        with patch.object(_specs.mcp_client, "call_tool",
                          _mcp_mock(generate_justification=just)), \
             patch.object(_specs.mem0_client, "search_memory",
                          new_callable=AsyncMock, return_value=[]), \
             patch.object(_specs.mem0_client, "add_memory",
                          new_callable=AsyncMock):
            from app.agents.supervisor import evidence_node
            result = await evidence_node(_base_state())
        assert result["messages"][0]["agent_name"] == "evidence_agent"


# ═══════════════════════════════════════════════════════════════════════════════
# value_creator_node
# HITL logic: requires_approval = projected_ebitda_pct > 5.0
# ═══════════════════════════════════════════════════════════════════════════════
class TestValueCreatorNode:
    async def _run_value_creator(self, ebitda_pct: float):
        with patch.object(_specs.mcp_client, "call_tool",
                          _mcp_mock(run_gap_analysis=_gap_data(ebitda_pct))), \
             patch.object(_specs.mem0_client, "search_memory",
                          new_callable=AsyncMock, return_value=[]), \
             patch.object(_specs.mem0_client, "add_memory",
                          new_callable=AsyncMock):
            from app.agents.supervisor import value_creator_node
            return await value_creator_node(_base_state())

    async def test_returns_value_creation_plan(self):
        result = await self._run_value_creator(ebitda_pct=3.8)
        assert result["value_creation_plan"]["company_id"] == "NVDA"

    async def test_ebitda_above_5_triggers_hitl(self):
        result = await self._run_value_creator(ebitda_pct=5.5)
        assert result["requires_approval"] is True

    async def test_ebitda_below_5_no_hitl(self):
        result = await self._run_value_creator(ebitda_pct=4.9)
        assert result["requires_approval"] is False

    async def test_ebitda_exactly_5_no_hitl(self):
        # code uses strict > 5.0, so exactly 5.0 is NOT over the threshold
        result = await self._run_value_creator(ebitda_pct=5.0)
        assert result["requires_approval"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# hitl_approval_node
# ═══════════════════════════════════════════════════════════════════════════════
class TestHITLApprovalNode:
    async def test_auto_approves(self):
        from app.agents.supervisor import hitl_approval_node
        result = await hitl_approval_node(
            _base_state(requires_approval=True, approval_status="pending",
                        approval_reason="Score 88 outside [40, 85]")
        )
        assert result["approval_status"] == "approved"

    async def test_sets_approved_by(self):
        from app.agents.supervisor import hitl_approval_node
        result = await hitl_approval_node(
            _base_state(requires_approval=True, approval_status="pending", approval_reason="test")
        )
        assert result["approved_by"] is not None

    async def test_appends_hitl_message(self):
        from app.agents.supervisor import hitl_approval_node
        result = await hitl_approval_node(
            _base_state(requires_approval=True, approval_status="pending", approval_reason="high score")
        )
        assert result["messages"][0]["agent_name"] == "hitl"


# ═══════════════════════════════════════════════════════════════════════════════
# complete_node
# ═══════════════════════════════════════════════════════════════════════════════
class TestCompleteNode:
    async def test_sets_completed_at(self):
        from app.agents.supervisor import complete_node
        result = await complete_node(_base_state())
        assert isinstance(result["completed_at"], datetime)

    async def test_appends_completion_message(self):
        from app.agents.supervisor import complete_node
        result = await complete_node(_base_state())
        assert result["messages"][0]["agent_name"] == "supervisor"
        assert "NVDA" in result["messages"][0]["content"]


# ═══════════════════════════════════════════════════════════════════════════════
# Full workflow integration (mocked MCP + mem0)
# ═══════════════════════════════════════════════════════════════════════════════
class TestFullWorkflow:
    def _patches(self, org_air: float = 72.0, ebitda_pct: float = 3.5):
        """All 4 context-manager patches needed for a complete workflow run."""
        evidence = [{"dimension": "talent", "content": "Strong"}]
        justification = {"score": 80.0, "justification": "Good."}
        return (
            patch.object(_specs.mcp_client, "call_tool", _mcp_mock(
                get_company_evidence=evidence,
                calculate_org_air_score=_score_data(org_air),
                generate_justification=justification,
                run_gap_analysis=_gap_data(ebitda_pct),
            )),
            patch.object(_specs.mem0_client, "search_memory",
                         new_callable=AsyncMock, return_value=[]),
            patch.object(_specs.mem0_client, "add_memory",
                         new_callable=AsyncMock),
        )

    async def test_quick_mode_skips_value_creator(self):
        from app.agents.supervisor import dd_graph
        initial = _base_state(assessment_type="quick")
        config = {"configurable": {"thread_id": "test-quick-wf"}}
        p = self._patches(org_air=72.0)
        with p[0], p[1], p[2]:
            result = await dd_graph.ainvoke(initial, config)

        assert result["sec_analysis"] is not None
        assert result["scoring_result"] is not None
        assert result["evidence_justifications"] is not None
        assert result["value_creation_plan"] is None
        assert result["completed_at"] is not None

    async def test_full_mode_includes_value_creator(self):
        from app.agents.supervisor import dd_graph
        initial = _base_state(assessment_type="full")
        config = {"configurable": {"thread_id": "test-full-wf"}}
        p = self._patches(org_air=72.0, ebitda_pct=3.5)
        with p[0], p[1], p[2]:
            result = await dd_graph.ainvoke(initial, config)

        assert result["value_creation_plan"] is not None
        assert result["completed_at"] is not None

    async def test_hitl_auto_approved_for_high_score(self):
        from app.agents.supervisor import dd_graph
        initial = _base_state(assessment_type="full")
        config = {"configurable": {"thread_id": "test-hitl-wf"}}
        p = self._patches(org_air=92.0, ebitda_pct=3.0)
        with p[0], p[1], p[2]:
            result = await dd_graph.ainvoke(initial, config)

        assert result["approval_status"] == "approved"
        assert result["completed_at"] is not None

    async def test_messages_accumulate_from_all_agents(self):
        from app.agents.supervisor import dd_graph
        initial = _base_state(assessment_type="full")
        config = {"configurable": {"thread_id": "test-msgs-wf"}}
        p = self._patches(org_air=72.0, ebitda_pct=3.5)
        with p[0], p[1], p[2]:
            result = await dd_graph.ainvoke(initial, config)

        agent_names = {m["agent_name"] for m in result["messages"]}
        assert {"sec_analyst", "scorer", "evidence_agent"}.issubset(agent_names)
