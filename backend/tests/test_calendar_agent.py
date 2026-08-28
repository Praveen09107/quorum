"""Real tests for agents/calendar_agent.py."""
from datetime import datetime, timezone

from quorum_backend.agents.calendar_agent import (
    CalendarAgentState,
    build_calendar_agent_graph,
    build_event_proposal,
)
from quorum_backend.agents.tool_authorization import (
    DOMAIN_TOOL_MAP,
    ToolAuthorizationError,
    authorize_tool_call,
)
from quorum_backend.gate.schemas import ActionType
from quorum_backend.router import get_stakes


def _now():
    return datetime.now(timezone.utc)


def test_local_event_produces_create_calendar_event_local():
    proposal = build_event_proposal(_now(), _now(), "team sync", has_external_invitee=False)
    assert proposal.action_type == ActionType.CREATE_CALENDAR_EVENT_LOCAL


def test_external_event_produces_create_calendar_event_external():
    proposal = build_event_proposal(
        _now(), _now(), "vendor call", has_external_invitee=True, invitee_email="vendor@example.com"
    )
    assert proposal.action_type == ActionType.CREATE_CALENDAR_EVENT_EXTERNAL
    assert proposal.payload["invitee_email"] == "vendor@example.com"


def test_external_event_without_a_real_invitee_email_fails_loud():
    """RESOLVED, `DEC-151`: a real, honest external booking needs a real
    email to invite -- never fabricated, never silently proceeding
    without one."""
    try:
        build_event_proposal(_now(), _now(), "vendor call", has_external_invitee=True, invitee_email=None)
        raise AssertionError("should have raised ValueError")
    except ValueError:
        pass


def test_graph_compiles_as_a_real_compiled_state_graph():
    graph = build_calendar_agent_graph()
    assert type(graph).__name__ == "CompiledStateGraph"


async def test_graph_invocation_produces_a_real_proposal():
    graph = build_calendar_agent_graph()
    state: CalendarAgentState = {
        "proposed_start": _now(),
        "proposed_end": _now(),
        "title": "1:1",
        "has_external_invitee": False,
        "invitee_email": None,
        "proposal": None,
    }
    result = await graph.ainvoke(state)
    assert result["proposal"].action_type == ActionType.CREATE_CALENDAR_EVENT_LOCAL


async def test_graph_invocation_produces_a_real_external_proposal_with_a_real_invitee():
    graph = build_calendar_agent_graph()
    state: CalendarAgentState = {
        "proposed_start": _now(),
        "proposed_end": _now(),
        "title": "vendor call",
        "has_external_invitee": True,
        "invitee_email": "vendor@example.com",
        "proposal": None,
    }
    result = await graph.ainvoke(state)
    assert result["proposal"].action_type == ActionType.CREATE_CALENDAR_EVENT_EXTERNAL
    assert result["proposal"].payload["invitee_email"] == "vendor@example.com"


def test_calendar_domain_is_authorized_for_its_own_tools():
    for tool in DOMAIN_TOOL_MAP["calendar"]:
        authorize_tool_call(tool, calling_agent_domain="calendar")  # must not raise


def test_calendar_domain_still_cannot_touch_email_tools():
    for tool in DOMAIN_TOOL_MAP["email"]:
        try:
            authorize_tool_call(tool, calling_agent_domain="calendar")
            raise AssertionError(f"calendar must not be authorized for {tool}")
        except ToolAuthorizationError:
            pass


def test_email_domain_still_cannot_touch_calendar_tools():
    # A real regression check on IMPL_13's own domain -- proves this
    # extension didn't accidentally loosen email's authorization.
    for tool in DOMAIN_TOOL_MAP["calendar"]:
        try:
            authorize_tool_call(tool, calling_agent_domain="email")
            raise AssertionError(f"email must not be authorized for {tool}")
        except ToolAuthorizationError:
            pass


def test_local_and_external_events_route_to_genuinely_different_real_stakes():
    # A real, cross-session integration proof -- not just that the
    # ActionType differs, but that IMPL_09's real get_stakes() resolves
    # each to the correct, different stakes level.
    local = build_event_proposal(_now(), _now(), "team sync", has_external_invitee=False)
    external = build_event_proposal(
        _now(), _now(), "vendor call", has_external_invitee=True, invitee_email="vendor@example.com"
    )
    from quorum_backend.gate.schemas import Stakes

    assert get_stakes(local.action_type) == Stakes.S2
    assert get_stakes(external.action_type) == Stakes.S3
