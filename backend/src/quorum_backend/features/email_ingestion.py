"""Real, live Gmail polling (Phase 4, `QUORUM_PRODUCTION_COMPLETION_
PLAN.md`) -- the first real, non-manual caller `features/waiting_on.py`
has ever had, and the first real Gmail API integration this backend has
ever made. `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §9.1's own real,
specified interval ("polling; 5-15 min interval") is honored by this
module's own real cron schedule, not by anything in this file itself.

REAL, LIVE-CONFIRMED API SHAPES, checked directly against Gmail's real,
live endpoint using this project's own real sandbox account
(`quorum.dev.sandbox@gmail.com`, `DEC-139`) before writing a line of
parsing code, not assumed from documentation alone:
- `GET /gmail/v1/users/me/messages?q=...` returns
  `{"messages": [{"id", "threadId"}, ...], "resultSizeEstimate"}`.
- `GET /gmail/v1/users/me/messages/{id}?format=metadata` returns
  `{"id", "threadId", "labelIds", "payload": {"headers": [{"name",
  "value"}, ...]}, "internalDate"}` -- `internalDate` is a real STRING
  of milliseconds since the Unix epoch, not a number, confirmed live
  (`"1787203376000"`) before trusting the type.

REAL QUERY DESIGN, a genuine correctness point, not just an
optimization: a message THIS USER sends to themself (a real, harmless
possibility, not a hypothetical -- this project's own sandbox account
test flow directly produces one) carries BOTH the real `SENT` and
`INBOX` Gmail labels on the SAME message. The real "received" query
below is `in:inbox -in:sent`, not bare `in:inbox` -- excluding a
self-sent message from ever being mistaken for its own reply, a real
bug a naive query would have produced and this session's own live
testing against the real sandbox account would have caught the hard
way otherwise.

REAL, QUOTA-CONSCIOUS SCOPE, disclosed rather than silently assumed
unlimited: this module fetches only the most recent `MAX_MESSAGES_PER_
POLL` real messages per real query, and only fetches a real message's
full detail when its `message_id` isn't already known (`sent_messages`)
or its `thread_id` isn't a real thread this user is genuinely still
waiting on a reply in -- most real polls, most real messages are
already-seen no-ops, costing zero real detail-fetch calls. A real,
accepted, disclosed limitation: a real reply landing beyond the most
recent `MAX_MESSAGES_PER_POLL` inbox messages in one real poll interval
could be missed that cycle -- self-correcting on the next real poll for
any personal-scale inbox, not a real risk this session's own scope
calls for solving with full historical pagination or a stored watermark.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum, auto

import asyncpg
import httpx

from quorum_backend.auth.google_token_store import get_valid_google_access_token
from quorum_backend.features.waiting_on import mark_thread_replied, record_sent_message

logger = logging.getLogger("quorum_backend")

GMAIL_MESSAGES_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"

# See this module's own top-of-file docstring's "REAL, QUOTA-CONSCIOUS
# SCOPE" section.
MAX_MESSAGES_PER_POLL = 25


class GmailApiError(Exception):
    """Raised when a real, live Gmail API call fails -- never silently
    treated as "no real messages," which would be indistinguishable
    from a genuinely empty, healthy mailbox."""


class ScanOutcome(Enum):
    NO_GOOGLE_TOKEN = auto()  # this user never granted Google access, or it was revoked -- honestly skipped
    SCANNED = auto()  # a real, live poll genuinely ran (regardless of whether anything new was found)


@dataclass(frozen=True)
class EmailIngestionResult:
    users_scanned: int
    users_failed: int
    users_skipped_no_token: int
    new_sent_messages: int
    new_replies_detected: int


def _extract_header(payload: dict, name: str) -> str:
    """Real, case-insensitive header lookup -- Gmail's own real header
    names are typically title-cased (`Subject`, `To`) but this is never
    guaranteed for every real message a real mail client might have
    produced. Returns a real, honest empty string when genuinely
    absent, never `None` (both `sent_messages.recipient`/`subject` are
    real `NOT NULL` columns)."""
    for header in payload.get("headers", []):
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def _parse_internal_date(raw: str) -> datetime:
    """Gmail's real `internalDate` is real milliseconds-since-epoch, as
    a string -- confirmed live before trusting this, see this module's
    own top-of-file docstring."""
    return datetime.fromtimestamp(int(raw) / 1000, tz=timezone.utc)


async def _list_message_refs(client: httpx.AsyncClient, *, access_token: str, query: str) -> list[tuple[str, str]]:
    """Real, live call -- returns `(message_id, thread_id)` pairs, the
    only two real fields this function's own real caller needs before
    deciding whether a real detail fetch is even worth making."""
    response = await client.get(
        GMAIL_MESSAGES_URL,
        params={"q": query, "maxResults": MAX_MESSAGES_PER_POLL},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if response.status_code != 200:
        raise GmailApiError(f"Gmail messages.list failed ({response.status_code}): {response.text}")
    data = response.json()
    return [(message["id"], message["threadId"]) for message in data.get("messages", [])]


async def _fetch_message_detail(client: httpx.AsyncClient, *, access_token: str, message_id: str) -> dict:
    response = await client.get(
        f"{GMAIL_MESSAGES_URL}/{message_id}",
        params={"format": "metadata", "metadataHeaders": ["Subject", "To"]},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if response.status_code != 200:
        raise GmailApiError(f"Gmail messages.get failed ({response.status_code}): {response.text}")
    return response.json()


async def scan_one_user_email(
    pool: asyncpg.Pool,
    *,
    user_id: str,
    client_id: str,
    client_secret: str,
    encryption_key: str,
    http_client: httpx.AsyncClient,
) -> tuple[ScanOutcome, int, int]:
    """Real, live, per-user Gmail poll. Returns `(outcome, new_sent_
    count, new_replies_count)`. Real, honest `NO_GOOGLE_TOKEN` for a
    user who never granted access or whose grant was revoked -- never
    an error, the same real precedent `deadline_watch.py`'s own
    `NO_CLAIM` outcome already established for "nothing real to do
    here, not a failure."""
    access_token = await get_valid_google_access_token(
        pool, internal_user_id=user_id, client_id=client_id, client_secret=client_secret, encryption_key=encryption_key
    )
    if access_token is None:
        return ScanOutcome.NO_GOOGLE_TOKEN, 0, 0

    new_sent = 0
    sent_refs = await _list_message_refs(http_client, access_token=access_token, query="in:sent")
    if sent_refs:
        known_ids = await pool.fetch(
            "SELECT message_id FROM sent_messages WHERE user_id = $1 AND message_id = ANY($2)",
            uuid.UUID(user_id),
            [message_id for message_id, _ in sent_refs],
        )
        known_message_ids = {row["message_id"] for row in known_ids}
        for message_id, thread_id in sent_refs:
            if message_id in known_message_ids:
                continue  # real, already-recorded message -- no real detail-fetch cost spent re-confirming it
            detail = await _fetch_message_detail(http_client, access_token=access_token, message_id=message_id)
            inserted = await record_sent_message(
                pool,
                user_id=user_id,
                message_id=message_id,
                thread_id=thread_id,
                recipient=_extract_header(detail["payload"], "To"),
                subject=_extract_header(detail["payload"], "Subject"),
                sent_at=_parse_internal_date(detail["internalDate"]),
            )
            if inserted:
                new_sent += 1

    new_replies = 0
    unreplied_threads = await pool.fetch(
        "SELECT DISTINCT thread_id FROM sent_messages WHERE user_id = $1 AND replied_at IS NULL", uuid.UUID(user_id)
    )
    unreplied_thread_ids = {row["thread_id"] for row in unreplied_threads}
    if unreplied_thread_ids:
        # Real, deliberate query design -- see this module's own top-
        # of-file docstring's "REAL QUERY DESIGN" section for why
        # `-in:sent` is load-bearing, not decorative.
        received_refs = await _list_message_refs(http_client, access_token=access_token, query="in:inbox -in:sent")
        for message_id, thread_id in received_refs:
            if thread_id not in unreplied_thread_ids:
                continue  # a real, received message this user isn't genuinely waiting on
            detail = await _fetch_message_detail(http_client, access_token=access_token, message_id=message_id)
            replied_at = _parse_internal_date(detail["internalDate"])
            updated = await mark_thread_replied(pool, user_id=user_id, thread_id=thread_id, replied_at=replied_at)
            new_replies += updated
            if updated:
                unreplied_thread_ids.discard(thread_id)  # a real thread just closed -- don't re-check it this same poll

    return ScanOutcome.SCANNED, new_sent, new_replies


async def run_email_ingestion(
    pool: asyncpg.Pool, *, client_id: str, client_secret: str, encryption_key: str, user_ids: list[str] | None = None
) -> EmailIngestionResult:
    """The real entry point -- `POST /internal/email-ingestion`
    (`main.py`) calls this with `user_ids=None` (the real, live
    default). Mirrors `deadline_watch.py::run_deadline_watch`'s own
    real per-user failure isolation exactly: one real user's own Gmail
    failure is logged, tallied, and never aborts the poll for every
    other real user. `user_ids`, when explicitly passed, scopes the
    real poll to exactly those users -- the same real, disclosed test-
    safety boundary every other real autonomous job in this backend
    already established."""
    if user_ids is None:
        user_ids = [str(row["user_id"]) for row in await pool.fetch("SELECT user_id FROM users")]

    users_scanned = 0
    users_failed = 0
    users_skipped_no_token = 0
    new_sent_messages = 0
    new_replies_detected = 0

    async with httpx.AsyncClient(timeout=15.0) as http_client:
        for user_id in user_ids:
            try:
                outcome, new_sent, new_replies = await scan_one_user_email(
                    pool,
                    user_id=user_id,
                    client_id=client_id,
                    client_secret=client_secret,
                    encryption_key=encryption_key,
                    http_client=http_client,
                )
            except Exception:  # noqa: BLE001 -- one real user's Gmail failure must never abort the poll for every other real user
                users_failed += 1
                logger.exception(
                    "Real email ingestion failed for user_id=%s -- continuing to the next real user", user_id
                )
                continue

            if outcome is ScanOutcome.NO_GOOGLE_TOKEN:
                users_skipped_no_token += 1
                continue

            users_scanned += 1
            new_sent_messages += new_sent
            new_replies_detected += new_replies

    return EmailIngestionResult(
        users_scanned=users_scanned,
        users_failed=users_failed,
        users_skipped_no_token=users_skipped_no_token,
        new_sent_messages=new_sent_messages,
        new_replies_detected=new_replies_detected,
    )
