"""
LangGraph State Definitions (Task 10.1)

Defines the message structure and workflow state for the multi-agent
due diligence system.  Every node reads from and writes to
``DueDiligenceState``; LangGraph merges partial dicts returned by nodes
into the running state using the declared reducers.
"""
import operator
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional, TypedDict


class AgentMessage(TypedDict):
    """Single message produced by an agent node."""
    role: str          # "user" | "assistant" | "system"
    content: str
    agent_name: str
    timestamp: datetime


class DueDiligenceState(TypedDict):
    """
    Shared state object that flows through every node in the
    due-diligence LangGraph workflow.

    Inputs (set once at invocation time):
        company_id      – ticker or internal ID, e.g. "NVDA"
        assessment_type – "screening" | "limited" | "full"
        requested_by    – analyst / system identifier

    Agent outputs (each specialist populates its own key):
        sec_analysis          – SECAnalysisAgent output
        talent_analysis       – talent / leadership analysis (optional)
        scoring_result        – ScoringAgent output (org_air, vr, hr …)
        evidence_justifications – EvidenceAgent output (dim → justification)
        value_creation_plan   – ValueCreationAgent output (gap analysis)

    Workflow control:
        next_agent      – which node the supervisor routes to next
        requires_approval  – True when HITL gate must fire
        approval_reason    – human-readable explanation of why approval needed
        approval_status    – "pending" | "approved" | "rejected"
        approved_by        – identifier of the approver

    Metadata:
        started_at    – workflow start timestamp
        completed_at  – workflow completion timestamp (set by complete_node)
        total_tokens  – cumulative LLM token usage across all agents
        error         – error message if workflow fails
    """

    # -- Inputs ----------------------------------------------------------------
    company_id: str
    assessment_type: str   # "screening" | "limited" | "full"
    requested_by: str

    # -- Message history (append-only via operator.add reducer) ---------------
    messages: Annotated[List[AgentMessage], operator.add]

    # -- Agent outputs ---------------------------------------------------------
    sec_analysis: Optional[Dict[str, Any]]
    talent_analysis: Optional[Dict[str, Any]]
    scoring_result: Optional[Dict[str, Any]]
    evidence_justifications: Optional[Dict[str, Any]]
    value_creation_plan: Optional[Dict[str, Any]]

    # -- Workflow control ------------------------------------------------------
    next_agent: Optional[str]
    requires_approval: bool
    approval_reason: Optional[str]
    approval_status: Optional[str]   # "pending" | "approved" | "rejected"
    approved_by: Optional[str]

    # -- Metadata --------------------------------------------------------------
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    total_tokens: int
    error: Optional[str]
