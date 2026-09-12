"""Real tests for agents/career_agent.py -- the fifth and final domain
agent, the first genuinely branching graph, and the full, complete
5-domain exhaustive authorization matrix proof."""
import pytest

from quorum_backend.agents.career_agent import (
    CareerAgentState,
    InvalidApplicationStatusError,
    _normalize_application_status,
    build_career_agent_graph,
    build_status_update_proposal,
    make_compile_digest_node,
    make_update_status_node,
    route_after_status_update,
)
from quorum_backend.agents.tool_authorization import (
    DOMAIN_TOOL_MAP,
    authorize_tool_call,
    ToolAuthorizationError,
)
from quorum_backend.gate.schemas import ActionType


async def _fake_digest_call(company: str, findings: list[str]) -> dict:
    return {"company": company, "summary_points": findings[:3]}


def test_status_update_always_produces_update_application_status():
    proposal = build_status_update_proposal("app_1", "interview_scheduled")
    assert proposal.action_type == ActionType.UPDATE_APPLICATION_STATUS


# --- `_normalize_application_status` / `build_status_update_proposal`'s
# own real, live normalization (`DEC-183`) ---


def test_normalize_application_status_replaces_spaces_and_lowercases():
    assert _normalize_application_status("Interview Scheduled") == "interview_scheduled"


def test_normalize_application_status_collapses_hyphens_and_repeated_whitespace_too():
    assert _normalize_application_status("Phone -  Screen") == "phone_screen"


def test_normalize_application_status_leaves_an_already_canonical_value_unchanged():
    assert _normalize_application_status("interview_scheduled") == "interview_scheduled"


def test_normalize_application_status_strips_leading_and_trailing_whitespace():
    assert _normalize_application_status("  rejected  ") == "rejected"


def test_normalize_application_status_strips_a_real_leading_separator_too():
    # REAL, DISCLOSED FIX, found by this fix's own standard-tier review:
    # `raw.strip()` alone only strips whitespace, not a leading/trailing
    # hyphen -- "- Interview Scheduled" previously normalized to the
    # wrong `"_interview_scheduled"` (a stray leading underscore) instead
    # of genuinely matching the canonical form.
    assert _normalize_application_status("- Interview Scheduled") == "interview_scheduled"


def test_normalize_application_status_raises_on_a_genuinely_degenerate_all_separator_input():
    # REAL, DISCLOSED FIX, found by the same review: an all-separator
    # input (e.g. "---") previously normalized to the meaningless stored
    # value `"_"` instead of being rejected.
    with pytest.raises(InvalidApplicationStatusError):
        _normalize_application_status("---")
    with pytest.raises(InvalidApplicationStatusError):
        _normalize_application_status("   ")


def test_build_status_update_proposal_normalizes_the_stored_payload_status():
    proposal = build_status_update_proposal("app_1", "Interview Scheduled")
    assert proposal.payload["status"] == "interview_scheduled"


def test_build_status_update_proposal_raises_on_a_genuinely_degenerate_status():
    # Closes the real, structural gap this fix's own review found: this
    # function is the one real, shared funnel every caller (quick-capture
    # AND this graph's own `make_update_status_node`) goes through -- a
    # degenerate status must be rejected here, not only at one call site.
    with pytest.raises(InvalidApplicationStatusError):
        build_status_update_proposal("app_1", "---")


async def test_real_graph_compiles_digest_when_interview_detected_with_findings():
    graph = build_career_agent_graph(_fake_digest_call)
    state: CareerAgentState = {
        "application_id": "app_1",
        "company": "Notion",
        "new_status": "interview_scheduled",
        "is_interview_detected": True,
        "search_findings": ["Raised a Series C round in 2021."],
        "status_proposal": None,
        "digest": None,
    }
    result = await graph.ainvoke(state)
    assert result["status_proposal"].action_type == ActionType.UPDATE_APPLICATION_STATUS
    assert result["digest"] is not None
    assert result["digest"]["company"] == "Notion"


async def test_real_graph_skips_digest_when_no_interview_detected():
    graph = build_career_agent_graph(_fake_digest_call)
    state: CareerAgentState = {
        "application_id": "app_1",
        "company": "Notion",
        "new_status": "applied",
        "is_interview_detected": False,
        "search_findings": None,
        "status_proposal": None,
        "digest": None,
    }
    result = await graph.ainvoke(state)
    assert result["status_proposal"] is not None
    assert result["digest"] is None


async def test_real_graph_skips_digest_when_interview_detected_but_no_findings_yet():
    # The real edge case: detection and search are two separate real steps
    # that can complete at different times. An interview flagged before its
    # digest search has returned must not compile from nothing.
    graph = build_career_agent_graph(_fake_digest_call)
    state: CareerAgentState = {
        "application_id": "app_1",
        "company": "Notion",
        "new_status": "interview_scheduled",
        "is_interview_detected": True,
        "search_findings": None,
        "status_proposal": None,
        "digest": None,
    }
    result = await graph.ainvoke(state)
    assert result["digest"] is None


def test_graph_compiles_as_a_real_compiled_state_graph():
    graph = build_career_agent_graph(_fake_digest_call)
    assert type(graph).__name__ == "CompiledStateGraph"


def test_route_after_status_update_returns_real_conditional_values():
    from langgraph.graph import END

    assert route_after_status_update(
        {"is_interview_detected": True, "search_findings": ["a finding"]}
    ) == "compile_digest"
    assert route_after_status_update({"is_interview_detected": False, "search_findings": None}) == END
    assert route_after_status_update({"is_interview_detected": True, "search_findings": None}) == END


def test_both_node_factories_are_real_and_independently_callable():
    update_node = make_update_status_node()
    digest_node = make_compile_digest_node(_fake_digest_call)
    assert callable(update_node)
    assert callable(digest_node)


def test_full_five_domain_authorization_matrix_holds():
    """The real, complete centerpiece proof of this batch -- re-run at
    full scope now that all five domains exist."""
    assert len(DOMAIN_TOOL_MAP) == 5, f"Expected exactly 5 domains, found {len(DOMAIN_TOOL_MAP)}: {sorted(DOMAIN_TOOL_MAP)}"

    total_checks = 0
    violations = 0
    for domain, allowed in DOMAIN_TOOL_MAP.items():
        for other, other_tools in DOMAIN_TOOL_MAP.items():
            if domain == other:
                continue
            for tool in other_tools:
                if tool in allowed:
                    continue
                total_checks += 1
                try:
                    authorize_tool_call(tool, calling_agent_domain=domain)
                    violations += 1
                except ToolAuthorizationError:
                    pass
    assert total_checks > 0
    assert violations == 0, f"{violations} real authorization violations found"
