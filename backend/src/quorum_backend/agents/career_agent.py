"""Fifth and final real, compiled LangGraph node -- and the first genuinely
branching graph in this project. Same construction-not-copy pattern as
every agent this batch, held to the same rigor regardless.

Inherits, without re-deriving: the "agents propose, Gate verifies" boundary
from DEC-013 -- this agent has no detection pipeline of its own;
is_interview_detected and search_findings arrive as already-resolved
state, per the ADD's explicit design (Career rides on Email's ingestion).

Two real nodes, not one, because this domain's job genuinely branches --
see this session's report for why. update_status ALWAYS runs; compile_digest
runs ONLY when a real interview has been detected AND real search findings
have actually returned -- the exact edge case (detected before findings
arrive) is proven separately, not assumed to be the same as "not detected."
"""
from __future__ import annotations

from typing import Awaitable, Callable, TypedDict

from langgraph.graph import END, StateGraph

from quorum_backend.agents.tool_authorization import authorize_tool_call
from quorum_backend.gate.schemas import ActionProposal, ActionType

CompileDigestCall = Callable[[str, list[str]], Awaitable[dict]]


class CareerAgentState(TypedDict):
    application_id: str
    company: str
    new_status: str
    is_interview_detected: bool
    search_findings: list[str] | None
    status_proposal: ActionProposal | None
    digest: dict | None


def build_status_update_proposal(application_id: str, new_status: str) -> ActionProposal:
    authorize_tool_call("career.update_application_status", calling_agent_domain="career")
    return ActionProposal(
        action_type=ActionType.UPDATE_APPLICATION_STATUS,
        payload={"application_id": application_id, "status": new_status},
    )


def make_update_status_node():
    def update_status_node(state: CareerAgentState) -> dict:
        proposal = build_status_update_proposal(state["application_id"], state["new_status"])
        return {"status_proposal": proposal}

    return update_status_node


def make_compile_digest_node(compile_digest_call: CompileDigestCall):
    """Factory -- compile_digest_call (the real search/LLM-backed
    compilation) is injected, never imported or called by name directly,
    same discipline as email_agent.py's llm_call."""

    async def compile_digest_node(state: CareerAgentState) -> dict:
        digest = await compile_digest_call(state["company"], state["search_findings"] or [])
        return {"digest": digest}

    return compile_digest_node


def route_after_status_update(state: CareerAgentState) -> str:
    """Real conditional routing, not a hardcoded single path: proceeds to
    digest compilation only when BOTH a real interview is detected AND
    real search findings have actually returned -- detection alone is not
    enough, since the two events don't happen simultaneously."""
    if state.get("is_interview_detected") and state.get("search_findings"):
        return "compile_digest"
    return END


def build_career_agent_graph(compile_digest_call: CompileDigestCall):
    graph = StateGraph(CareerAgentState)
    graph.add_node("update_status", make_update_status_node())
    graph.add_node("compile_digest", make_compile_digest_node(compile_digest_call))
    graph.set_entry_point("update_status")
    graph.add_conditional_edges(
        "update_status", route_after_status_update, {"compile_digest": "compile_digest", END: END}
    )
    graph.add_edge("compile_digest", END)
    return graph.compile()
