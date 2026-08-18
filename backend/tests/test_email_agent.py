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
