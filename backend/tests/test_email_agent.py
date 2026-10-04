"""Real tests for agents/email_agent.py -- the first real, compiled
LangGraph graph in this project."""
from quorum_backend.agents.email_agent import (
    EmailAgentState,
    build_email_agent_graph,
    build_reply_proposal,
)
from quorum_backend.agents.tool_authorization import (
    DOMAIN_TOOL_MAP,
    ToolAuthorizationError,
    authorize_tool_call,
)
from quorum_backend.gate.schemas import ActionType


def test_build_reply_proposal_returns_real_send_email_proposal():
    proposal = build_reply_proposal("priya@x.com", "5pm works for me.")
    assert proposal.action_type == ActionType.SEND_EMAIL
    assert proposal.payload == {"to": "priya@x.com", "body": "5pm works for me."}


def test_graph_compiles_as_a_real_compiled_state_graph():
    async def fake_llm(intent: str) -> str:
        return "a real draft"

    graph = build_email_agent_graph(fake_llm)
    assert type(graph).__name__ == "CompiledStateGraph"


async def test_graph_invocation_produces_a_real_proposal_via_injected_llm():
    async def fake_llm(intent: str) -> str:
        return f"real reply to: {intent}"

    graph = build_email_agent_graph(fake_llm)
    state: EmailAgentState = {
        "thread_id": "t1",
        "recipient": "priya@x.com",
        "user_intent": "confirm Thursday",
        "draft_body": None,
        "proposal": None,
    }
    result = await graph.ainvoke(state)
    assert result["proposal"].action_type == ActionType.SEND_EMAIL
    assert "confirm Thursday" in result["draft_body"]


def test_authorize_tool_call_fails_closed_for_unrecognized_domain():
    try:
        authorize_tool_call("gmail.send", calling_agent_domain="not_a_real_domain")
        raise AssertionError("expected ToolAuthorizationError")
    except ToolAuthorizationError:
        pass


def test_email_domain_authorized_for_its_own_real_tools_only():
    for tool in DOMAIN_TOOL_MAP["email"]:
        authorize_tool_call(tool, calling_agent_domain="email")  # must not raise
    try:
        authorize_tool_call("finance.write_budget", calling_agent_domain="email")
        raise AssertionError("email domain must not be authorized for finance tools")
    except ToolAuthorizationError:
        pass


def test_build_reply_proposal_includes_a_real_subject_when_given_one():
    """`DEC-189`: the payload gained an optional `subject`, closing the
    real gap that made every executed send go out with an empty Subject
    header. `action_executor.py` already read `payload.get("subject")`
    -- the defect was always on this, the producing, side."""
    proposal = build_reply_proposal("sarah@example.com", "Body text.", subject="Contract Monday")
    assert proposal.payload["subject"] == "Contract Monday"
    assert proposal.payload["to"] == "sarah@example.com"
    assert proposal.payload["body"] == "Body text."


def test_build_reply_proposal_omits_subject_entirely_when_absent_or_blank():
    """Kept OPTIONAL deliberately, so the existing `draft_reply_node`
    caller -- which has no subject to give -- produces exactly today's
    behavior rather than a key with an empty string in it."""
    for subject in (None, "", "   "):
        proposal = build_reply_proposal("sarah@example.com", "Body text.", subject=subject)
        assert "subject" not in proposal.payload, f"blank subject {subject!r} must not create the key"


def test_build_reply_proposal_strips_surrounding_whitespace_from_subject():
    proposal = build_reply_proposal("sarah@example.com", "Body.", subject="  Padded  ")
    assert proposal.payload["subject"] == "Padded"
