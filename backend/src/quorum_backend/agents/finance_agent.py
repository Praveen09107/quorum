"""Fourth real, compiled LangGraph node. Same construction-not-copy pattern.

Inherits, without re-deriving: per DEC-013, no self-check of
budget_check() before proposing -- that stays Stage A's job exclusively,
same reasoning already established for tasks_agent.py.

The real decision this agent makes: logging a new expense (LOG_EXPENSE, S1)
versus changing a budget ceiling itself (UPDATE_BUDGET, S2) -- a
genuinely different-stakes distinction.

REAL, DISCLOSED SESSION-6 EXTENSION (`QUORUM_FINAL_COMPLETION_PLAN.md`):
`update_expense`/`delete_expense` are real, new, first-class `FinanceAction`
values -- a real edit or deletion of an EXISTING `expenses` row, genuinely
distinct from `log_expense`'s own fresh, additive write. `existing_expense_id`
mirrors `tasks_agent.py::build_task_proposal()`'s own already-established
"presence of an existing-record id, not a fuzzier inference" convention
exactly. `amount`/`category` become optional here (defaulting to `None`)
specifically because `delete_expense` needs neither -- every existing real
caller (`retry_queue_drainer.py`'s own negotiation-originated `log_expense`/
`update_budget` calls) already passes both by keyword, so this stays a real,
backward-compatible widening, not a behavior change for any real caller
that predates this session.
"""
from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.graph import END, StateGraph

from quorum_backend.agents.tool_authorization import authorize_tool_call
from quorum_backend.gate.schemas import ActionProposal, ActionType

FinanceAction = Literal["log_expense", "update_budget", "update_expense", "delete_expense"]


class FinanceAgentState(TypedDict):
    action: FinanceAction
    amount: float
    category: str
    payee: str | None
    proposal: ActionProposal | None


def build_finance_proposal(
    action: FinanceAction,
    amount: float | None = None,
    category: str | None = None,
    payee: str | None = None,
    existing_expense_id: str | None = None,
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
    if action == "update_expense":
        authorize_tool_call("finance.update_expense", calling_agent_domain="finance")
        return ActionProposal(
            action_type=ActionType.UPDATE_EXPENSE,
            payload={"existing_expense_id": existing_expense_id, "amount": amount, "payee": payee},
        )
    if action == "delete_expense":
        authorize_tool_call("finance.delete_expense", calling_agent_domain="finance")
        # `amount`/`payee` are real DISPLAY-ONLY context here (matching
        # `tasks_agent.py::build_task_deletion_proposal()`'s own
        # identical real reasoning) -- `action_executor.py`'s own real
        # `DELETE_EXPENSE` branch only ever reads `existing_expense_id`.
        return ActionProposal(
            action_type=ActionType.DELETE_EXPENSE,
            payload={"existing_expense_id": existing_expense_id, "amount": amount, "payee": payee},
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
