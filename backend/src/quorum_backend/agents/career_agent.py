"""Fifth and final real, compiled LangGraph node -- and the first genuinely
branching graph in this project. Same construction-not-copy pattern as
every agent this batch, held to the same rigor regardless.

Inherits, without re-deriving: the "agents propose, Gate verifies" boundary
from DEC-013 -- this agent has no detection pipeline of its own;
is_interview_detected and search_findings arrive as already-resolved
state, per the ADD's explicit design (Career rides on Email's ingestion).

Two real nodes, not one, because this domain's job genuinely branches --
see this session's report for why. update_status ALWAYS runs; compile_digest
runs ONLY when a real interview has been detected AND real search findings
have actually returned -- the exact edge case (detected before findings
arrive) is proven separately, not assumed to be the same as "not detected."
"""
from __future__ import annotations

import re
from typing import Awaitable, Callable, TypedDict

from langgraph.graph import END, StateGraph

from quorum_backend.agents.tool_authorization import authorize_tool_call
from quorum_backend.gate.schemas import ActionProposal, ActionType

CompileDigestCall = Callable[[str, list[str]], Awaitable[dict]]

# REAL, DISCLOSED FIX (`DEC-183`) -- see `_normalize_application_status()`'s
# own docstring below for the full account. Module-level and precompiled,
# matching this codebase's own established convention for a named regex
# used more than once conceptually (e.g. `action_executor.py`'s own
# precompiled patterns), rather than an inline literal re-compiled on
# every real call.
_APPLICATION_STATUS_SEPARATOR_PATTERN = re.compile(r"[\s_-]+")


class InvalidApplicationStatusError(ValueError):
    """Raised when a real, extracted status genuinely has no real content
    left once normalized (e.g. `"---"`, `"   "`) -- a real, disclosed
    edge case a standard-tier review found the first version of this fix
    missed (`DEC-183`'s own review-fix round)."""


def _normalize_application_status(raw: str) -> str:
    """REAL, DISCLOSED FIX (`DEC-183`), found live during `QUORUM_
    PRODUCTION_READINESS_AUDIT_PLAN.md`'s own on-device confirmation
    pass, not a hypothetical: a real quick-capture update ("Mark the
    Stripe application as interview scheduled") had a real Gemini
    extraction return `new_status = "interview scheduled"` (a space) --
    a real, genuinely different string from this project's own
    established canonical snake_case convention (`interview_scheduled`,
    the value the real seed dataset and `career_pipeline_logic.dart`'s
    own `knownStatusOrder` both use). Stored verbatim, that produced a
    real, live, confirmed bug: `career_pipeline_logic.dart::groupByStatus`
    groups by EXACT raw status-string equality, so the real Career
    Pipeline screen silently split one real status into two identically-
    displayed, duplicate-looking "Interview scheduled" groups of one
    application each, confirmed directly against the real, live
    Supabase row (`Notion` stored `'interview_scheduled'`, `Stripe`
    stored `'interview scheduled'`) rather than assumed from the
    screenshot alone.

    **Lives here, in `build_status_update_proposal()`'s own module, not
    in `features/quick_capture.py`'s call site** -- a real, disclosed
    correction from this fix's own standard-tier review: the original
    version normalized only at the one quick-capture call site, leaving
    this graph's own `make_update_status_node()` (below) -- a real,
    structural second path onto the identical `UPDATE_APPLICATION_
    STATUS` proposal, currently uncalled in production but a real
    bypass nonetheless, not a caller-discipline guarantee -- to persist
    an unnormalized status if it were ever wired up. Normalizing inside
    this one, real, shared funnel closes it for every real (and future)
    caller at once.

    `applications.status` remains genuinely, deliberately open-
    vocabulary (`CLAUDE.md`'s own architecture fact -- no database
    `CHECK` constraint, parsed defensively everywhere) -- this function
    does NOT reject or invent a status, it only makes different real
    phrasings of the SAME real status collapse onto one consistent
    stored form: lowercased, with any run of whitespace, hyphens, or
    underscores collapsed to a single underscore, then any leading/
    trailing underscore stripped -- matching the exact convention every
    existing real status value in this schema already uses. A genuinely
    novel status the model extracts (e.g. "phone screen") is still
    preserved, just canonicalized (`phone_screen`), never dropped or
    rewritten into a hardcoded enum. A pure, deterministic code
    transform, not a second LLM call -- `CLAUDE.md`'s own drift pattern
    #1 (never reach for a model to do something checkable in code).

    **A second real, disclosed edge case this same review found and this
    version now closes:** stripping only whitespace (not a leading/
    trailing hyphen) before substitution let `"- Interview Scheduled"`
    collapse to `"_interview_scheduled"` rather than the canonical
    `"interview_scheduled"` -- a leading separator survived as a leading
    underscore. Fixed by stripping leading/trailing underscores from the
    result, not just leading/trailing whitespace from the input. A
    genuinely degenerate input (e.g. `"---"`, all separator characters)
    now normalizes to the empty string and is rejected explicitly via
    `InvalidApplicationStatusError`, rather than silently persisting a
    real, meaningless `"_"` status -- callers that want a friendlier,
    typed translation error (matching their own existing exception
    vocabulary) should catch this alongside `ValueError` generally,
    which it already subclasses."""
    normalized = _APPLICATION_STATUS_SEPARATOR_PATTERN.sub("_", raw.strip().lower()).strip("_")
    if not normalized:
        raise InvalidApplicationStatusError(f"Status {raw!r} normalizes to an empty, degenerate value.")
    return normalized


class CareerAgentState(TypedDict):
    application_id: str
    company: str
    new_status: str
    is_interview_detected: bool
    search_findings: list[str] | None
    status_proposal: ActionProposal | None
    digest: dict | None


def build_status_update_proposal(application_id: str, new_status: str, company: str | None = None) -> ActionProposal:
    """`company` is optional, real DISPLAY-ONLY context
    (`QUORUM_FINAL_COMPLETION_PLAN.md` Session 6, matching `tasks_agent
    .py::build_task_deletion_proposal()`'s own identical real reasoning)
    -- `action_executor.py`'s own real `UPDATE_APPLICATION_STATUS`
    branch only ever reads `application_id`/`status`.

    `new_status` is normalized (`_normalize_application_status()`, see
    its own docstring for the full, real account -- `DEC-183`) before it
    ever reaches the stored payload -- the one, real, shared point every
    caller of this function passes through, deliberately, so a real
    caller can never bypass it by calling this function directly instead
    of going through `features/quick_capture.py`'s own resolution path."""
    authorize_tool_call("career.update_application_status", calling_agent_domain="career")
    return ActionProposal(
        action_type=ActionType.UPDATE_APPLICATION_STATUS,
        payload={"application_id": application_id, "status": _normalize_application_status(new_status), "company": company},
    )


def make_update_status_node():
    def update_status_node(state: CareerAgentState) -> dict:
        proposal = build_status_update_proposal(state["application_id"], state["new_status"])
        return {"status_proposal": proposal}

    return update_status_node


def make_compile_digest_node(compile_digest_call: CompileDigestCall):
    """Factory -- compile_digest_call (the real search/LLM-backed
    compilation) is injected, never imported or called by name directly,
    same discipline as email_agent.py's llm_call."""

    async def compile_digest_node(state: CareerAgentState) -> dict:
        digest = await compile_digest_call(state["company"], state["search_findings"] or [])
        return {"digest": digest}

    return compile_digest_node


def route_after_status_update(state: CareerAgentState) -> str:
    """Real conditional routing, not a hardcoded single path: proceeds to
    digest compilation only when BOTH a real interview is detected AND
    real search findings have actually returned -- detection alone is not
    enough, since the two events don't happen simultaneously."""
    if state.get("is_interview_detected") and state.get("search_findings"):
        return "compile_digest"
    return END


def build_career_agent_graph(compile_digest_call: CompileDigestCall):
    graph = StateGraph(CareerAgentState)
    graph.add_node("update_status", make_update_status_node())
    graph.add_node("compile_digest", make_compile_digest_node(compile_digest_call))
    graph.set_entry_point("update_status")
    graph.add_conditional_edges(
        "update_status", route_after_status_update, {"compile_digest": "compile_digest", END: END}
    )
    graph.add_edge("compile_digest", END)
    return graph.compile()
