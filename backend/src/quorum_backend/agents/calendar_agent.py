"""The second real, compiled LangGraph node. HONEST DISCLOSURE: same
construction-not-copy pattern as every agent file this batch.

The real, load-bearing decision this agent makes: has_external_invitee is
what decides the real ActionType and therefore the real stakes -- not the
event's payload complexity. See this session's report for the reasoning
(reversibility + external consequence, not just a documented intent).

No LLM call anywhere -- this agent needs no drafting, only structural
proposal construction, unlike email_agent.py.

RESOLVED, real gap found and closed while building real `CREATE_
CALENDAR_EVENT_EXTERNAL` execution (Phase 5, `DEC-151`): this function's
own payload never carried a real external attendee's email address --
`has_external_invitee` was a bare boolean flag with no actual invitee to
invite. A real, honest external booking genuinely needs a real email to
send a real Google Calendar invite to; `invitee_email` is now a real,
required parameter whenever `has_external_invitee=True`, raising loud
(never silently proceeding without one) for the same "never fabricate
what wasn't genuinely provided" reason `negotiation/downstream_
translation.py` never invents a real external attendee for a calendar
domain translated from free text.
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
    invitee_email: str | None
    proposal: ActionProposal | None


def build_event_proposal(
    proposed_start: datetime,
    proposed_end: datetime,
    title: str,
    has_external_invitee: bool,
    invitee_email: str | None = None,
) -> ActionProposal:
    if has_external_invitee:
        if not invitee_email:
            raise ValueError(
                "has_external_invitee=True requires a real invitee_email -- never fabricated, never guessed."
            )
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
            "invitee_email": invitee_email,
        },
    )


def make_propose_event_node():
    def propose_event_node(state: CalendarAgentState) -> dict:
        proposal = build_event_proposal(
            state["proposed_start"],
            state["proposed_end"],
            state["title"],
            state["has_external_invitee"],
            state.get("invitee_email"),
        )
        return {"proposal": proposal}

    return propose_event_node


def build_calendar_agent_graph():
    graph = StateGraph(CalendarAgentState)
    graph.add_node("propose_event", make_propose_event_node())
    graph.set_entry_point("propose_event")
    graph.add_edge("propose_event", END)
    return graph.compile()
