"""Real, live Tasks-domain read query, backing `GET /tasks`
(`QUORUM_DATA_CONTRACTS.md` §5.17).

HONEST DISCLOSURE, confirmed by direct search before writing this file:
no read path for the real `tasks` table existed anywhere in this
backend before this session -- `agents/tasks_agent.py` operates purely
on already-fetched context passed in as arguments (confirmed directly:
zero references to `user_id` or any SQL anywhere in that file), the
same "the Gate/agents never touch the database directly" separation
`trust_digest.py`'s own real, live database work established first.

**RESOLVED, `DEC-110`:** this module previously carried the same
disclosed per-user-scoping limitation as `trust_digest.py` --
`tasks.user_id` is real, but no real user-provisioning system existed
anywhere in this backend to map a real Google `sub` onto it. A real
`users` table and `auth/user_provisioning.py` now close that gap;
`fetch_tasks()` below takes the real, resolved internal `user_id` and
filters by it directly. `/trust_digest` still carries the original
limitation -- `action_events` itself has no `user_id` column at all,
a genuinely different, unresolved gap.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import asyncpg


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    title: str
    estimated_hours: float
    deadline: str | None  # ISO 8601 with a literal "Z" suffix, or None
    status: str


def _format_deadline(deadline: datetime) -> str:
    # A real, UTC-normalized ISO 8601 string with a literal "Z" suffix --
    # matches QUORUM_DATA_CONTRACTS.md §5.17's own example
    # ("2026-08-20T00:00:00Z") exactly, rather than Python's default
    # "+00:00" offset suffix.
    return deadline.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _row_to_task(row: asyncpg.Record) -> TaskRecord:
    deadline = row["deadline"]
    return TaskRecord(
        task_id=str(row["task_id"]),
        title=row["title"],
        # asyncpg maps a real NUMERIC(4,1) column to a Python Decimal by
        # default (no custom type codec is registered anywhere in
        # core/db.py) -- cast to float explicitly, matching
        # §5.17's own JSON example (a plain number, e.g. 2.5), never
        # left as a Decimal a plain dict response can't serialize.
        estimated_hours=float(row["estimated_hours"]),
        deadline=_format_deadline(deadline) if deadline is not None else None,
        status=row["status"],
    )


async def fetch_tasks(pool: asyncpg.Pool, *, user_id: str) -> list[TaskRecord]:
    """The real, live query backing `GET /tasks`, real per-user scoped
    as of `DEC-110`. Ordered by `created_at` for a real, deterministic
    response -- the mobile client's own `sortTasks()` (`tasks_logic.
    dart`) re-sorts for display regardless, so this order is a real,
    reasoned default (insertion order), not a claim about display
    order.

    `user_id` is the real, resolved internal UUID (from
    `auth/user_provisioning.py`), converted to a real `uuid.UUID`
    object before binding -- asyncpg's default UUID codec expects one,
    never a plain string, matching the pattern every real UUID-column
    insert in this codebase's own test suite already established."""
    rows = await pool.fetch(
        """
        SELECT task_id, title, estimated_hours, deadline, status
        FROM tasks
        WHERE user_id = $1
        ORDER BY created_at
        """,
        uuid.UUID(user_id),
    )
    return [_row_to_task(row) for row in rows]
