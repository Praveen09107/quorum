"""Real, shared primitives for every real, autonomous negotiation-
trigger job (`features/deadline_watch.py`, `DEC-132`; this session's
own `features/spend_alert.py`) -- factored out here, not duplicated in
each, once a second real caller needed the exact same real logic
`deadline_watch.py` first built.

`trigger_source` (migration `0008_negotiation_trigger_source`) is what
makes the real, shared idempotency check PRECISE rather than a blunt,
cross-job instrument: a real, live, human-readable audit trail of
which autonomous job created a given negotiation (`'deadline_watch'`,
`'spend_alert'`), so one job's own real, unresolved BARE negotiation
never silently suppresses a genuinely different, unrelated real
concern another job would otherwise raise.

**A REAL, DISCLOSED CORRECTION, found by the CRITICAL-tier review of
this very module (the `spend_alert.py` PR, same session):** an earlier
version of `has_blocking_negotiation()` below required an EXACT
`trigger_source` match UNCONDITIONALLY -- including for a negotiation
that already carries real `options`. That silently regressed `DEC-132`'s
own, separately-proven guarantee ("a negotiation with real options
blocks unconditionally, full stop") down to "...blocks unconditionally,
but only from the same job" -- live-proven by the review to let
`deadline_watch` stack a fresh, un-actionable bare negotiation directly
on top of a real, already-actionable one the user hadn't gotten to yet
(reachable the moment `trigger_source` is `NULL` or a different job's,
e.g. any row `scripts/seed_demo_dataset.py --with-negotiation-detail`
writes, which never sets `trigger_source` at all). Fixed here: the
EXACT `trigger_source` match now applies ONLY to a still-bare
negotiation's own cooldown check (see below) -- a negotiation with
real `options`, from ANY source, still blocks a new one unconditionally,
exactly as `DEC-132` originally established.

BARE-NEGOTIATION COOLDOWN, not a permanent block: a bare negotiation
(no real, Gemini-backed `options` yet -- both real autonomous jobs'
own deliberate scope boundary) can never become resolved through any
real code path in this backend (`features/negotiation_choice.py`
requires real `options` to choose) -- `DEC-132`'s own CRITICAL-tier
review found this live-proven to permanently silence `deadline_watch.
py`'s trigger for a real user after its very first firing. `has_
blocking_negotiation()` carries that real, live-proven fix here too,
generalized: a negotiation with real `options` blocks unconditionally,
regardless of which job created it; a still-bare one blocks only
within a real, bounded `cooldown_hours` of its own `started_at`, AND
only when it shares this scan's own EXACT `trigger_source` -- a bare
negotiation from a genuinely different, unrelated autonomous job never
blocks a new one, the real reason `trigger_source` exists at all.

REAL, SHARED TASKS-DOMAIN CLAIM CONSTRUCTION: both `deadline_watch.py`
and `spend_alert.py` need the exact same real computation for "how
overcommitted is this user's real task schedule right now" -- real
committed effort hours due before the user's nearest real, open,
future task deadline (`retry_queue_drainer.py`'s own already-real
`fetch_committed_hours_before`) against real available working hours
before that same deadline. `available_hours_before_deadline_including_
today()` below is a real, corrected, module-local version of `retry_
queue_drainer.py`'s own `available_hours_before_deadline` -- that
function returns `0.0` for a same-day deadline, a real, reasonable
choice for ITS OWN use case (checking whether a NEW proposed task
safely fits before an EXISTING deadline), but `DEC-132`'s own CRITICAL-
tier review live-proved this wrong for a job proactively checking a
user's ALREADY-EXISTING commitments: a single 1-hour task due today,
on an otherwise free day, was found to trigger a false conflict,
directly contradicting `features/today.py::fetch_today_capacity`'s own
real answer for the identical data. This module's own version does NOT
change `retry_queue_drainer.py`'s own shared function or its own real,
already-passing tests, since that module's own zero-for-today choice
remains correct for its own, different scenario.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import asyncpg

from quorum_backend.features.retry_queue_drainer import fetch_committed_hours_before
from quorum_backend.features.subscription_detective import DetectedSubscription, detect_subscriptions
from quorum_backend.features.today import TODAY_WORKING_HOURS_PER_DAY, fetch_monthly_budget_limit
from quorum_backend.gate.schemas import ResourceClaim
from quorum_backend.negotiation.trigger import DomainState

# Same real, deliberately simple, disclosed choice `deadline_watch.py`
# first established (`DEC-132`) -- long enough that neither real job's
# own cron cadence (30 minutes) spams a duplicate bare negotiation for
# the identical, still-standing real situation; short enough that one
# old, un-actionable detection can never silence a real trigger for
# more than a real day.
BARE_NEGOTIATION_COOLDOWN_HOURS = 24


async def has_blocking_negotiation(
    conn: asyncpg.Connection, *, user_id: str, trigger_source: str, cooldown_hours: float = BARE_NEGOTIATION_COOLDOWN_HOURS
) -> bool:
    """Real, precise idempotency guard -- see this module's own top-of-
    file docstring for the real, disclosed correction this query
    represents: a negotiation with real `options` blocks unconditionally
    regardless of source; a still-bare one blocks only within
    `cooldown_hours` AND only when it shares this scan's own EXACT
    `trigger_source`."""
    row = await conn.fetchrow(
        "SELECT 1 FROM negotiations WHERE user_id = $1 AND resolved_at IS NULL "
        "AND (options IS NOT NULL OR (trigger_source = $2 AND started_at > now() - ($3 * INTERVAL '1 hour'))) "
        "LIMIT 1",
        uuid.UUID(user_id),
        trigger_source,
        cooldown_hours,
    )
    return row is not None


async def create_bare_negotiation(
    conn: asyncpg.Connection, *, user_id: str, conflicted_domains: list[str], trigger_source: str
) -> str:
    """Real, shared write -- a real, bare `negotiations` row (real
    `positions`/`options` intentionally NULL; see the calling module's
    own top-of-file docstring for why real detail-generation is a
    genuine, separate, still-open item, not silently rolled in here)."""
    negotiation_id = uuid.uuid4()
    await conn.execute(
        "INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at, trigger_source) "
        "VALUES ($1, $2, $3, $4, $5)",
        negotiation_id,
        uuid.UUID(user_id),
        conflicted_domains,
        datetime.now(timezone.utc),
        trigger_source,
    )
    return str(negotiation_id)


async def fetch_nearest_upcoming_task_deadline(conn: asyncpg.Connection, *, user_id: str) -> datetime | None:
    """The real user's nearest real, still-open, future task deadline --
    the reference point every real tasks-domain claim in this backend's
    autonomous trigger jobs scopes to. Returns `None` honestly when no
    such real task exists, never a fabricated default."""
    row = await conn.fetchrow(
        "SELECT MIN(deadline) AS nearest FROM tasks WHERE user_id = $1 AND status = 'open' AND deadline > now()",
        uuid.UUID(user_id),
    )
    return row["nearest"] if row is not None else None


def available_hours_before_deadline_including_today(deadline: datetime, *, now: datetime | None = None) -> float:
    """Real, corrected version of `retry_queue_drainer.py`'s own
    `available_hours_before_deadline` -- see this module's own top-of-
    file docstring for the real, live-proven bug this fixes and why the
    shared function itself is left unchanged. A same-day deadline still
    has today's own real working hours available (the same real
    semantic `features/today.py::fetch_today_capacity` already uses),
    not zero."""
    reference_now = now or datetime.now(timezone.utc)
    whole_days = max(0, (deadline.date() - reference_now.date()).days)
    if whole_days == 0:
        return TODAY_WORKING_HOURS_PER_DAY
    return whole_days * TODAY_WORKING_HOURS_PER_DAY


async def fetch_month_to_date_spend(conn: asyncpg.Connection, *, user_id: str) -> float:
    """Real, live query -- the same real logic `features/today.py::
    fetch_today_budget` already applies, queried directly here since
    that function returns an already-computed `BudgetState`, not the
    raw spend figure a `ResourceClaim` amount needs. Shared by both
    `deadline_watch.py` and `spend_alert.py`."""
    row = await conn.fetchrow(
        "SELECT COALESCE(SUM(amount), 0) AS spent FROM expenses "
        "WHERE user_id = $1 AND date_trunc('month', occurred_at) = date_trunc('month', CURRENT_DATE)",
        uuid.UUID(user_id),
    )
    return float(row["spent"])


async def fetch_budget_snapshot(conn: asyncpg.Connection, *, user_id: str) -> tuple[float, float, float]:
    """Real, shared `(monthly_limit, spent_this_month, remaining)`
    snapshot -- `DEC-148` review, LOW L1: `deadline_watch.py` and
    `negotiation_detail_backfill.py::_build_spend_alert_state`
    previously called two or three of `fetch_month_to_date_spend`/
    `fetch_monthly_budget_limit`/`fetch_remaining_monthly_budget`
    separately, issuing the identical real spend query more than once
    per call and letting the limit/spend pair used for one real number
    (e.g. a claim) drift from the pair used for another (e.g. available
    capacity) if a real, concurrent expense committed between the two
    separate statements. One real, shared read here, used everywhere
    all three numbers are needed together, closes both the duplicate
    query and the split-snapshot exposure at once."""
    spent = await fetch_month_to_date_spend(conn, user_id=user_id)
    monthly_limit = await fetch_monthly_budget_limit(conn, user_id=user_id)
    remaining = max(0.0, monthly_limit - spent)
    return monthly_limit, spent, remaining


async def fetch_remaining_monthly_budget(conn: asyncpg.Connection, *, user_id: str) -> float:
    """Real, shared finance-domain `available` figure -- never
    negative (a real month that's already run over shows `0.0` real
    remaining budget, not a nonsensical negative number). A thin
    wrapper over `fetch_budget_snapshot()` for the real callers
    (`spend_alert.py`) that only need this one number.

    RESOLVED, `DEC-148`: previously subtracted spend from the module-
    level `TODAY_MONTHLY_BUDGET_LIMIT` constant -- now reads the real,
    per-user `users.monthly_budget_limit` (migration `0015`) instead, so
    a real `UPDATE_BUDGET` execution genuinely changes what this
    function returns."""
    _limit, _spent, remaining = await fetch_budget_snapshot(conn, user_id=user_id)
    return remaining


async def fetch_detected_subscriptions_via_conn(conn: asyncpg.Connection, *, user_id: str) -> list[DetectedSubscription]:
    """Real, live query -- the same real logic `subscription_detective.
    py::fetch_detected_subscriptions` already applies, queried directly
    on the SAME real transaction's own `conn` here (not that function's
    own `pool` parameter), so a caller's own read stays transaction-
    consistent with the rest of its per-user check-and-create block.
    Reuses `detect_subscriptions()` -- the real, pure, already-tested
    grouping logic -- directly, never reimplemented. Promoted here from
    `spend_alert.py`'s own original, module-private version once this
    session's own negotiation-detail-generation work needed the exact
    same real logic as a second real caller -- the same "factor out once
    a second caller needs it" precedent this whole shared module already
    follows."""
    rows = await conn.fetch(
        "SELECT payee, amount, occurred_at FROM expenses WHERE user_id = $1 ORDER BY occurred_at",
        uuid.UUID(user_id),
    )
    return detect_subscriptions([(row["payee"], float(row["amount"]), row["occurred_at"]) for row in rows])


async def build_tasks_claim_and_state(conn: asyncpg.Connection, *, user_id: str) -> tuple[ResourceClaim, DomainState] | None:
    """Real, shared tasks-domain `ResourceClaim`/`DomainState`
    construction -- both `deadline_watch.py` and `spend_alert.py` need
    this exact same real computation, so it lives here once. Returns
    `None` honestly when the user has no real open task carrying a
    future deadline -- no real claim to construct, never a fabricated
    "no conflict" default."""
    deadline = await fetch_nearest_upcoming_task_deadline(conn, user_id=user_id)
    if deadline is None:
        return None
    committed_hours = await fetch_committed_hours_before(conn, user_id=user_id, deadline=deadline)
    available_hours = available_hours_before_deadline_including_today(deadline)
    return (
        ResourceClaim(claim_type="effort", amount=committed_hours, unit="hours"),
        DomainState(domain="tasks", available=available_hours, unit="hours"),
    )
