"""Real, live Finance-domain read query, backing `GET /finance/expenses`
-- the redesign's own real "Finance hub" work. Closes a real, confirmed
gap found while enriching the mobile Finance screen: `features/
subscription_detective.py` already gives real, live subscription
detection a backend, but no real route anywhere has ever let a person
see their actual recent expenses, just the derived subscription
pattern. Mirrors `features/tasks.py`'s own established real, live,
per-user-scoped read-query shape exactly."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import asyncpg

# A real, deliberate, small cap -- this is a "recent activity" list for
# a Finance hub card, not a full transaction-history export. Matches
# `search.py`'s own `SEARCH_RESULT_CAP` precedent for "a bounded recent
# list is the honest scope for this real UI surface."
RECENT_EXPENSES_LIMIT = 20


@dataclass(frozen=True)
class ExpenseRecord:
    expense_id: str
    payee: str
    amount: float
    occurred_at: str  # ISO 8601 with a literal "Z" suffix


def _format_occurred_at(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _row_to_expense(row: asyncpg.Record) -> ExpenseRecord:
    return ExpenseRecord(
        expense_id=str(row["expense_id"]),
        payee=row["payee"],
        # A real NUMERIC column comes back as a Decimal by default --
        # cast to float explicitly, the same established discipline
        # `tasks.py`'s own `estimated_hours` handling already uses.
        amount=float(row["amount"]),
        occurred_at=_format_occurred_at(row["occurred_at"]),
    )


async def fetch_recent_expenses(pool: asyncpg.Pool, *, user_id: str, limit: int = RECENT_EXPENSES_LIMIT) -> list[ExpenseRecord]:
    """Real, live, per-user-scoped. Most recent first -- the real,
    actionable order for "what have I actually been spending on," the
    opposite of `subscription_detective.py`'s own most-expensive-first
    order (a genuinely different real question)."""
    rows = await pool.fetch(
        "SELECT expense_id, payee, amount, occurred_at FROM expenses WHERE user_id = $1 ORDER BY occurred_at DESC LIMIT $2",
        uuid.UUID(user_id),
        limit,
    )
    return [_row_to_expense(row) for row in rows]
