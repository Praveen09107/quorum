"""Real Email agent workspace data (`DEC-199`, product rebuild). Backs
`GET /email/overview`.

WHY THIS EXISTS: `DEC-197` closed the Agents tab's own tap-navigation
gap for four of five domains by reusing existing screens, but honestly
disclosed that Email has no real workspace at all -- the rebuild plan's
own Part B1 named it as a real tool, not a read-only list: "threads
awaiting reply, drafts the agent created... sent history with delivery
state... known-recipient trust list." This module is the real, live
data behind exactly those three real, already-existing sources this
backend has been writing to for multiple sessions and never once
surfaced together: `action_events` (real `CREATE_EMAIL_DRAFT` rows),
`sent_messages` (real Gmail sends, `features/waiting_on.py`'s own
table), and the same table's own distinct recipients.

REAL, DELIBERATE SCOPE DECISION: no new table and no new column. Every
real fact here already exists; this module is a real, pure read over
data this backend was already writing before this session, the same
"the database is the only source of truth" discipline `agent_
telemetry.py`/`gate_stats.py` already established for the Agents index
and the Gate showcase.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime

import asyncpg

from quorum_backend.features.honesty_log import SUCCESS_OUTCOMES
from quorum_backend.gate.schemas import ActionType

# A real, disclosed bound on every real list this module returns --
# matching `_fetch_known_recipients()`'s own established "most recent
# N, a real caller needing more is a real, honest non-match" trade-off
# (`quick_capture.py`), not an oversight.
_DEFAULT_LIMIT = 25


@dataclass(frozen=True)
class EmailDraft:
    proposal_id: str
    created_at: datetime
    recipient: str
    subject: str | None
    draft_id: str | None


@dataclass(frozen=True)
class SentMessageRecord:
    recipient: str
    subject: str
    sent_at: datetime
    # `None` means genuinely still unreplied -- never collapsed into a
    # fabricated "no reply" state distinct from "not checked yet";
    # there is only one real state here, this table's own `replied_at
    # IS NULL`, matching `waiting_on.py`'s own established meaning for
    # this exact column.
    replied_at: datetime | None


@dataclass(frozen=True)
class KnownRecipient:
    recipient: str
    last_contacted_at: datetime
    message_count: int


async def fetch_recent_drafts(pool: asyncpg.Pool, *, user_id: str, limit: int = _DEFAULT_LIMIT) -> list[EmailDraft]:
    """Real `CREATE_EMAIL_DRAFT` rows this user's own agent has
    genuinely created and the Gate has genuinely approved -- `outcome
    = ANY(SUCCESS_OUTCOMES)` (reused, not re-derived, from `honesty_
    log.py`) rather than a bare literal, so this stays correct if that
    set's own real membership is ever revisited. `draft_id` is read
    from the real, structured `artifact` column (`DEC-191`, migration
    `0022`) -- the first real reader of it for this specific action
    type outside execution itself."""
    rows = await pool.fetch(
        "SELECT proposal_id, resolved_at, payload, artifact FROM action_events "
        "WHERE user_id = $1 AND action_type = $2 AND outcome = ANY($3) "
        "ORDER BY resolved_at DESC LIMIT $4",
        uuid.UUID(user_id), ActionType.CREATE_EMAIL_DRAFT.value, list(SUCCESS_OUTCOMES), limit,
    )
    drafts: list[EmailDraft] = []
    for row in rows:
        payload = json.loads(row["payload"])
        artifact = json.loads(row["artifact"]) if row["artifact"] is not None else None
        drafts.append(
            EmailDraft(
                proposal_id=str(row["proposal_id"]),
                created_at=row["resolved_at"],
                recipient=payload.get("to", ""),
                subject=payload.get("subject"),
                draft_id=artifact.get("draft_id") if artifact else None,
            )
        )
    return drafts


async def fetch_sent_history(pool: asyncpg.Pool, *, user_id: str, limit: int = _DEFAULT_LIMIT) -> list[SentMessageRecord]:
    """Every real sent message this user's own real Gmail poll has
    ever recorded (`sent_messages`, `features/waiting_on.py`'s own real
    table), most recent first -- deliberately unfiltered by `replied_at`
    (unlike `fetch_unreplied_sent_messages()`, that function's own real
    job): this is a real history, not a real action queue, so a real,
    already-replied thread belongs here too."""
    rows = await pool.fetch(
        "SELECT recipient, subject, sent_at, replied_at FROM sent_messages WHERE user_id = $1 ORDER BY sent_at DESC LIMIT $2",
        uuid.UUID(user_id), limit,
    )
    return [
        SentMessageRecord(
            recipient=row["recipient"], subject=row["subject"], sent_at=row["sent_at"], replied_at=row["replied_at"]
        )
        for row in rows
    ]


async def fetch_known_recipients(pool: asyncpg.Pool, *, user_id: str, limit: int = _DEFAULT_LIMIT) -> list[KnownRecipient]:
    """Real, distinct recipients this user has genuinely emailed,
    most-recently-contacted first -- a real, honest trust list built
    from real send history, never a fabricated contacts integration
    this backend has no real source for. A deliberately simpler real
    query than `_fetch_known_recipients()` (`quick_capture.py`): that
    function exists to produce fuzzy-MATCHABLE text for resolving free
    text to one address, a genuinely different real job from this
    one's plain, real "who have I actually emailed" display list --
    kept as two separate, real, independently-purposed queries rather
    than one general-purpose function serving two different real
    callers' own distinct needs."""
    rows = await pool.fetch(
        "SELECT recipient, MAX(sent_at) AS last_contacted_at, COUNT(*) AS message_count "
        "FROM sent_messages WHERE user_id = $1 GROUP BY recipient ORDER BY last_contacted_at DESC LIMIT $2",
        uuid.UUID(user_id), limit,
    )
    return [
        KnownRecipient(recipient=row["recipient"], last_contacted_at=row["last_contacted_at"], message_count=row["message_count"])
        for row in rows
    ]
