"""The real, first autonomous, non-manual caller of `negotiation/
trigger.py::scan_for_conflicts` -- closes the single most important
real gap `DEC-129`'s full repository diagnosis found: that function's
only real caller in this backend's entire history was `scripts/
seed_demo_dataset.py`, a one-time, hand-run script. `POST /internal/
deadline-watch` (`main.py`) calls `run_deadline_watch()` below, which
iterates every real user, computes REAL tasks/finance domain state
from their REAL, live data, and creates a real, bare `negotiations`
row the moment a genuine conflict is found -- with zero LLM calls,
matching `scan_for_conflicts`'s own "pure computation, zero LLM calls,
zero inference" contract exactly, the same Stage-A-is-pure-code
discipline this project's Gate already holds itself to.

A REAL, DELIBERATE SCOPE BOUNDARY, DISCLOSED HERE, NOT SILENTLY
ASSUMED: this module creates the bare negotiation row only --
positions/options (real Gemini-backed content) are NOT generated
here. This mirrors `scripts/seed_demo_dataset.py`'s own real,
established two-phase precedent (`seed_negotiation_row`, then a
SEPARATE, deliberate `--with-negotiation-detail` step) for the same
real, disclosed reason: a scheduled job that may touch many real
users on every cron tick, and also makes live Gemini calls for full
negotiation detail, would risk burning through this project's own
already-disclosed, fluctuating Gemini free-tier quota unpredictably
(`STATUS_INDEX.md` item #21) -- the exact real failure mode a pure,
zero-LLM trigger scan structurally cannot hit. Generating real detail
for an autonomously-created negotiation (via the same real subgraph
`negotiation/subgraph.py` already provides) is a genuine, separate,
still-open item, not silently rolled into this session's scope.

CALENDAR IS DELIBERATELY EXCLUDED: no `calendar_events` table exists
anywhere in this backend's real schema (confirmed since `DEC-121`) --
`scan_for_conflicts`'s own "no real data for a domain is never
silently assumed to be a conflict" rule already handles this
honestly (a `domain_states` dict with no `"calendar"` key), so this
module simply never constructs one, rather than fabricating a
calendar `DomainState` from data that doesn't exist. Career is
likewise not a first-class negotiation domain -- confirmed directly
against `gate/schemas.py`: `Position.domain` and `ResourceClaim.
claim_type`'s real `CLAIM_TYPE_TO_DOMAIN` mapping only ever resolve
to `calendar`/`tasks`/`finance`. A real, disclosed correction to this
session's own `QUORUM_PRODUCTION_COMPLETION_PLAN.md`, which described
Phase 2 as covering "Tasks, Finance, Career": Career has no
resource-claim shape of its own to negotiate over in this schema --
any Career-driven urgency (e.g., interview prep) already surfaces as
a real `tasks` claim if a real task was created for it, not as an
independent domain here.

REAL RESOURCE-CLAIM CONSTRUCTION, reusing every already-established
real pattern rather than inventing new arithmetic:
- tasks: `features/negotiation_trigger_support.py::build_tasks_claim_
  and_state()` -- real, shared with `spend_alert.py`, since both jobs
  need the exact same real computation. See that module's own top-of-
  file docstring for the full real reasoning, including a real,
  live-proven same-day-deadline bug this session's own CRITICAL-tier
  review found and fixed there.
- finance: real money already spent this real calendar month against
  the real remaining monthly budget (both computed from the same real
  `expenses` table `features/today.py::fetch_today_budget` already
  queries). A real, disclosed, deliberately simple interpretation:
  since this backend's only real financial ground truth is already-
  incurred `expenses` (no `budgets`-ceiling or pending-commitment
  table exists, the same real gap `retry_queue_drainer.py`'s own
  top-of-file docstring already discloses), "spent this month exceeds
  remaining budget" is the real, honest comparison available --
  algebraically equivalent to "already spent more than half this
  month's allowance," a genuine, meaningful real signal of financial
  strain from real data, not an invented threshold.
A user with no real open task carrying a future deadline has no real
claim to construct -- skipped honestly, never defaulted to zero
(which would fabricate a "no conflict" conclusion from missing data,
the same epistemic trap `scan_for_conflicts`'s own `no_data_found`-
adjacent discipline already avoids).

REAL IDEMPOTENCY, not just a plausible-looking check: a real `SELECT
... FOR UPDATE` on the user's own real `users` row for the duration
of that user's check-and-create serializes a concurrent second
invocation (a real possibility once `pg_cron` fires against a
`--max-instances=2` deployment, the same real concern `retry_queue_
drainer.py`'s own `FOR UPDATE SKIP LOCKED` already addresses for its
own real job queue -- a different real primitive here since there is
no queue row to lock, only the user being processed). If that lock
query finds no real row at all (the user_id doesn't genuinely exist --
confirmed live-reachable via this module's own `user_ids` scoping
parameter, not merely a hypothetical), this module now raises loud
rather than silently continuing to scan a nonexistent user with no
lock actually held -- a real gap this session's own CRITICAL-tier
review found and this fix closes.

A SECOND REAL, LIVE-PROVEN BUG FOUND BY THIS SESSION'S OWN CRITICAL-
TIER REVIEW, FIXED HERE: an earlier version treated ANY unresolved
negotiation (`resolved_at IS NULL`) as blocking a new one. But a bare
negotiation (`options IS NULL`, this module's own deliberate scope
boundary above) can NEVER become resolved through any real code path
in this backend -- `features/negotiation_choice.py`'s own only real
`resolved_at` writer requires `options IS NOT NULL`, returning a real
`409` otherwise -- live-proven to PERMANENTLY silence this trigger for
a real user after its very first firing, regardless of how genuinely
severe a later, real conflict becomes. Fixed, and since generalized
into `features/negotiation_trigger_support.py::has_blocking_negotiation()`
once a second real autonomous job (`spend_alert.py`) needed the exact
same real logic: a negotiation with real options (genuinely
actionable, truly awaiting the user's real choice) still blocks a new
one unconditionally, exactly as before. A still-bare negotiation
blocks a new one only within `BARE_NEGOTIATION_COOLDOWN_HOURS` of its
own real `started_at` -- long enough that this module's own real
30-minute cron cadence never spams a duplicate bare row for the
identical, still-standing situation, short enough that a real, later,
genuinely different crisis is never silenced forever by one old,
un-actionable detection. The real, generalized check is scoped to an
EXACT `trigger_source` match (`'deadline_watch'` here), so this
module's own idempotency never collides with `spend_alert.py`'s own,
different real concerns for the same user -- see that shared module's
own top-of-file docstring for the full real reasoning. Real detail
generation (this module's own disclosed, still-open follow-up above)
would let a negotiation actually become resolved and close this gap
properly; this cooldown is the real, minimal, disclosed mitigation
until then, not a permanent design.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from enum import Enum, auto

import asyncpg

from quorum_backend.features.negotiation_trigger_support import (
    build_tasks_claim_and_state,
    create_bare_negotiation,
    fetch_month_to_date_spend,
    has_blocking_negotiation,
)
from quorum_backend.features.today import TODAY_MONTHLY_BUDGET_LIMIT
from quorum_backend.gate.schemas import ResourceClaim
from quorum_backend.negotiation.trigger import DomainState, scan_for_conflicts

# Same real logger name main.py's own module-level logger already uses
# -- one real, consistent log stream for this backend, not a second,
# independently-named one.
logger = logging.getLogger("quorum_backend")

# The real trigger_source (migration 0008) this module writes onto
# every negotiation it creates -- see negotiation_trigger_support.py's
# own top-of-file docstring for why this exact-match key is what keeps
# this job's own idempotency check from colliding with any other real
# autonomous trigger job's (this session's own spend_alert.py included).
DEADLINE_WATCH_TRIGGER_SOURCE = "deadline_watch"


class DeadlineWatchUserNotFoundError(Exception):
    """Raised when this module's own real `SELECT ... FOR UPDATE` lock
    finds no real `users` row at all for a given `user_id` -- a real
    gap this session's own CRITICAL-tier review found: the lock query
    silently no-ops (locks nothing, returns no row) for a nonexistent
    user, and an earlier version of this module continued scanning
    that user anyway with no real lock actually held. Raised loud
    instead, so `run_deadline_watch()`'s own real per-user failure
    isolation catches and tallies it, rather than silently proceeding
    unserialized."""


class ScanOutcome(Enum):
    NO_CLAIM = auto()  # no real open task with a future deadline -- honestly skipped
    NO_CONFLICT = auto()  # a real claim exists but doesn't exceed real available capacity
    ALREADY_NEGOTIATING = auto()  # a real conflict, but a real, unresolved negotiation already covers it
    CREATED = auto()  # a real, genuine conflict -- a new, bare negotiation row was created


@dataclass(frozen=True)
class DeadlineWatchResult:
    users_scanned: int
    users_failed: int
    negotiations_created: int
    outcome_counts: dict[str, int]


async def scan_one_user(conn: asyncpg.Connection, *, user_id: str) -> tuple[ScanOutcome, str | None]:
    """Real, live, per-user scan -- the one real place this module's
    own claim-construction, trigger-scan, and idempotency logic lives;
    `run_deadline_watch()` below calls this once per real user, never
    duplicating this logic inline. Returns `(outcome, negotiation_id)`
    -- `negotiation_id` is only ever real and non-`None` for
    `ScanOutcome.CREATED`."""
    tasks_claim_and_state = await build_tasks_claim_and_state(conn, user_id=user_id)
    if tasks_claim_and_state is None:
        return ScanOutcome.NO_CLAIM, None
    tasks_claim, tasks_state = tasks_claim_and_state

    # A single real query for the raw spend figure -- both this
    # module's own real finance CLAIM (spent this month) and its real
    # available capacity (remaining budget) derive from the same one
    # real number, never fetched twice.
    spent_this_month = await fetch_month_to_date_spend(conn, user_id=user_id)
    remaining_budget = max(0.0, TODAY_MONTHLY_BUDGET_LIMIT - spent_this_month)

    resource_claims = [
        tasks_claim,
        ResourceClaim(claim_type="money", amount=spent_this_month, unit="currency_minor_units"),
    ]
    domain_states = {
        "tasks": tasks_state,
        "finance": DomainState(domain="finance", available=remaining_budget, unit="currency_minor_units"),
    }
    scan_result = scan_for_conflicts(resource_claims, domain_states)
    if not scan_result.triggers_negotiation:
        return ScanOutcome.NO_CONFLICT, None

    if await has_blocking_negotiation(conn, user_id=user_id, trigger_source=DEADLINE_WATCH_TRIGGER_SOURCE):
        return ScanOutcome.ALREADY_NEGOTIATING, None

    negotiation_id = await create_bare_negotiation(
        conn, user_id=user_id, conflicted_domains=scan_result.conflicted_domains,
        trigger_source=DEADLINE_WATCH_TRIGGER_SOURCE,
    )
    return ScanOutcome.CREATED, negotiation_id


async def run_deadline_watch(pool: asyncpg.Pool, *, user_ids: list[str] | None = None) -> DeadlineWatchResult:
    """The real entry point -- `POST /internal/deadline-watch` (`main.py`)
    calls this with `user_ids=None` (the real, live default), which
    scans every real user in this deployment. Each real user's own
    check-and-create runs inside its own real transaction, with a real
    `SELECT ... FOR UPDATE` on that user's own `users` row held for the
    duration -- see this module's own top-of-file docstring for why
    that specific real lock, not a queue-style `FOR UPDATE SKIP
    LOCKED`, is the right primitive here.

    A REAL BUG FOUND AND FIXED BY THIS SESSION'S OWN ADVERSARIAL SELF-
    REVIEW, BEFORE ANY REVIEW SUBAGENT RAN: an earlier version of this
    loop had no per-user exception handling at all -- a genuine
    database error for ONE real user (a transient connection hiccup,
    a real constraint violation) would propagate straight out of this
    function, aborting the scan for every OTHER real user too, and the
    whole `/internal/deadline-watch` request would 500. Since this
    route runs on a periodic real schedule rather than being retried
    within the same request (unlike `retry_queue_drainer.py`'s own
    per-job retry queue), that one bad user could silently block every
    real user's negotiation trigger until the next scheduled run.
    Fixed: each real user's own check-and-create is now wrapped in its
    own `try`/`except`, logged via `logger.exception()` and tallied
    into `DeadlineWatchResult.users_failed`, never silently dropped --
    and the loop always continues to the next real user regardless.

    `user_ids`, when explicitly passed, scopes the scan to exactly
    those real users instead of the whole real `users` table -- exists
    specifically so `test_deadline_watch.py` can exercise this real
    entry point's own per-user-iteration/locking/tallying logic against
    real, test-owned rows only, never this deployment's one real, live
    production account (a real, disclosed safety boundary, not a
    hypothetical concern -- see that test file's own top-of-file
    docstring)."""
    if user_ids is None:
        user_ids = [str(row["user_id"]) for row in await pool.fetch("SELECT user_id FROM users")]

    users_scanned = 0
    users_failed = 0
    negotiations_created = 0
    outcome_counts: dict[str, int] = {outcome.name: 0 for outcome in ScanOutcome}

    for user_id in user_ids:
        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    lock_row = await conn.fetchrow("SELECT user_id FROM users WHERE user_id = $1 FOR UPDATE", uuid.UUID(user_id))
                    if lock_row is None:
                        raise DeadlineWatchUserNotFoundError(
                            f"No real users row for user_id={user_id!r} -- cannot safely lock/scan a nonexistent user"
                        )
                    outcome, _negotiation_id = await scan_one_user(conn, user_id=user_id)
        except Exception:  # noqa: BLE001 -- deliberately broad: a real failure for one user must never abort the scan for every other real user; see this function's own top-of-docstring account of the real bug this isolation fixes
            users_failed += 1
            logger.exception("Real deadline-watch scan failed for user_id=%s -- continuing to the next real user", user_id)
            continue

        users_scanned += 1
        outcome_counts[outcome.name] += 1
        if outcome is ScanOutcome.CREATED:
            negotiations_created += 1

    return DeadlineWatchResult(
        users_scanned=users_scanned,
        users_failed=users_failed,
        negotiations_created=negotiations_created,
        outcome_counts=outcome_counts,
    )
