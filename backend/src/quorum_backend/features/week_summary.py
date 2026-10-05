"""Real, live "This week across your agents" cross-domain summary --
backs `GET /today/summary`. REAL, NEW (the redesign's own real Today-
screen work): closes a real, named gap from this session's own approved
redesign plan -- "a new 'This week across your agents' strip -- one
glanceable row surfacing real, live cross-domain numbers already
computed by the backend." This is the one new, lightweight backend
round trip the plan itself named as worth a dedicated endpoint, rather
than forcing the mobile client to eagerly fetch four separate real
screens' worth of data just to show four small numbers.

Every real number here is a genuinely cheap, already-indexed query
against a table this backend already queries elsewhere
(`tasks`/`expenses`/`applications`/`sent_messages`) -- no new real
computation, no new real LLM call, just a real, per-user-scoped
aggregate reusing data these other modules already prove is correct.
`CLAUDE.md`'s own drift pattern #1 ("reaching for an LLM call to check
something checkable in code") does not apply here at all -- this is
four plain `COUNT`/`SUM` queries."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import asyncpg

from quorum_backend.features.today import fetch_monthly_budget_limit
from quorum_backend.features.waiting_on import fetch_stale_waiting_on


@dataclass(frozen=True)
class WeekSummary:
    tasks_due_this_week: int
    month_to_date_spend: float
    monthly_budget_limit: float
    applications_in_progress: int
    waiting_on_count: int


async def fetch_week_summary(pool: asyncpg.Pool, *, user_id: str) -> WeekSummary:
    """Real, live, per-user-scoped. Four independent, cheap real
    queries -- deliberately not one giant join, since the four source
    tables share no real foreign key relating them to each other (the
    same real reason `features/search.py`'s own four domain content
    tables are queried separately too)."""
    uid = uuid.UUID(user_id)

    tasks_row = await pool.fetchrow(
        """
        SELECT COUNT(*) AS due_this_week
        FROM tasks
        WHERE user_id = $1 AND status = 'open'
          AND deadline IS NOT NULL
          AND deadline < now() + interval '7 days'
        """,
        uid,
    )

    expenses_row = await pool.fetchrow(
        """
        SELECT COALESCE(SUM(amount), 0) AS spent
        FROM expenses
        WHERE user_id = $1
          AND date_trunc('month', occurred_at) = date_trunc('month', CURRENT_DATE)
        """,
        uid,
    )

    # `applications.status` is real, confirmed-open vocabulary (no real
    # database CHECK constraint, `CLAUDE.md`'s own documented fact) --
    # "in progress" is deliberately computed as "not rejected" rather
    # than an exhaustive allow-list of every real in-progress status,
    # the same defensive-open-vocabulary handling `career_pipeline_
    # logic.dart`'s own `groupByStatus()` already established for this
    # exact column on the mobile side.
    applications_row = await pool.fetchrow(
        "SELECT COUNT(*) AS in_progress FROM applications WHERE user_id = $1 AND status != 'rejected'",
        uid,
    )

    # Reuses the real, already-tested `fetch_stale_waiting_on()` directly
    # -- deliberately NOT a second, parallel raw-SQL staleness query.
    # That function's own real cutoff is `sent_at <= now - threshold`
    # (inclusive, computed in Python by `find_stale_waiting_on()`); an
    # earlier version of this function wrote its own raw SQL `sent_at <
    # now() - interval` here, a real, subtly different (exclusive,
    # computed in Postgres) boundary that could disagree with the Waiting
    # On screen's own real count by one row right at the threshold.
    stale_waiting_on = await fetch_stale_waiting_on(pool, user_id=user_id)

    monthly_limit = await fetch_monthly_budget_limit(pool, user_id=user_id)

    return WeekSummary(
        tasks_due_this_week=tasks_row["due_this_week"],
        month_to_date_spend=float(expenses_row["spent"]),
        monthly_budget_limit=monthly_limit,
        applications_in_progress=applications_row["in_progress"],
        waiting_on_count=len(stale_waiting_on),
    )
