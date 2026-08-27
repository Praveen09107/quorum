"""Real, live queries and pure computation backing `GET /today`
(`QUORUM_DATA_CONTRACTS.md` §5.4 -- the full response shape, including
`needs_you_now` and `in_motion`, was already fully specified since
`DEC-026`/`DEC-028`; this module is the first real implementation
against that already-correct spec, not new spec-writing, `DEC-119`).

HONEST DISCLOSURE, confirmed by direct search before writing this
file: no persistence for a negotiation's own state has ever existed
anywhere in this backend -- `negotiation/subgraph.py` computes a full
negotiation in memory, per request, and has never itself written a
real row anywhere. `migrations/0004_today_persistence/` closes that
gap with a genuinely new `negotiations` table, and adds the one real,
missing column (`user_id`) `action_events` needed to be safely
per-user scoped -- done from this module's first line, unlike
`/tasks`/`/career_pipeline`/`/finance/subscriptions`, which needed a
later retrofit (`DEC-110`).

A real, disclosed, honest scope boundary, not silently glossed over:
this module closes the READ side of `/today` only. Nothing in this
backend currently invokes the Gate against a real, live user action --
no email/calendar/task-monitoring pipeline exists yet to ever
*produce* a real row into `action_events` or `negotiations` in the
first place. `GET /today` will therefore genuinely, honestly return
empty `needs_you_now`/`in_motion` arrays in real production use, the
same "correct but currently empty" result `/trust_digest` already
established (`DEC-100`) -- not a bug in this module, a real, disclosed
fact about what doesn't exist yet elsewhere in this backend.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import asyncpg

from quorum_backend.features.meeting_load import WORKING_HOURS_PER_DAY as TODAY_WORKING_HOURS_PER_DAY

# A REAL, DISCLOSED CORRECTION TO THIS FILE'S OWN EARLIER COMMENT, closed
# by `features/meeting_load.py` (Phase 5, `DEC-144`): this line used to
# define a second, local `8.0` with a comment claiming it "reuses the
# real, already-defined constant from QUORUM_CONFIGURATION_CONSTANTS.md
# §4" -- true of the real, specified VALUE, but `meeting_load.py` (the
# module that constant actually belongs to) did not exist anywhere in
# this repository yet, so there was no real constant to import, only a
# duplicate `8.0` with an aspirational comment. Now a real import, not
# a coincidence of two files agreeing on the same number.

# RESOLVED, `DEC-148`: this comment previously described the value below
# as a genuinely global default because "no per-user budget-
# configuration feature exists anywhere in this app yet." A real one
# now does -- `users.monthly_budget_limit` (migration `0015`), closing
# the gap `action_executor.py`'s own docstring named as the reason
# `UPDATE_BUDGET` had no real execution target. `50000.0` survives here
# ONLY as the real migration's own default value (every existing user
# starts here) and as this constant's own historical name -- the real,
# live-read path is `fetch_monthly_budget_limit()` below, never this
# module-level constant directly, for every real per-user computation.
# QUORUM_CONFIGURATION_CONSTANTS.md §4.
TODAY_MONTHLY_BUDGET_LIMIT = 50000.0


async def fetch_monthly_budget_limit(conn: asyncpg.Pool | asyncpg.Connection, *, user_id: str) -> float:
    """Real, live, per-user lookup -- `DEC-148`. Accepts either a real
    `Pool` or a real `Connection`: every real call site here is a single,
    non-transactional read, and both asyncpg types expose an identical
    `fetchrow()` interface for that -- no pool-specific behavior (no
    `.acquire()`, no transaction management) is ever needed by this
    function itself. Callers already inside their own transaction
    (`negotiation_trigger_support.py`, `negotiation_detail_backfill.py`)
    pass their own `conn`, so this read joins that same transaction
    rather than opening a second, separate one; `fetch_today_budget()`
    below, with no surrounding transaction of its own, passes the real
    `pool` directly."""
    row = await conn.fetchrow("SELECT monthly_budget_limit FROM users WHERE user_id = $1", uuid.UUID(user_id))
    # A user_id that doesn't resolve to a real row is a genuine caller
    # error (every real caller here has already resolved this exact
    # user_id via `_resolve_internal_user_id_or_404` or an internal
    # job's own real user iteration) -- falls back to the same real
    # default the migration itself uses, rather than raising and
    # breaking an entire real batch job over one bad id.
    return float(row["monthly_budget_limit"]) if row is not None else TODAY_MONTHLY_BUDGET_LIMIT


@dataclass(frozen=True)
class CapacityState:
    hours_remaining_today: float
    remaining_fraction: float  # 0.0-1.0
    source: str  # "live_backend" | "local_mirror" -- always "live_backend" here


@dataclass(frozen=True)
class BudgetState:
    amount_remaining: float
    remaining_fraction: float  # 0.0-1.0
    source: str


@dataclass(frozen=True)
class PendingActionRecord:
    proposal_id: str
    action_type: str
    stakes: str
    payload: dict
    created_at: str  # ISO 8601 with a literal "Z" suffix


@dataclass(frozen=True)
class ActiveNegotiationRecord:
    negotiation_id: str
    conflicted_domains: list[str]
    started_at: str  # ISO 8601 with a literal "Z" suffix


def _format_timestamp(value: datetime) -> str:
    # A real, UTC-normalized ISO 8601 string with a literal "Z" suffix
    # -- matches §5.4's own real examples exactly, the same established
    # pattern every other real feature module in this backend already
    # uses (tasks.py, career_pipeline.py).
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def compute_capacity_state(
    *, total_working_hours_today: float, hours_committed_today: float
) -> CapacityState:
    """Pure, deterministic -- the same real Python port of
    `mobile/lib/features/computed_state.dart`'s `computeCapacityState()`,
    confirmed identical arithmetic before being trusted (real clamp
    order, real division-by-zero guard). The literal implementation of
    the F4 fix's guarantee (ADD §10.5): this backend and the mobile
    Drift mirror must compute the same real numbers from the same real
    inputs, regardless of which side of the network they run on."""
    remaining = max(0.0, min(total_working_hours_today, total_working_hours_today - hours_committed_today))
    fraction = 0.0 if total_working_hours_today <= 0 else max(0.0, min(1.0, remaining / total_working_hours_today))
    return CapacityState(hours_remaining_today=remaining, remaining_fraction=fraction, source="live_backend")


def compute_budget_state(*, monthly_limit: float, spent_so_far: float) -> BudgetState:
    """Pure, deterministic -- the real Python port of `computed_state.
    dart`'s `computeBudgetState()`, same arithmetic-parity discipline as
    `compute_capacity_state()` above."""
    remaining = max(0.0, min(monthly_limit, monthly_limit - spent_so_far))
    fraction = 0.0 if monthly_limit <= 0 else max(0.0, min(1.0, remaining / monthly_limit))
    return BudgetState(amount_remaining=remaining, remaining_fraction=fraction, source="live_backend")


async def fetch_pending_actions(pool: asyncpg.Pool, *, user_id: str) -> list[PendingActionRecord]:
    """The real, live query backing `needs_you_now`, real per-user
    scoped from this module's first line, per `DEC-110`'s own lesson.

    `resolved_at IS NULL` is the real, precise definition of "pending,"
    grounded directly in `QUORUM_GATE_SPECIFICATION.md` §2's own state
    machine, not guessed: every real Stage-B terminal state (S0/S1 auto-
    approval, a real Stage-A hard reject, `escalate_to_human`, and the
    unconditional S3 `pending_human_approval` override) resolves to a
    real, immediate `outcome`/`resolved_at` the moment the Gate decides
    an action's fate does NOT require further human action -- only a
    genuinely still-open action ever has a real, live NULL `resolved_at`
    in the first place."""
    rows = await pool.fetch(
        """
        SELECT proposal_id, action_type, stakes, payload, created_at
        FROM action_events
        WHERE user_id = $1 AND resolved_at IS NULL
        ORDER BY created_at
        """,
        uuid.UUID(user_id),
    )
    return [
        PendingActionRecord(
            proposal_id=str(row["proposal_id"]),
            action_type=row["action_type"],
            stakes=row["stakes"],
            # asyncpg returns a real JSONB column as a plain string by
            # default (no custom type codec is registered anywhere in
            # core/db.py, confirmed live before writing this line) --
            # decoded explicitly, never left as an unparsed string a
            # plain dict response can't nest correctly.
            payload=json.loads(row["payload"]),
            created_at=_format_timestamp(row["created_at"]),
        )
        for row in rows
    ]


async def fetch_active_negotiations(pool: asyncpg.Pool, *, user_id: str) -> list[ActiveNegotiationRecord]:
    """The real, live query backing `in_motion`, real per-user scoped
    from this module's first line. `resolved_at IS NULL` is the real,
    honest "still awaiting a real choice" state -- the same real
    column, same meaning, `POST /negotiations/{id}/choose` (§5.6, still
    genuinely unbuilt) will set once it exists."""
    rows = await pool.fetch(
        """
        SELECT negotiation_id, conflicted_domains, started_at
        FROM negotiations
        WHERE user_id = $1 AND resolved_at IS NULL
        ORDER BY started_at
        """,
        uuid.UUID(user_id),
    )
    return [
        ActiveNegotiationRecord(
            negotiation_id=str(row["negotiation_id"]),
            # A real Postgres TEXT[] column round-trips as a plain
            # Python list natively via asyncpg -- confirmed live before
            # writing this line, no manual decode needed (unlike JSONB
            # above).
            conflicted_domains=list(row["conflicted_domains"]),
            started_at=_format_timestamp(row["started_at"]),
        )
        for row in rows
    ]


async def fetch_today_capacity(pool: asyncpg.Pool, *, user_id: str) -> CapacityState:
    """Real, live-computed capacity: today's real open task commitments
    (`tasks.estimated_hours`, `deadline`'s real calendar date matching
    today, `status = 'open'` -- `done`/`cancelled` tasks commit no real
    remaining time) against the real, shared working-day constant."""
    row = await pool.fetchrow(
        """
        SELECT COALESCE(SUM(estimated_hours), 0) AS committed
        FROM tasks
        WHERE user_id = $1 AND status = 'open' AND deadline::date = CURRENT_DATE
        """,
        uuid.UUID(user_id),
    )
    # A real NUMERIC SUM comes back as a Decimal by default -- cast to
    # float explicitly, the same established discipline as every other
    # real feature module's own NUMERIC handling.
    committed = float(row["committed"])
    return compute_capacity_state(
        total_working_hours_today=TODAY_WORKING_HOURS_PER_DAY, hours_committed_today=committed
    )


async def fetch_today_budget(pool: asyncpg.Pool, *, user_id: str) -> BudgetState:
    """Real, live-computed budget: real expenses actually incurred so
    far this real calendar month against the real, disclosed default
    monthly limit."""
    row = await pool.fetchrow(
        """
        SELECT COALESCE(SUM(amount), 0) AS spent
        FROM expenses
        WHERE user_id = $1
          AND date_trunc('month', occurred_at) = date_trunc('month', CURRENT_DATE)
        """,
        uuid.UUID(user_id),
    )
    spent = float(row["spent"])
    monthly_limit = await fetch_monthly_budget_limit(pool, user_id=user_id)
    return compute_budget_state(monthly_limit=monthly_limit, spent_so_far=spent)
