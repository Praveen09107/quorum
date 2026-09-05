"""Real, live per-user briefing composition -- Phase 2 of
`QUORUM_PRODUCTION_COMPLETION_PLAN.md`, its own explicit scope for this
job: "composes the real `/today`-equivalent numbers server-side plus
the weather enrichment `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §9.8
names (one free API call) -- this is what eventually backs a real push
notification/home-screen-widget refresh, not built this phase, but the
real data-producing half is."

A REAL, DISCLOSED SPEC-CORPUS GAP, found before writing a line of this
module: `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` -- the document the
production plan's own text above cites for the weather-enrichment
detail -- does not exist anywhere in this repository's real
`specs/tier1_foundation/` directory (confirmed directly via a full
listing before this session started building anything against it, the
same "stale narrative describing a no-longer-accessible environment"
pattern `STATUS_INDEX.md` already discloses once at its own top).
Weather enrichment is therefore explicitly NOT built here -- it would
need a new, real, free-tier weather API key, which needs real browser
signup access this environment does not have (the same disclosed
blocker class as this project's `mem0`/credential-rotation open
items). This module builds ONLY the real, data-producing half the plan
names as this phase's genuine scope: per-user capacity/budget/pending-
action/negotiation composition, reusing `features/today.py`'s own
already-real, already-tested queries directly rather than
re-implementing any of their arithmetic.

REAL, DELIBERATE DIFFERENCE FROM `deadline_watch.py`/`spend_alert.py`,
disclosed rather than silently inconsistent: those two modules take a
real `SELECT ... FOR UPDATE` lock on each user's own `users` row before
scanning, because a concurrent second invocation could otherwise
create a duplicate real `negotiations` row -- a genuine write to
serialize. This module never writes anything at all (pure composition
of already-real, already-live data), so there is no real write to
protect and no real reason to pay for a row lock here; two concurrent
`run_briefing()` calls reading the same real data at the same real
moment produce the same real, correct answer independently, with no
need for mutual exclusion.

REAL, DELIBERATE RELIANCE ON AN ALREADY-EXISTING GUARANTEE, not a new
check invented here: `features/today.py::fetch_today_budget()` already
raises `MonthlyBudgetLimitUserNotFoundError` loud when no real `users`
row exists for a given `user_id` (`DEC-148`) -- `compose_briefing_for_
user()` below calls it as part of composing a real briefing, so a
`user_ids` scope naming a genuinely nonexistent user surfaces as a
real, tallied failure in `run_briefing()`'s own per-user isolation,
never as a silently-fabricated all-zero briefing. This module
deliberately does not duplicate that existence check itself -- one
real place already enforces it correctly.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import asyncpg

from quorum_backend.features.today import (
    BudgetState,
    CapacityState,
    fetch_active_negotiations,
    fetch_pending_actions,
    fetch_today_budget,
    fetch_today_capacity,
)

# Same real, shared logger name every other feature module in this
# backend already logs under -- one real, consistent log stream, not a
# second, independently-named one.
logger = logging.getLogger("quorum_backend")


@dataclass(frozen=True)
class BriefingData:
    """The real, composed per-user briefing -- exactly the four real
    numbers `GET /today` already serves this same user on demand,
    composed here so a future scheduled consumer (a real push
    notification, a real home-screen-widget refresh -- explicitly not
    built this phase, per this module's own top-of-file scope) has a
    single real function to call instead of re-deriving this
    composition itself."""
    user_id: str
    capacity: CapacityState
    budget: BudgetState
    pending_action_count: int
    active_negotiation_count: int


@dataclass(frozen=True)
class BriefingResult:
    users_scanned: int
    users_failed: int
    users_with_pending_actions: int
    users_with_active_negotiations: int


async def compose_briefing_for_user(pool: asyncpg.Pool, *, user_id: str) -> BriefingData:
    """Real, live composition for one real user -- the one place this
    module's own data-gathering lives; `run_briefing()` below calls
    this once per real user, never duplicating this logic inline.
    Every one of the four real queries below is already real, live,
    and independently tested by `features/today.py`'s own test suite;
    this function's only real job is composing their results into one
    `BriefingData`, the same "reuse, never re-derive" discipline this
    project holds itself to everywhere a real number already has a
    real, single source of truth."""
    capacity = await fetch_today_capacity(pool, user_id=user_id)
    # Real, deliberate ordering: `fetch_today_budget()` is what raises
    # `MonthlyBudgetLimitUserNotFoundError` loud for a genuinely
    # nonexistent user (see this module's own top-of-file docstring) --
    # called before the two list-fetches below so a nonexistent user
    # fails fast rather than after two real, wasted queries.
    budget = await fetch_today_budget(pool, user_id=user_id)
    pending_actions = await fetch_pending_actions(pool, user_id=user_id)
    active_negotiations = await fetch_active_negotiations(pool, user_id=user_id)
    return BriefingData(
        user_id=user_id,
        capacity=capacity,
        budget=budget,
        pending_action_count=len(pending_actions),
        active_negotiation_count=len(active_negotiations),
    )


async def run_briefing(pool: asyncpg.Pool, *, user_ids: list[str] | None = None) -> BriefingResult:
    """The real entry point -- `POST /internal/briefing` (`main.py`)
    calls this with `user_ids=None` (the real, live default), which
    composes a real briefing for every real user in this deployment.

    Matches `run_deadline_watch()`/`run_spend_alert()`'s own real, per-
    user failure isolation exactly, for the same real reason: this
    route is meant to run on a periodic real schedule (once real
    push-notification/widget delivery exists to consume it -- not
    built this phase), so one real user's own transient failure (a
    momentary database hiccup, or the genuinely-nonexistent-user case
    this module's own top-of-file docstring names) must never abort
    composition for every other real user in the same run.

    `user_ids`, when explicitly passed, scopes the run to exactly those
    real users instead of the whole real `users` table -- exists
    specifically so this module's own test suite can exercise this
    real entry point's own per-user-iteration/tallying logic against
    real, test-owned rows only, never this deployment's real,
    live production account."""
    if user_ids is None:
        user_ids = [str(row["user_id"]) for row in await pool.fetch("SELECT user_id FROM users")]

    users_scanned = 0
    users_failed = 0
    users_with_pending_actions = 0
    users_with_active_negotiations = 0

    for user_id in user_ids:
        try:
            data = await compose_briefing_for_user(pool, user_id=user_id)
        except Exception:  # noqa: BLE001 -- deliberately broad: a real failure composing one user's briefing must never abort the run for every other real user, the same real discipline `run_deadline_watch`/`run_spend_alert` already established
            users_failed += 1
            logger.exception("Real briefing composition failed for user_id=%s -- continuing to the next real user", user_id)
            continue

        users_scanned += 1
        if data.pending_action_count > 0:
            users_with_pending_actions += 1
        if data.active_negotiation_count > 0:
            users_with_active_negotiations += 1

    return BriefingResult(
        users_scanned=users_scanned,
        users_failed=users_failed,
        users_with_pending_actions=users_with_pending_actions,
        users_with_active_negotiations=users_with_active_negotiations,
    )
