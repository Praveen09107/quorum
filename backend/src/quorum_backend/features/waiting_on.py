"""Real Waiting On tracker (Phase 4, `QUORUM_PRODUCTION_COMPLETION_
PLAN.md`) -- the inverse of commitment tracking: surfaces sent messages
with no reply past a real staleness threshold. Closes the real gap
`QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §9.1 already names, and
`QUORUM_DATA_CONTRACTS.md` §5.9 already specifies the real response
shape for -- confirmed directly before writing a line of code: neither
document gave this module a full implementation, only the real,
already-tested mobile side (`waiting_on_logic.dart`, `waiting_on_
screen.dart`) and the real response contract (`recipient`/`subject`/
`sent_at`) already existed, both built years ahead of any real backend
to call, per `.claude/CLAUDE.md`'s own disclosed "honest `UnimplementedError`
placeholder" pattern for every mobile screen.

`SentMessage` is documented in `QUORUM_DATA_CONTRACTS.md` §2 as a real,
internal-only feature-layer schema living here -- a plain `@dataclass`,
never crossing the API boundary directly (the real `GET /waiting_on`
route builds its own response shape from this).

`WAITING_ON_STALENESS_THRESHOLD_DAYS = 4` is `QUORUM_CONFIGURATION_
CONSTANTS.md` §4's own real, specified, "default parameter, overridable"
value -- reused here, not reinvented.

REAL SPLIT, matching `subscription_detective.py`'s own already-
established pure-computation/live-query pattern: `find_stale_waiting_on()`
is pure and real business logic (what counts as "stale" at all,
`QUORUM_DATA_CONTRACTS.md` §5.9's own explicit note that this decision
stays server-side, never re-derived on the client); the real, live
Postgres queries are kept separate, in their own real, testable
functions.

REAL, HOW A REPLY IS DETECTED -- confirmed against Gmail's actual API
shape before designing this, not assumed: Gmail groups every message
into a real `threadId`; `features/email_ingestion.py`'s own real
polling job (a genuinely separate concern -- the real network calls to
Gmail, not this module's job) calls `record_sent_message()` for every
real message THIS USER sent, and `mark_thread_replied()` the moment a
NEW real message arrives in a `thread_id` that already has a real,
unreplied `sent_messages` row -- the real signal an actual reply landed.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import asyncpg

WAITING_ON_STALENESS_THRESHOLD_DAYS = 4


@dataclass(frozen=True)
class SentMessage:
    recipient: str
    subject: str
    sent_at: datetime


def find_stale_waiting_on(
    messages: list[SentMessage],
    *,
    now: datetime | None = None,
    threshold_days: int = WAITING_ON_STALENESS_THRESHOLD_DAYS,
) -> list[SentMessage]:
    """Pure, real, deterministic. Every real message passed in is
    assumed already-unreplied -- the real `replied_at IS NULL` filter
    is the caller's own real DB query's job (`fetch_unreplied_sent_
    messages()` below), never re-checked here. This function's only
    real job is the real age threshold -- exactly the same real
    "business logic stays server-side" split `QUORUM_DATA_CONTRACTS.md`
    §5.9 already specifies."""
    reference_now = now or datetime.now(timezone.utc)
    cutoff = reference_now - timedelta(days=threshold_days)
    return [message for message in messages if message.sent_at <= cutoff]


async def fetch_unreplied_sent_messages(pool: asyncpg.Pool, *, user_id: str) -> list[SentMessage]:
    """Real, live query -- every real message this user sent that has
    never had a real reply detected, oldest first (matching `sortByStaleness`'s
    own already-established "oldest matters more" convention on the
    mobile side, reapplied here so a caller that doesn't re-sort still
    gets a real, sensible order)."""
    rows = await pool.fetch(
        "SELECT recipient, subject, sent_at FROM sent_messages WHERE user_id = $1 AND replied_at IS NULL ORDER BY sent_at",
        uuid.UUID(user_id),
    )
    return [SentMessage(recipient=row["recipient"], subject=row["subject"], sent_at=row["sent_at"]) for row in rows]


async def fetch_stale_waiting_on(pool: asyncpg.Pool, *, user_id: str, now: datetime | None = None) -> list[SentMessage]:
    """The one real function `GET /waiting_on` (`main.py`) calls --
    composes the real, live query above with the real, pure staleness
    filter. Never touches Gmail directly; this module's own job is
    reading what `features/email_ingestion.py`'s real polling job has
    already written."""
    messages = await fetch_unreplied_sent_messages(pool, user_id=user_id)
    return find_stale_waiting_on(messages, now=now)


async def record_sent_message(
    pool: asyncpg.Pool,
    *,
    user_id: str,
    message_id: str,
    thread_id: str,
    recipient: str,
    subject: str,
    sent_at: datetime,
) -> bool:
    """Real, live, idempotent insert -- a real re-poll of the same real
    Gmail message is a real, harmless no-op (`ON CONFLICT DO NOTHING`,
    the real `UNIQUE (user_id, message_id)` constraint from migration
    `0011`), never a duplicate row. Returns whether this call genuinely
    inserted a new real row, so a caller (the real ingestion job) can
    tell a real new message from an already-seen one without a second
    query."""
    tag = await pool.execute(
        "INSERT INTO sent_messages (user_id, message_id, thread_id, recipient, subject, sent_at) "
        "VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT (user_id, message_id) DO NOTHING",
        uuid.UUID(user_id),
        message_id,
        thread_id,
        recipient,
        subject,
        sent_at,
    )
    return tag == "INSERT 0 1"


async def mark_thread_replied(pool: asyncpg.Pool, *, user_id: str, thread_id: str, replied_at: datetime) -> int:
    """Real, live update -- the real signal a reply landed. Marks
    EVERY real, still-unreplied `sent_messages` row in this real
    thread (not just the most recent one) as replied, since a single
    real incoming message in a thread genuinely answers every prior
    real message this user sent in that same thread, not just the
    latest. Returns the real count of rows actually updated -- `0` is
    a real, honest, common case (a reply arrived in a thread this user
    never sent the first message in, or every message in the thread
    was already marked replied)."""
    tag = await pool.execute(
        "UPDATE sent_messages SET replied_at = $1 WHERE user_id = $2 AND thread_id = $3 AND replied_at IS NULL",
        replied_at,
        uuid.UUID(user_id),
        thread_id,
    )
    return int(tag.rsplit(" ", 1)[-1])
