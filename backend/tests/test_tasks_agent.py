"""Real tests for agents/tasks_agent.py."""
from quorum_backend.agents.tasks_agent import (
    TasksAgentState,
    build_task_proposal,
    build_tasks_agent_graph,
)
from quorum_backend.agents.tool_authorization import DOMAIN_TOOL_MAP
from quorum_backend.gate.schemas import ActionType
from quorum_backend.router import get_stakes
from quorum_backend.gate.schemas import Stakes


def test_new_task_produces_create_task():
    proposal = build_task_proposal("Finish Q3 review", 2.5)
    assert proposal.action_type == ActionType.CREATE_TASK


def test_existing_task_id_produces_update_task():
    proposal = build_task_proposal("Finish Q3 review", 2.5, existing_task_id="task_123")
    assert proposal.action_type == ActionType.UPDATE_TASK


def test_graph_compiles_as_a_real_compiled_state_graph():
    graph = build_tasks_agent_graph()
    assert type(graph).__name__ == "CompiledStateGraph"


async def test_graph_invocation_produces_a_real_proposal():
    graph = build_tasks_agent_graph()
    state: TasksAgentState = {
        "title": "Prep interview",
        "estimated_hours": 3.0,
        "deadline": None,
        "existing_task_id": None,
        "proposal": None,
    }
    result = await graph.ainvoke(state)
    assert result["proposal"].action_type == ActionType.CREATE_TASK


def test_task_actions_correctly_route_via_the_real_router():
    # Real cross-session integration, same pattern as IMPL_14's stakes
    # proof -- both real task ActionTypes resolve through the actual
    # router, not just asserted from the schema alone.
    #
    # RESOLVED, a real, disclosed CRITICAL-tier review MEDIUM (DEC-172,
    # M2): `UPDATE_TASK` was bumped from `S1` to `S2` this session, for
    # genuine consistency with `UPDATE_BUDGET`'s own already-established
    # "an update of an existing row sits one stakes level above its
    # CREATE sibling" precedent -- see `router.py`'s own full reasoning.
    create = build_task_proposal("new task", 1.0)
    update = build_task_proposal("existing task", 1.0, existing_task_id="t1")
    assert get_stakes(create.action_type) == Stakes.S1
    assert get_stakes(update.action_type) == Stakes.S2


def test_tasks_domain_does_not_overlap_with_any_prior_domain():
    tasks_tools = DOMAIN_TOOL_MAP["tasks"]
    for other in ("email", "calendar"):
        overlap = DOMAIN_TOOL_MAP[other] & tasks_tools
        assert not overlap, f"{other} vs tasks overlap: {overlap}"
