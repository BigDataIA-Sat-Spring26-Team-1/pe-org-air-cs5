"""
Supervisor Agent (Lab 10.3) - LangGraph orchestration for the due diligence workflow.
"""
from typing import Literal, Dict, Any
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import structlog

from agents.state import DueDiligenceState
from agents.specialists import sec_agent, scoring_agent, evidence_agent, value_agent

logger = structlog.get_logger()


async def supervisor_node(state: DueDiligenceState) -> Dict[str, Any]:
    if state.get("requires_approval") and state.get("approval_status") == "pending":
        return {"next_agent": "hitl_approval"}
    elif not state.get("sec_analysis"):
        return {"next_agent": "sec_analyst"}
    elif not state.get("scoring_result"):
        return {"next_agent": "scorer"}
    elif not state.get("evidence_justifications"):
        return {"next_agent": "evidence_agent"}
    elif not state.get("value_creation_plan") and state["assessment_type"] != "screening":
        return {"next_agent": "value_creator"}
    else:
        return {"next_agent": "complete"}


async def sec_analyst_node(state: DueDiligenceState) -> Dict[str, Any]:
    return await sec_agent.analyze(state)


async def scorer_node(state: DueDiligenceState) -> Dict[str, Any]:
    return await scoring_agent.calculate(state)


async def evidence_node(state: DueDiligenceState) -> Dict[str, Any]:
    return await evidence_agent.justify(state)


async def value_creator_node(state: DueDiligenceState) -> Dict[str, Any]:
    return await value_agent.plan(state)


async def hitl_approval_node(state: DueDiligenceState) -> Dict[str, Any]:
    logger.warning(
        "hitl_approval_required",
        company_id=state["company_id"],
        reason=state.get("approval_reason"),
    )
    return {
        "approval_status": "approved",
        "approved_by": "exercise_auto_approve",
        "messages": [
            {
                "role": "system",
                "content": f"HITL approval granted: {state.get('approval_reason')}",
                "agent_name": "hitl",
                "timestamp": datetime.utcnow(),
            }
        ],
    }


async def complete_node(state: DueDiligenceState) -> Dict[str, Any]:
    return {
        "completed_at": datetime.utcnow(),
        "messages": [
            {
                "role": "assistant",
                "content": f"Due diligence complete for {state['company_id']}",
                "agent_name": "supervisor",
                "timestamp": datetime.utcnow(),
            }
        ],
    }


def create_due_diligence_graph():
    workflow = StateGraph(DueDiligenceState)

    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("sec_analyst", sec_analyst_node)
    workflow.add_node("scorer", scorer_node)
    workflow.add_node("evidence_agent", evidence_node)
    workflow.add_node("value_creator", value_creator_node)
    workflow.add_node("hitl_approval", hitl_approval_node)
    workflow.add_node("complete", complete_node)

    workflow.add_conditional_edges(
        "supervisor",
        lambda s: s["next_agent"],
        {
            "sec_analyst": "sec_analyst",
            "scorer": "scorer",
            "evidence_agent": "evidence_agent",
            "value_creator": "value_creator",
            "hitl_approval": "hitl_approval",
            "complete": "complete",
        },
    )

    for node in ["sec_analyst", "scorer", "evidence_agent", "value_creator"]:
        workflow.add_edge(node, "supervisor")

    workflow.add_edge("hitl_approval", "supervisor")
    workflow.add_edge("complete", END)
    workflow.set_entry_point("supervisor")

    return workflow.compile(checkpointer=MemorySaver())


dd_graph = create_due_diligence_graph()
