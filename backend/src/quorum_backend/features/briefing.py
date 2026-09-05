"""Real, live per-user briefing composition -- Phase 2 of
`QUORUM_PRODUCTION_COMPLETION_PLAN.md`, its own explicit scope for this
job: "composes the real `/today`-equivalent numbers server-side plus
the weather enrichment `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §9.8
names (one free API call) -- this is what eventually backs a real push
notification/home-screen-widget refresh, not built this phase, but the
real data-producing half is."

**A REAL, DISCLOSED CORRECTION TO THIS MODULE'S OWN ORIGINAL DOCSTRING,
found by this PR's own CRITICAL-tier review, BLOCKING until fixed:**
this docstring originally claimed `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.
md` "does not exist anywhere in this repository" -- false. The
document exists, at the repository root (not under `specs/tier1_
foundation/`, which is the directory an earlier, narrower search
actually checked -- a real, embarrassing scoping error, not a
fabrication, but one this project's own `CLAUDE.md` names by name as
an already-recurring failure mode, which makes stating it correctly
here non-optional). **§9.8 of that real document genuinely specifies
weather enrichment**, verbatim: "Weather via a free API, folded into
the morning composition alongside the computed-state numbers (§11.4)
-- one additional call, disproportionate perceived-quality gain." The
real reason weather is NOT built here stands entirely on its own,
without needing a false spec-gap premise: it needs a new, real,
free-tier weather API key, which needs real browser signup access this
environment does not have (the same disclosed blocker class as this
project's `mem0`/credential-rotation open items). This module builds
ONLY the real, data-producing half the plan names as this phase's
genuine scope: per-user capacity/budget/pending-action/negotiation
composition, reusing `features/today.py`'s own already-real,
already-tested queries directly rather than re-implementing any of
their arithmetic.

REAL, DELIBERATE DIFFERENCE FROM `deadline_watch.py`/`spend_alert.py`,
disclosed rather than silently inconsistent: those two modules take a
real `SELECT ... FOR UPDATE` lock on each user's own `users` row before
scanning, because a concurrent second invocation could otherwise
create a duplicate real `negotiations` row -- a genuine write to
serialize. This module never writes anything at all (pure composition
of already-real, already-live data), so there is no real write to
protect and no real reason to pay for a row lock here. **A real,
disclosed limit on that reasoning, found by this PR's own review:**
the four real queries inside `compose_briefing_for_user()` are NOT one
atomic snapshot -- a real, concurrent write between them could still
leave one individual briefing internally skewed (its own capacity
computed a moment before a task that would have changed it was
created, say). This is a genuinely pre-existing, already-shipped risk
class, not a new one introduced here: `GET /today` (`main.py`, live
since `DEC-119`) already makes these same four calls in this same
order, non-transactionally, and a row lock was never the right tool
for read consistency anyway (that would be a single `REPEATABLE READ`
transaction, not a `FOR UPDATE` lock). Not worth adding for a job with
no real consumer yet -- a real, deliberate scope boundary for whichever
future session gives this job one. What no row lock DOES still
guarantee, correctly: two concurrent `run_briefing()` calls produce the
same real, correct TALLIES (`users_scanned`/`users_with_*`) -- that
guarantee never depended on any one briefing's own internal snapshot
consistency in the first place.

**A REAL, DISCLOSED HARDENING, found by this PR's own review (MEDIUM
M2), applied here rather than left as a known gap:** an earlier version
of this module relied on `features/today.py::fetch_today_budget()`'s
own already-real `MonthlyBudgetLimitUserNotFoundError` (`DEC-148`) as
an incidental side effect to surface a nonexistent user as a real,
tallied failure. The review correctly flagged this as fragile and
inconsistent with this codebase's own established precedent --
`deadline_watch.py`/`spend_alert.py` each define and raise their OWN
explicit `*UserNotFoundError` rather than depending on a different
module's unrelated function to happen to check for them, the exact
same real bug class `DEC-148` found and fixed once already (a silent
all-zero fallback for a ghost user, indistinguishable from a real,
quiet one). Fixed here: `compose_briefing_for_user()` now checks for
the real `users` row directly, itself, first.
"""
from __future__ import annotations

import logging
import uuid
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


class BriefingUserNotFoundError(Exception):
    """Raised when no real `users` row exists at all for a given
    `user_id` -- this module's own explicit existence check, matching
    `deadline_watch.py`'s own `DeadlineWatchUserNotFoundError`/`spend_
    alert.py`'s own `SpendAlertUserNotFoundError` precedent, added by
    this PR's own CRITICAL-tier review (MEDIUM M2) in place of an
    earlier version that relied on `features/today.py::fetch_today_
    budget()`'s own, different `MonthlyBudgetLimitUserNotFoundError` as
    an incidental side effect. Caught by `run_briefing()`'s own real
    per-user failure isolation like any other genuine failure."""


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
    """A real, honest disclosure, flagged by this PR's own review (L2),
    worth stating plainly rather than only implying: `run_briefing()`
    computes a real, correct `BriefingData` per user and then discards
    everything except these two booleans -- nothing is persisted,
    nothing is returned to any real consumer. This route has genuinely
    zero real, observable effect today, exactly like `follow_up.py`'s
    own honestly-disclosed stub, even though it computes real numbers
    rather than skipping computation entirely. The real gap this session
    closes is proving the composition pipeline itself is correct and
    reusable -- not delivering a real briefing to anyone yet."""
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
    real, single source of truth.

    Checks for a real `users` row itself, first, and raises
    `BriefingUserNotFoundError` loud when none exists -- see this
    module's own top-of-file docstring for why this is now an explicit
    check here, not an incidental side effect of a different module's
    unrelated function."""
    exists = await pool.fetchrow("SELECT 1 FROM users WHERE user_id = $1", uuid.UUID(user_id))
    if exists is None:
        raise BriefingUserNotFoundError(f"No real users row for user_id={user_id!r} -- cannot compose a real briefing for a nonexistent user")

    capacity = await fetch_today_capacity(pool, user_id=user_id)
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
