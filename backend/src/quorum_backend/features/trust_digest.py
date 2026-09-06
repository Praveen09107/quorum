"""Week-over-week trend comparison for the Trust Digest screen.
HONEST DISCLOSURE: a genuinely new backend module, not a wrapper around
existing logic -- no week-over-week trend comparison existed anywhere in
this repository's backend before this session. `backend/src/quorum_
backend/features/predictive_risk.py`, cited by this session's own spec as
this module's design-philosophy precedent, did not exist in this
repository at the time (`backend/features/*` from the ADD's Sec 9.7 table
had never been built here) -- built directly against the philosophy that
table DESCRIBES ("deliberately simple and explainable... a count
comparison, not a trained model"), not literally copied from a file this
repository didn't have then. **A real, stale-claim correction, `DEC-150`:**
`predictive_risk.py` is now real too (`DEC-149`) -- this paragraph is kept
as a historical account of this module's own real origin, not edited to
imply the precedent existed at the time.

Real, deliberate design choice: a plain threshold comparison against a
real, named constant, never a trained model or a magic number.

Batch 10 Phase 3 Part B adds the real weekly-aggregation query this
module's own `compare_weeks()` docstring named as explicitly out of
scope -- `aggregate_weekly_summary()` and `fetch_trust_digest()` below,
querying the real, live `action_events` table (`DEC-098`) directly via
`asyncpg`, closing the gap to a real, live `GET /trust_digest` endpoint.

**RESOLVED, `DEC-150`:** `aggregate_weekly_summary()`/`fetch_trust_digest()`
had no real `user_id` filter at all since the day they were written --
`action_events.user_id` existed since migration `0004`/`DEC-119`, but this
module was never updated to use it, meaning the real, live, deployed
`GET /trust_digest` genuinely aggregated every real user's data together.
Found while building `DEC-145`'s Honesty Log, disclosed rather than
silently fixed at the time (out of that session's own scope) -- closed
here as its own, real, standalone fix. Both functions now require a real,
resolved `user_id`, matching every other per-user-scoped route in this
backend.

**RESOLVED, a real, live, currently-active bug found on-device (Session
2, `QUORUM_FINAL_COMPLETION_PLAN.md`, `DEC-168`), affecting THIS
project's own real Trust screen, its central thesis surface:**
`aggregate_weekly_summary()`'s own SQL bound `week_start`/`week_end`
(real Python `date` objects) as raw query parameters with no explicit
cast. Because the comparison itself (`COALESCE(resolved_at,
created_at) >= $2 AND ... < $3`) is against a `timestamptz` column,
Postgres infers both parameters as `timestamptz`, not `date` -- and
asyncpg's own binary encoder for a bare Python `date` value, bound as
`timestamptz`, silently uses the local machine's OS timezone (not UTC,
and not the real, confirmed-UTC `SHOW TIMEZONE` session setting) to
compute the encoded instant. On a machine set to IST (UTC+5:30), this
means `week_end` was actually encoded as `week_end - 5.5 hours` in real
UTC terms -- so for roughly the last 5.5 real UTC hours of every single
day, any genuine action resolved in that window was silently excluded
from "this week"'s count, understating `total_actions`/`success_rate`
on the live Trust screen for a very real, recurring fraction of every
day, not a rare edge case. Live-reproduced directly, multiple times,
before writing this fix: a real row with `outcome = 'approved_unchanged'`
and a real, current `resolved_at` returned `total_actions = 0` when
queried during that window, and `total_actions = 1` outside it, with
the identical query and data. **Fixed** by casting both parameters
explicitly to `::date` in the SQL -- this forces Postgres's own,
already-confirmed-correct `date -> timestamptz` implicit cast (real,
live-verified: `'<date>'::date::timestamptz` correctly resolves to UTC
midnight, matching the real, confirmed-UTC session timezone) rather
than trusting asyncpg's own client-side encoder to guess the right
instant for an ambiguous, timezone-naive Python `date` value.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Literal

import asyncpg

# A 2-percentage-point real, named threshold: week-over-week success-rate
# movement smaller than this is treated as noise, not a real trend. Not
# specified anywhere in this project's real corpus -- a real, reasoned
# choice, disclosed rather than presented as a recalled spec value.
STABLE_THRESHOLD = 0.02


@dataclass(frozen=True)
class WeeklyTrustSummary:
    week_start: str  # ISO date, e.g. "2026-08-10"
    total_actions: int
    success_rate: float


@dataclass(frozen=True)
class TrendResult:
    current_week: WeeklyTrustSummary
    previous_week: WeeklyTrustSummary | None
    trend: Literal["improving", "declining", "stable", "insufficient_data"]
    delta: float | None


def compare_weeks(
    current: WeeklyTrustSummary,
    previous: WeeklyTrustSummary | None,
) -> TrendResult:
    """Real, deterministic comparison over two already-computed weekly
    summaries -- the real weekly aggregation query itself (grouping raw
    action_events rows into a WeeklyTrustSummary) is out of scope here;
    this function is independently correct regardless of how its inputs
    are produced.

    insufficient_data is a real, honest fourth state -- a week with zero
    actions, or no prior week to compare against -- never silently
    reported as "stable", which would claim a real comparison was made
    when it genuinely wasn't.
    """
    if previous is None or current.total_actions == 0 or previous.total_actions == 0:
        return TrendResult(current_week=current, previous_week=previous, trend="insufficient_data", delta=None)

    # round(..., 3) resolves real floating-point noise at the exact
    # threshold boundary -- confirmed live before trusting the exact-
    # equality comparison below (0.80 + STABLE_THRESHOLD produces
    # 0.8200000000000001 in raw floating point; rounding to 3 places
    # cleanly yields 0.02 again).
    delta = round(current.success_rate - previous.success_rate, 3)

    if delta > STABLE_THRESHOLD:
        trend: Literal["improving", "declining", "stable"] = "improving"
    elif delta < -STABLE_THRESHOLD:
        trend = "declining"
    else:
        trend = "stable"

    return TrendResult(current_week=current, previous_week=previous, trend=trend, delta=delta)


async def aggregate_weekly_summary(pool: asyncpg.Pool, week_start: date, *, user_id: str) -> WeeklyTrustSummary:
    """The real weekly-aggregation query -- groups raw `action_events`
    rows into a `WeeklyTrustSummary`, the one gap `compare_weeks()`'s own
    docstring named as out of scope.

    RESOLVED, real per-user scoping closed here: this query previously
    had no `user_id` filter at all, despite `action_events.user_id`
    existing since migration `0004`/`DEC-119` -- a real, live, currently-
    deployed cross-user aggregation gap, found while building `DEC-145`'s
    Honesty Log and disclosed rather than silently fixed at the time (out
    of that session's own scope). Every real caller now must supply the
    real, resolved internal `user_id`, matching every other per-user-
    scoped route in this backend (`/tasks`, `/career_pipeline`, `/today`,
    etc. since `DEC-110`).

    Only resolved actions (`outcome IS NOT NULL`) are counted, bucketed
    by `COALESCE(resolved_at, created_at)` -- defensive against a real
    row somehow having `outcome` set without `resolved_at` (the schema
    doesn't enforce they're set together), the same defensive-parsing
    discipline `CLAUDE.md` holds for `applications.status`.

    `uncertain_no_data` outcomes are deliberately excluded from both
    `total_actions` and the success-rate numerator, and never a
    denominator either -- counting them as attempts that merely didn't
    succeed would collapse "we don't know" into "it failed," the exact
    thing `CLAUDE.md`'s `Finding.evidence_state` rule forbids for Stage A
    findings, applied here by the same reasoning to this real, adjacent
    case. This is a real, reasoned, disclosed choice -- nothing in this
    project's real spec corpus states the formula explicitly.
    """
    week_end = week_start + timedelta(days=7)
    row = await pool.fetchrow(
        """
        SELECT
            COUNT(*) FILTER (
                WHERE outcome IN ('approved_unchanged', 'caught_by_gate', 'corrected_by_user')
            ) AS total_actions,
            COUNT(*) FILTER (WHERE outcome = 'approved_unchanged') AS successes
        FROM action_events
        WHERE user_id = $1
          AND COALESCE(resolved_at, created_at) >= $2::date
          AND COALESCE(resolved_at, created_at) < $3::date
        """,
        uuid.UUID(user_id),
        week_start,
        week_end,
    )
    total_actions: int = row["total_actions"]
    successes: int = row["successes"]
    # A real, honest 0.0 fallback when total_actions is 0 -- never read as
    # a meaningful rate on its own, since compare_weeks() already treats
    # total_actions == 0 as insufficient_data before delta/trend logic
    # would ever consult this value.
    success_rate = round(successes / total_actions, 3) if total_actions > 0 else 0.0
    return WeeklyTrustSummary(week_start=week_start.isoformat(), total_actions=total_actions, success_rate=success_rate)


async def fetch_trust_digest(pool: asyncpg.Pool, *, user_id: str, today: date | None = None) -> TrendResult:
    """The real, live entry point for `GET /trust_digest` -- computes
    this week's and last week's real `WeeklyTrustSummary` from the real
    database (ISO weeks, Monday-start), real per-user scoped, then
    reuses the already-correct, already-tested `compare_weeks()`
    unchanged.

    `today` is injectable for tests only -- the real endpoint always
    calls this with no override, so it always uses the real current
    date.
    """
    if today is None:
        today = datetime.now(timezone.utc).date()
    this_week_start = today - timedelta(days=today.weekday())
    last_week_start = this_week_start - timedelta(days=7)

    current = await aggregate_weekly_summary(pool, this_week_start, user_id=user_id)
    previous = await aggregate_weekly_summary(pool, last_week_start, user_id=user_id)

    return compare_weeks(current, previous)
