"""The second real, compiled LangGraph node. HONEST DISCLOSURE: same
construction-not-copy pattern as every agent file this batch.

The real, load-bearing decision this agent makes: has_external_invitee is
what decides the real ActionType and therefore the real stakes -- not the
event's payload complexity. See this session's report for the reasoning
(reversibility + external consequence, not just a documented intent).

No LLM call anywhere -- this agent needs no drafting, only structural
proposal construction, unlike email_agent.py.
"""
from __future__ import annotations

from datetime import datetime
from typing import TypedDict

from langgraph.graph import END, StateGraph

from quorum_backend.agents.tool_authorization import authorize_tool_call
from quorum_backend.gate.schemas import ActionProposal, ActionType


class CalendarAgentState(TypedDict):
    proposed_start: datetime
    proposed_end: datetime
    title: str
    has_external_invitee: bool
    proposal: ActionProposal | None


def build_event_proposal(
    proposed_start: datetime,
    proposed_end: datetime,
    title: str,
    has_external_invitee: bool,
) -> ActionProposal:
    if has_external_invitee:
        authorize_tool_call("calendar.create_external", calling_agent_domain="calendar")
        action_type = ActionType.CREATE_CALENDAR_EVENT_EXTERNAL
    else:
        authorize_tool_call("calendar.create_local", calling_agent_domain="calendar")
        action_type = ActionType.CREATE_CALENDAR_EVENT_LOCAL

    return ActionProposal(
        action_type=action_type,
        payload={
            "start": proposed_start.isoformat(),
            "end": proposed_end.isoformat(),
            "title": title,
            "has_external_invitee": has_external_invitee,
        },
    )


def make_propose_event_node():
    def propose_event_node(state: CalendarAgentState) -> dict:
        proposal = build_event_proposal(
            state["proposed_start"],
            state["proposed_end"],
            state["title"],
            state["has_external_invitee"],
        )
        return {"proposal": proposal}

    return propose_event_node


def build_calendar_agent_graph():
    graph = StateGraph(CalendarAgentState)
    graph.add_node("propose_event", make_propose_event_node())
    graph.set_entry_point("propose_event")
    graph.add_edge("propose_event", END)
    return graph.compile()
