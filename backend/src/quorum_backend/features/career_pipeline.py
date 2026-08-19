"""Real, live Career-domain read query, backing `GET /career_pipeline`
(`QUORUM_DATA_CONTRACTS.md` §5.10).

HONEST DISCLOSURE, confirmed by direct search before writing this file:
no read path for the real `applications` table existed anywhere in
this backend before this session -- `agents/career_agent.py` operates
purely on already-fetched context passed in as arguments (confirmed
directly: zero references to `user_id` or any SQL anywhere in that
file), the same "the Gate/agents never touch the database directly"
separation `trust_digest.py`/`tasks.py` already established.

Same real, disclosed limitation as `trust_digest.py`/`tasks.py`, not a
new gap: `applications.user_id` is a real, non-null `UUID` column, but
no real user-provisioning system anywhere in this backend maps a
Google `sub` claim onto it (no `users` table exists in the real
migration) -- this route is a real "you must be signed in" gate, not
yet a per-user data filter.

A real, deliberate CONTRAST with `tasks.py`, confirmed directly against
the real schema before writing this file, not assumed by habit:
`applications.status` has NO database `CHECK` constraint (unlike
`tasks.status`) -- the real status vocabulary is genuinely open. This
module does no status validation or normalization of any kind; the raw
column value passes through unchanged, exactly matching
`career_pipeline_logic.dart`'s own real, already-tested defensive
handling on the client side (`statusLabel()`'s de-snaking fallback,
`groupByStatus()`'s never-drop-an-unrecognized-status behavior).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import asyncpg


@dataclass(frozen=True)
class CareerApplicationRecord:
    application_id: str
    company: str
    role: str | None
    status: str
    deadline: str | None  # ISO 8601 with a literal "Z" suffix, or None


def _format_deadline(deadline: datetime) -> str:
    # Same real, UTC-normalized ISO 8601 formatting as tasks.py's own
    # _format_deadline -- matches QUORUM_DATA_CONTRACTS.md §5.10's own
    # example ("2026-09-01T00:00:00Z") exactly.
    return deadline.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _row_to_application(row: asyncpg.Record) -> CareerApplicationRecord:
    deadline = row["deadline"]
    return CareerApplicationRecord(
        application_id=str(row["application_id"]),
        company=row["company"],
        role=row["role"],
        status=row["status"],
        deadline=_format_deadline(deadline) if deadline is not None else None,
    )


async def fetch_career_pipeline(pool: asyncpg.Pool) -> list[CareerApplicationRecord]:
    """The real, live query backing `GET /career_pipeline`. Ordered by
    `created_at` for a real, deterministic response -- the mobile
    client's own `groupByStatus()`/`orderedStatusKeys()`
    (`career_pipeline_logic.dart`) determine real display order and
    grouping, so this is a reasoned default (insertion order), not a
    claim about display order."""
    rows = await pool.fetch(
        """
        SELECT application_id, company, role, status, deadline
        FROM applications
        ORDER BY created_at
        """
    )
    return [_row_to_application(row) for row in rows]
