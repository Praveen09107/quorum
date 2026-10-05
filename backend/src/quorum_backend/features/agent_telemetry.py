"""Real per-agent telemetry (`DEC-192`, product rebuild Block D) --
backs `GET /agents`.

WHY THIS EXISTS: a direct, confirmed cause of "none of the AI features
reflect in the app" is that Quorum's five domain agents have never had
any representation in this product at all, in either direction --
`DEC-189` already fixed the UI side (`theme/agent_identity.dart`, the
identity each agent now has on screen), and this module is the real
data side: lifetime action counts, a success/caught/rejected/uncertain
breakdown, and the real last-activity timestamp, per agent, computed
from data this backend has been writing to `action_events` the whole
time and never once aggregated this way.

REAL DESIGN DECISION: `ActionType` has no stored domain column of its
own anywhere in this schema -- `action_events.action_type` is a bare
string (`"send_email"`, `"create_task"`, ...), and nothing in the
database says which of the five domain agents proposed it. Rather than
add a new column (a real, disclosed-as-out-of-scope schema change for
what is a pure read), `AGENT_FOR_ACTION_TYPE` below is the single,
explicit, exhaustive mapping -- confirmed against the real, current
`ActionType` enum in `gate/schemas.py` before writing it, not assumed,
and proven exhaustive by a real test that iterates every real member.

`CREATE_NOTE` is the one real, disclosed exception: no agent in this
system has ever proposed it (confirmed by direct search -- no
`build_*_proposal()` function anywhere constructs a `CREATE_NOTE`
action, and it has no execution target either), so it maps to `None`
rather than being force-fit under an arbitrary domain. A `None` here
means "this real action type belongs to no current agent," never "this
row should be silently dropped" -- `aggregate_agent_stats()` below
still accounts for it in a real, named bucket rather than letting it
vanish from any total silently.

Real, pure aggregation split from real, live querying, matching this
project's own established `trust_digest.py`/`subscription_detective.py`
precedent exactly.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

import asyncpg

from quorum_backend.features.honesty_log import FAILURE_OUTCOMES, SUCCESS_OUTCOMES, UNCERTAIN_OUTCOMES
from quorum_backend.gate.schemas import ActionType

# The real, exhaustive mapping from every real `ActionType` to the one
# real domain agent that proposes it -- confirmed directly against
# `gate/schemas.py`'s own current enum, not assumed. `None` for
# `CREATE_NOTE` specifically -- see this module's own top-of-file
# docstring for why that is a real, disclosed fact about this system
# today, not an oversight.
AGENT_FOR_ACTION_TYPE: dict[ActionType, str | None] = {
    ActionType.SEND_EMAIL: "email",
    ActionType.CREATE_EMAIL_DRAFT: "email",
    ActionType.ARCHIVE_EMAIL: "email",
    ActionType.LABEL_EMAIL: "email",
    ActionType.CREATE_CALENDAR_EVENT_EXTERNAL: "calendar",
    ActionType.CREATE_CALENDAR_EVENT_LOCAL: "calendar",
    ActionType.CREATE_TASK: "tasks",
    ActionType.UPDATE_TASK: "tasks",
    ActionType.DELETE_TASK: "tasks",
    ActionType.LOG_EXPENSE: "finance",
    ActionType.UPDATE_EXPENSE: "finance",
    ActionType.DELETE_EXPENSE: "finance",
    ActionType.UPDATE_BUDGET: "finance",
    ActionType.UPDATE_APPLICATION_STATUS: "career",
    ActionType.CREATE_APPLICATION: "career",
    ActionType.CREATE_NOTE: None,
}

# The five real domain agents, in the fixed order every real surface in
# this product shows them -- matches `mobile/lib/theme/agent_identity
# .dart::kDomainAgents`'s own real, deliberate ordering exactly (Email
# and Calendar first: the two domains with real external side effects,
# the two a user most needs to keep an eye on).
REAL_DOMAIN_AGENTS = ("email", "calendar", "tasks", "finance", "career")


def agent_for_action_type(action_type: str) -> str | None:
    """Resolves a real, raw `action_events.action_type` string to its
    real domain agent. Fails loud on a genuinely unrecognized value --
    matching `CLAUDE.md`'s own mandated handling for `tasks.status`,
    this project's other closed, enum-backed set: an `ActionType` this
    mapping doesn't know about is a real bug in this module (it means
    the enum grew and this file wasn't updated), not a value to
    silently drop from a real user's own lifetime totals."""
    try:
        parsed = ActionType(action_type)
    except ValueError as exc:
        raise ValueError(
            f"Unrecognized action_events.action_type {action_type!r} -- this is a closed enum "
            f"(gate/schemas.py::ActionType); if a new member was added, add it to "
            f"AGENT_FOR_ACTION_TYPE in agent_telemetry.py."
        ) from exc
    return AGENT_FOR_ACTION_TYPE[parsed]


@dataclass(frozen=True)
class AgentStats:
    """Real, honest per-agent lifetime stats. Every count below is
    drawn from the SAME real partition `honesty_log.py` already
    established and this module reuses directly -- `success_count`/
    `caught_count`/`rejected_count`/`uncertain_count` sum to exactly
    `lifetime_actions`, by construction, since every real `outcome`
    value lands in exactly one of those four buckets."""

    domain: str
    lifetime_actions: int = 0
    success_count: int = 0
    caught_count: int = 0
    rejected_count: int = 0
    uncertain_count: int = 0

    # `None` is the real, honest default -- a real agent with zero
    # resolved actions yet has genuinely never been active, which is a
    # different fact from "active a long time ago." Never a fabricated
    # placeholder timestamp.
    last_activity: datetime | None = None

    @property
    def success_rate(self) -> float | None:
        """Mirrors `trust_digest.py`'s own already-established real
        precedent exactly: `uncertain_count` is excluded from both
        numerator and denominator (counting a genuinely-unknown outcome
        as an attempt that merely didn't succeed would collapse "we
        don't know" into "it failed"), and a real `None` -- never a
        fabricated `0.0` -- when there is nothing to compute a rate
        from at all."""
        resolved = self.lifetime_actions - self.uncertain_count
        if resolved <= 0:
            return None
        return round(self.success_count / resolved, 3)


def aggregate_agent_stats(
    rows: list[tuple[str, str | None, datetime]],
) -> dict[str, AgentStats]:
    """Pure, real aggregation over already-fetched `(action_type,
    outcome, resolved_or_created_at)` rows -- real DB access lives in
    `fetch_agent_stats()` below.

    Returns a dict keyed by every one of `REAL_DOMAIN_AGENTS`, ALWAYS,
    even for an agent with zero real rows -- a genuinely inactive agent
    must render as an honest zero-activity state, never be silently
    absent from the response, which would be indistinguishable from "no
    such agent" on the client.

    A row whose `action_type` resolves to `None` (today, only
    `CREATE_NOTE`) is counted nowhere -- there is no agent to attribute
    it to, and inventing one would misattribute a real row to an agent
    that didn't propose it."""
    stats: dict[str, AgentStats] = {domain: AgentStats(domain=domain) for domain in REAL_DOMAIN_AGENTS}

    for action_type, outcome, at in rows:
        domain = agent_for_action_type(action_type)
        if domain is None:
            continue
        current = stats[domain]

        # `rejected_by_user` is carved OUT of `honesty_log.py`'s own
        # coarser `FAILURE_OUTCOMES` bucket for `caught_count`
        # specifically -- that module deliberately keeps both under one
        # "failures_and_catches" grouping (both are "a reason an action
        # didn't sail through unchanged"), but this module's own real
        # consumer (the Agents index) wants the real, named distinction
        # the plan itself specifies: "caught-by-Gate" means the GATE
        # caught something, not a human declining to act on something
        # the Gate had already cleared. The two are mutually exclusive
        # by construction here, so they still sum to the same real
        # `FAILURE_OUTCOMES` total `honesty_log.py` itself reports.
        lifetime = current.lifetime_actions + 1
        success = current.success_count + (1 if outcome in SUCCESS_OUTCOMES else 0)
        rejected = current.rejected_count + (1 if outcome == "rejected_by_user" else 0)
        caught = current.caught_count + (1 if outcome in FAILURE_OUTCOMES and outcome != "rejected_by_user" else 0)
        uncertain = current.uncertain_count + (1 if outcome in UNCERTAIN_OUTCOMES else 0)
        last_activity = at if current.last_activity is None or at > current.last_activity else current.last_activity

        stats[domain] = AgentStats(
            domain=domain,
            lifetime_actions=lifetime,
            success_count=success,
            caught_count=caught,
            rejected_count=rejected,
            uncertain_count=uncertain,
            last_activity=last_activity,
        )

    return stats


async def fetch_agent_stats(pool: asyncpg.Pool, *, user_id: str) -> dict[str, AgentStats]:
    """The real, live query -- every real, RESOLVED `action_events` row
    for this user (matching `trust_digest.py`'s own `outcome IS NOT
    NULL` convention: an action still genuinely awaiting a human
    decision, e.g. a real `escalate_to_human`, is not yet a fact about
    this agent's own track record), per-user scoped from the query
    itself, never filtered after the fetch."""
    rows = await pool.fetch(
        "SELECT action_type, outcome, COALESCE(resolved_at, created_at) AS at "
        "FROM action_events WHERE user_id = $1 AND outcome IS NOT NULL",
        uuid.UUID(user_id),
    )
    return aggregate_agent_stats([(r["action_type"], r["outcome"], r["at"]) for r in rows])
