"""
LangGraph State Definitions
Defines the `DueDiligenceState` object that flows between nodes.
"""
import operator
from typing import Annotated, Any, Dict, List, TypedDict, Optional
from langchain_core.messages import BaseMessage

# Define how list elements should be merged
def add_messages(left: list[BaseMessage], right: list[BaseMessage]) -> list[BaseMessage]:
    return left + right

class DueDiligenceState(TypedDict):
    """
    Core state dictionary representing the workflow context
    for the multi-agent system.
    """
    # Core identifying info
    company_id: str
    target_org_air: Optional[float]
    
    # Message history with reducer
    messages: Annotated[list[BaseMessage], add_messages]
    
    # Sub-agent outputs. Each agent populates its domain.
    sec_analysis: Dict[str, Any]
    scoring_data: Dict[str, Any]
    evidence_data: Dict[str, Any]
    value_creation: Dict[str, Any]
    
    # Final aggregation for HITL supervisor
    final_score: float
    ebitda_impact: float
    
    # HITL flags
    requires_approval: bool
    hitl_approved: bool

    # Current step routing
    next_node: str
