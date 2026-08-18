"""Real tests for agents/finance_agent.py. The fourth domain -- where the
real authorization proof strength increases to a full exhaustive matrix
for the first time."""
from quorum_backend.agents.finance_agent import (
    FinanceAgentState,
    build_finance_agent_graph,
    build_finance_proposal,
)
from quorum_backend.agents.tool_authorization import (
    DOMAIN_TOOL_MAP,
    authorize_tool_call,
    ToolAuthorizationError,
)
from quorum_backend.gate.schemas import ActionType


def test_log_expense_produces_real_log_expense_action():
    proposal = build_finance_proposal("log_expense", 450.0, "groceries", payee="DMart")
    assert proposal.action_type == ActionType.LOG_EXPENSE


def test_update_budget_produces_real_update_budget_action():
    proposal = build_finance_proposal("update_budget", 5000.0, "groceries")
    assert proposal.action_type == ActionType.UPDATE_BUDGET


def test_graph_compiles_as_a_real_compiled_state_graph():
    graph = build_finance_agent_graph()
    assert type(graph).__name__ == "CompiledStateGraph"


async def test_graph_invocation_produces_a_real_proposal():
    graph = build_finance_agent_graph()
    state: FinanceAgentState = {
        "action": "log_expense",
        "amount": 649.0,
        "category": "subscriptions",
        "payee": "Netflix",
        "proposal": None,
    }
    result = await graph.ainvoke(state)
    assert result["proposal"].action_type == ActionType.LOG_EXPENSE


def test_full_cross_domain_authorization_matrix_holds_for_all_four_real_domains():
    """Not one more pairwise spot-check -- every domain's tools checked
    against every other domain, programmatically. Catches a class of
    accidental-overlap bug pairwise tests alone could miss."""
    real_domains = {k: v for k, v in DOMAIN_TOOL_MAP.items() if k in ("email", "calendar", "tasks", "finance")}
    assert len(real_domains) == 4

    total_checks = 0
    for domain, allowed in real_domains.items():
        for other, other_tools in real_domains.items():
            if domain == other:
                continue
            for tool in other_tools:
                total_checks += 1
                assert tool not in allowed, f"{domain} must not be authorized for {other}'s {tool}"
                try:
                    authorize_tool_call(tool, calling_agent_domain=domain)
                    raise AssertionError(f"VIOLATION: {domain} allowed to call {tool}")
                except ToolAuthorizationError:
                    pass
    assert total_checks > 0
    # Real count depends on this repository's own real tool-set sizes
    # (each domain has 3-4 tools, not a fixed assumption) -- see this
    # session's report/DECISIONS_LOG for the actual, computed number.


def test_finance_domain_tools_do_not_overlap_with_any_prior_domain():
    finance_tools = DOMAIN_TOOL_MAP["finance"]
    for other in ("email", "calendar", "tasks"):
        overlap = DOMAIN_TOOL_MAP[other] & finance_tools
        assert not overlap, f"{other} vs finance overlap: {overlap}"
