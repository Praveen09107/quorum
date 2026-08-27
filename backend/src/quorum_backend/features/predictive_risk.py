"""Real Predictive Risk (Phase 6, `QUORUM_PRODUCTION_COMPLETION_PLAN.md`,
`DEC-149`) -- backs `GET /predictive_risk`. `QUORUM_ARCHITECTURE_DESIGN_
DOCUMENT.md`'s own real description: "mines historical correction
patterns -- if an upcoming week's deadline density matches a
historically risky pattern (>=0.5 historical correction rate at that
density, within +/-1 deadline tolerance) it's flagged before the
collision happens, not after."

A REAL, DISCLOSED SCOPE DECISION, confirmed by direct search before
writing a line of code: unlike every other Phase 6 module built this
session (Gate Reveal, Honesty Log, Career Digest), no real API route
contract, JSON response shape, or mobile screen for this feature exists
anywhere in this project's real spec corpus -- `QUORUM_DATA_CONTRACTS.md`
names only `HistoricalWeek`/`RiskAssessment` as bare type labels in a
module-mapping table, with no field-level schema. This module's own real
shapes below are therefore new, disclosed design decisions, not
transcriptions of a pre-existing contract -- flagged explicitly rather
than presented as "the spec already said this."

TWO REAL DEFINITIONS THIS MODULE HAD TO CHOOSE, GROUNDED IN EXISTING
SCHEMA RATHER THAN A NEW TRACKING TABLE:

- **"Deadline density" for a real week** = the real COUNT of this
  user's own real `tasks.deadline` values falling within that real,
  Monday-to-Sunday UTC week. Uses the same real `tasks` table every
  other domain feature already reads -- no new schema.
- **"Correction," a real, grounded proxy** -- this schema has never
  tracked "was this task's deadline ever pushed" as its own concept
  (`UPDATE_TASK` has no real execution path, confirmed against `action_
  executor.py`'s own docstring), so this module does not invent that
  tracking. Instead, a real, past task counts as "corrected" if it
  ended in a state that honestly means the original plan didn't hold:
  real `status = 'cancelled'`, or real `status = 'open'` with a real
  `deadline` that has already passed (a real, live-observable "this
  didn't get done as planned" signal, using only columns that already
  exist).

REAL PARAMETERS, reused directly from `QUORUM_CONFIGURATION_CONSTANTS.md`
§4, not re-derived: `DEADLINE_DENSITY_TOLERANCE = 1`, `CORRECTION_RATE_
THRESHOLD = 0.5`.

"UPCOMING WEEK" MEANS NEXT CALENDAR WEEK, NOT THE CURRENT ONE, A
DELIBERATE CHOICE MATCHING THE FEATURE'S OWN STATED PURPOSE ("flagged
before the collision happens, not after"): the current week is already
partway resolved, too late for a person to act on all of it. Real
historical weeks are pooled by real deadline-density proximity (within
tolerance) to the real, current count of open tasks due next week; a
real, non-empty pool's own pooled correction rate is what gets compared
against the threshold -- never a single historical week judged alone,
which would be a real, noisy signal at low task volumes.

REAL, HONEST "NO DATA" CASE, matching this project's own established
`success_rate: float | None` precedent (`honesty_log.py`): a genuinely
new user, or one whose current deadline density has no real historical
match within tolerance, gets `pooled_correction_rate: None` and `is_at_
risk: False` -- an honest "not enough real history yet," never a
fabricated risk or a false reassurance."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import asyncpg

DEADLINE_DENSITY_TOLERANCE = 1
CORRECTION_RATE_THRESHOLD = 0.5

# A real, disclosed, reasoned bound on how far back real history is
# mined -- this app has been real for months at most (`DEC-050`), so a
# full year of real history is generous headroom, never mined
# unbounded as this real account's own history keeps growing.
HISTORY_WINDOW_WEEKS = 52


@dataclass(frozen=True)
class HistoricalWeek:
    week_start: datetime  # real, UTC-normalized Monday 00:00
    deadline_density: int
    corrected_count: int
    total_count: int

    @property
    def correction_rate(self) -> float:
        return self.corrected_count / self.total_count if self.total_count else 0.0


@dataclass(frozen=True)
class RiskAssessment:
    week_start: str  # real ISO 8601 date (Monday) of the assessed upcoming week
    deadline_density: int
    matching_historical_weeks: int
    pooled_correction_rate: float | None  # None -- genuinely no real matching history yet
    is_at_risk: bool


def _week_start(dt: datetime) -> datetime:
    """Real, UTC-normalized Monday 00:00 for whatever real week `dt`
    falls in."""
    dt = dt.astimezone(timezone.utc)
    monday = dt - timedelta(days=dt.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def _is_corrected(task: dict, *, now: datetime) -> bool:
    if task["status"] == "cancelled":
        return True
    return bool(task["status"] == "open" and task["deadline"] is not None and task["deadline"] < now)


def compute_historical_weeks(tasks: list[dict], *, now: datetime) -> list[HistoricalWeek]:
    """Pure, real grouping -- `tasks` is a list of already-fetched,
    real, minimal dicts (`deadline`, `status`). Only real tasks whose
    real deadline fell in a week strictly before the current one are
    counted as real history -- a task due later this week or next has
    no real, final outcome yet to grade as "corrected" or not."""
    current_week = _week_start(now)
    buckets: dict[datetime, list[dict]] = {}
    for task in tasks:
        deadline = task["deadline"]
        if deadline is None:
            continue
        week = _week_start(deadline)
        if week >= current_week:
            continue  # this week or later -- not yet real, settled history
        buckets.setdefault(week, []).append(task)

    return [
        HistoricalWeek(
            week_start=week,
            deadline_density=len(week_tasks),
            corrected_count=sum(1 for t in week_tasks if _is_corrected(t, now=now)),
            total_count=len(week_tasks),
        )
        for week, week_tasks in buckets.items()
    ]


def assess_upcoming_week(
    historical_weeks: list[HistoricalWeek], *, upcoming_deadline_density: int, upcoming_week_start: datetime
) -> RiskAssessment:
    """Pure, real risk computation -- pools every real historical week
    within `DEADLINE_DENSITY_TOLERANCE` of the real, assessed density,
    and flags a real risk only when that real, non-empty pool's own
    pooled correction rate reaches `CORRECTION_RATE_THRESHOLD`."""
    matching = [
        week for week in historical_weeks
        if abs(week.deadline_density - upcoming_deadline_density) <= DEADLINE_DENSITY_TOLERANCE
    ]
    total_tasks = sum(week.total_count for week in matching)
    total_corrected = sum(week.corrected_count for week in matching)
    pooled_rate = (total_corrected / total_tasks) if total_tasks else None
    is_at_risk = pooled_rate is not None and pooled_rate >= CORRECTION_RATE_THRESHOLD
    return RiskAssessment(
        week_start=upcoming_week_start.date().isoformat(),
        deadline_density=upcoming_deadline_density,
        matching_historical_weeks=len(matching),
        pooled_correction_rate=pooled_rate,
        is_at_risk=is_at_risk,
    )


async def fetch_risk_assessment(pool: asyncpg.Pool, *, user_id: str, now: datetime | None = None) -> RiskAssessment:
    """The real, live entry point -- fetches this exact user's own
    real tasks (`deadline`/`status` only, real per-user scoped),
    computes real historical weeks, and assesses next real calendar
    week against them. `now` is injectable for real, deterministic
    tests -- defaults to the real, current UTC time in production."""
    now = now or datetime.now(timezone.utc)
    current_week = _week_start(now)
    upcoming_week = current_week + timedelta(weeks=1)

    rows = await pool.fetch(
        "SELECT deadline, status FROM tasks WHERE user_id = $1 AND deadline IS NOT NULL AND deadline >= $2",
        uuid.UUID(user_id),
        now - timedelta(weeks=HISTORY_WINDOW_WEEKS),
    )
    tasks = [{"deadline": row["deadline"], "status": row["status"]} for row in rows]
    historical_weeks = compute_historical_weeks(tasks, now=now)

    upcoming_density = sum(
        1 for task in tasks
        if task["status"] == "open" and task["deadline"] is not None and _week_start(task["deadline"]) == upcoming_week
    )
    return assess_upcoming_week(
        historical_weeks, upcoming_deadline_density=upcoming_density, upcoming_week_start=upcoming_week
    )
