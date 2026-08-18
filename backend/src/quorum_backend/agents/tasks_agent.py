"""Third real, compiled LangGraph node. Same construction-not-copy pattern.

Inherits, without re-deriving: per this project's own established boundary
(agents propose, the Gate verifies), this agent does NOT self-check
deadline_conflict_check() before proposing -- that stays Stage A's job
exclusively. See this session's report for why duplicating it would be a
real architectural mistake, not just redundant code.
"""
from __future__ import annotations

from datetime import datetime
from typing import TypedDict

from langgraph.graph import END, StateGraph

from quorum_backend.agents.tool_authorization import authorize_tool_call
from quorum_backend.gate.schemas import ActionProposal, ActionType


class TasksAgentState(TypedDict):
    title: str
    estimated_hours: float
    deadline: datetime | None
    existing_task_id: str | None
    proposal: ActionProposal | None


def build_task_proposal(
    title: str,
    estimated_hours: float,
    deadline: datetime | None = None,
    existing_task_id: str | None = None,
) -> ActionProposal:
    """create vs. update, based on whether an existing task is actually
    referenced -- existing_task_id present or absent, not inferred from
    anything fuzzier."""
    if existing_task_id is not None:
        authorize_tool_call("tasks.update", calling_agent_domain="tasks")
        action_type = ActionType.UPDATE_TASK
    else:
        authorize_tool_call("tasks.create", calling_agent_domain="tasks")
        action_type = ActionType.CREATE_TASK

    return ActionProposal(
        action_type=action_type,
        payload={
            "title": title,
            "estimated_hours": estimated_hours,
            "deadline": deadline.isoformat() if deadline else None,
            "existing_task_id": existing_task_id,
        },
    )


def make_propose_task_node():
    def propose_task_node(state: TasksAgentState) -> dict:
        proposal = build_task_proposal(
            state["title"],
            state["estimated_hours"],
            state.get("deadline"),
            state.get("existing_task_id"),
        )
        return {"proposal": proposal}

    return propose_task_node


def build_tasks_agent_graph():
    graph = StateGraph(TasksAgentState)
    graph.add_node("propose_task", make_propose_task_node())
    graph.set_entry_point("propose_task")
    graph.add_edge("propose_task", END)
    return graph.compile()
