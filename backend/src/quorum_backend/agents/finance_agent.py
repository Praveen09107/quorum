"""Fourth real, compiled LangGraph node. Same construction-not-copy pattern.

Inherits, without re-deriving: per DEC-013, no self-check of
budget_check() before proposing -- that stays Stage A's job exclusively,
same reasoning already established for tasks_agent.py.

The real decision this agent makes: logging a new expense (LOG_EXPENSE, S1)
versus changing a budget ceiling itself (UPDATE_BUDGET, S2) -- a
genuinely different-stakes distinction.
"""
from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.graph import END, StateGraph

from quorum_backend.agents.tool_authorization import authorize_tool_call
from quorum_backend.gate.schemas import ActionProposal, ActionType

FinanceAction = Literal["log_expense", "update_budget"]


class FinanceAgentState(TypedDict):
    action: FinanceAction
    amount: float
    category: str
    payee: str | None
    proposal: ActionProposal | None


def build_finance_proposal(
    action: FinanceAction,
    amount: float,
    category: str,
    payee: str | None = None,
) -> ActionProposal:
    if action == "log_expense":
        authorize_tool_call("finance.log_expense", calling_agent_domain="finance")
        return ActionProposal(
            action_type=ActionType.LOG_EXPENSE,
            payload={"amount": amount, "category": category, "payee": payee},
        )
    if action == "update_budget":
        authorize_tool_call("finance.write_budget", calling_agent_domain="finance")
        return ActionProposal(
            action_type=ActionType.UPDATE_BUDGET,
            payload={"amount": amount, "category": category},
        )
    raise ValueError(f"Unrecognized finance action: {action!r}")


def make_propose_finance_action_node():
    def propose_finance_action_node(state: FinanceAgentState) -> dict:
        proposal = build_finance_proposal(
            state["action"], state["amount"], state["category"], state.get("payee")
        )
        return {"proposal": proposal}

    return propose_finance_action_node


def build_finance_agent_graph():
    graph = StateGraph(FinanceAgentState)
    graph.add_node("propose_finance_action", make_propose_finance_action_node())
    graph.set_entry_point("propose_finance_action")
    graph.add_edge("propose_finance_action", END)
    return graph.compile()
