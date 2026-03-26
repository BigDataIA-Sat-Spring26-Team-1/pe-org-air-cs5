"""
Agentic Due Diligence Exercise (Lab 10) - End-to-end multi-agent workflow.
"""
import asyncio
from datetime import datetime

from agents.supervisor import dd_graph
from agents.state import DueDiligenceState


async def run_due_diligence(company_id: str, assessment_type: str = "full") -> DueDiligenceState:
    initial_state: DueDiligenceState = {
        "company_id": company_id,
        "assessment_type": assessment_type,
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
        "started_at": datetime.utcnow(),
        "completed_at": None,
        "total_tokens": 0,
        "error": None,
    }
    config = {"configurable": {"thread_id": f"dd-{company_id}-{datetime.now().isoformat()}"}}
    return await dd_graph.ainvoke(initial_state, config)


async def main():
    print("=" * 60)
    print("PE Org-AI-R: Agentic Due Diligence")
    print("=" * 60)
    result = await run_due_diligence("NVDA", "full")
    print(f"\nOrg-AI-R: {result['scoring_result']['org_air']:.1f}")
    print(f"HITL Required: {result.get('requires_approval', False)}")
    print(f"Status: {result.get('approval_status', 'N/A')}")
    print("\nAll data came from CS1-CS4 via MCP tools.")


if __name__ == "__main__":
    asyncio.run(main())