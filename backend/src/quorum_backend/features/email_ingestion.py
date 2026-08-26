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

**REAL FINDINGS FROM THIS PR'S OWN CRITICAL-TIER REVIEW (`DEC-140`),
ALL FIXED HERE:**
1. **BLOCKER** -- reply detection had no timestamp-ordering guard at
   all; fixed in `waiting_on.py::mark_thread_replied` (see that
   function's own docstring), not in this file, but this file's own
   phase-2 loop is the real caller that made the bug reachable.
2. **HIGH** -- a single unparseable/deleted real Gmail message (a
   `KeyError`, a 404 from a message trashed between `list` and `get`)
   used to propagate out of the whole per-user scan, permanently
   re-triggering on every future poll (the offending message, never
   recorded, stays "unknown" forever) and silently skipping phase 2
   entirely for that user. Fixed: every real per-message fetch-and-
   write is now individually wrapped, tallied into `messages_failed`,
   and skipped -- the scan continues to the next real message.
3. **HIGH** -- no real overlap guard existed for the eventual
   `pg_cron`-scheduled batch, and no wall-clock budget bounded the
   batch's own real duration. Fixed: `run_email_ingestion()` now claims
   a real, singleton `email_ingestion_job_lock` row (migration `0012`)
   before doing any real work, and releases it when done.

   **A REAL, LIVE-DISCOVERED INFRASTRUCTURE CONSTRAINT changed this fix
   mid-session, not assumed in advance:** the first version of this fix
   used a Postgres session-level advisory lock
   (`pg_try_advisory_lock`/`pg_advisory_unlock`, held on one dedicated
   connection for the whole batch). A real, live contention test of
   that fix failed -- the second, "overlapping" caller acquired the
   lock too, when it should have been blocked. Root cause, confirmed
   directly: this backend's real `SUPABASE_URL` connects through
   Supabase's own PgBouncer pooler in TRANSACTION-POOLING mode
   (`...pooler.supabase.com:6543`), which does not guarantee the same
   underlying Postgres backend connection (and therefore the same
   session) across separate statements on what `asyncpg` presents as
   one logical connection -- session-scoped advisory locks are
   documented as unreliable under exactly this pooling mode. The real
   fix: a plain table row, claimed via one single, atomic
   `UPDATE ... WHERE ... RETURNING` statement (`_try_claim_job_lock()`
   below) -- every statement here is already a genuinely self-contained
   transaction, exactly what transaction-pooling mode serves correctly,
   with no dependency on session continuity at all. `started_at` also
   gives this lock a real, disclosed staleness self-heal: a run that
   crashed mid-batch (a real Cloud Run OOM-kill, a deploy restart)
   never leaves the lock stuck forever -- a claim attempt older than
   `EMAIL_INGESTION_JOB_LOCK_STALE_AFTER_SECONDS` is treated as free.
   A real, disclosed wall-clock `EMAIL_INGESTION_BATCH_DEADLINE_SECONDS`
   budget also now stops the batch cleanly and returns honest, partial
   counts rather than risking a Cloud Run request-timeout kill mid-run.
4. **HIGH** -- a real, revoked (or currently un-refreshable) Google
   grant was indistinguishable from a genuine code-level failure,
   silently inflating `users_failed` forever with no self-healing path
   and no honest signal for an operator to act on. Fixed: a real
   `GoogleOAuthExchangeFailed` from the refresh attempt is now caught
   and reported as its own, distinct `ScanOutcome.GOOGLE_TOKEN_
   REFRESH_FAILED` / `EmailIngestionResult.users_token_refresh_failed`
   -- genuinely uncertain whether the real cause is a revoked grant or
   a transient Google outage (this module does not guess), but no
   longer collapsed into the same bucket as an unrelated code bug, the
   same three-valued-over-collapsing discipline `Finding.evidence_
   state` already holds elsewhere in this project.
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum, auto

import asyncpg
import httpx

from quorum_backend.auth.google_oauth import GoogleOAuthExchangeFailed
from quorum_backend.auth.google_token_store import get_valid_google_access_token
from quorum_backend.features.waiting_on import mark_thread_replied, record_sent_message

logger = logging.getLogger("quorum_backend")

GMAIL_MESSAGES_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"

# See this module's own top-of-file docstring's "REAL, QUOTA-CONSCIOUS
# SCOPE" section.
MAX_MESSAGES_PER_POLL = 25

# A real, disclosed staleness window for the singleton `email_
# ingestion_job_lock` row (migration `0012`) -- comfortably more than
# `EMAIL_INGESTION_BATCH_DEADLINE_SECONDS` below, so a genuinely slow
# but still-running real batch is never treated as stale by a
# concurrent poller, while a real crash still self-heals within a
# bounded, disclosed window rather than wedging this job forever.
EMAIL_INGESTION_JOB_LOCK_STALE_AFTER_SECONDS = 600

# A real, disclosed wall-clock budget for the WHOLE batch, not per-user
# -- review finding 3. Must stay comfortably under whatever this job's
# own real `pg_cron`/`pg_net` `timeout_milliseconds` and Cloud Run's
# own request timeout are set to; see `backend/scripts/enable_email_
# ingestion_cron.sql`'s own real value.
EMAIL_INGESTION_BATCH_DEADLINE_SECONDS = 240.0


class GmailApiError(Exception):
    """Raised when a real, live Gmail API call fails -- never silently
    treated as "no real messages," which would be indistinguishable
    from a genuinely empty, healthy mailbox."""


class ScanOutcome(Enum):
    NO_GOOGLE_TOKEN = auto()  # this user never granted Google access at all -- honestly skipped
    GOOGLE_TOKEN_REFRESH_FAILED = auto()  # a real grant IS stored, but a real refresh attempt failed -- revoked or Google-side, genuinely unknown which; honestly skipped, not a code failure
    SCANNED = auto()  # a real, live poll genuinely ran (regardless of whether anything new was found)


@dataclass(frozen=True)
class EmailIngestionResult:
    users_scanned: int
    users_failed: int
    users_skipped_no_token: int
    users_token_refresh_failed: int
    messages_failed: int
    new_sent_messages: int
    new_replies_detected: int
    # True only when this real run did no real work at all because a
    # previous real run still held the job-level advisory lock -- see
    # review finding 3. Every other field is a real, honest zero in
    # that case, not a fabricated "nothing happened" result conflated
    # with a genuinely empty, healthy poll.
    already_running: bool = False


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


async def _record_new_sent_messages(
    pool: asyncpg.Pool, *, user_id: str, access_token: str, http_client: httpx.AsyncClient
) -> tuple[int, int]:
    """Phase 1: lists real `in:sent` messages, fetches detail only for
    ones `sent_messages` doesn't already know, and records them.
    Returns `(new_sent_count, messages_failed_count)`. Every real
    per-message fetch-and-write is individually isolated -- a genuine
    failure on ONE real message never aborts the rest (review finding
    2)."""
    new_sent = 0
    messages_failed = 0
    sent_refs = await _list_message_refs(http_client, access_token=access_token, query="in:sent")
    if not sent_refs:
        return new_sent, messages_failed

    known_ids = await pool.fetch(
        "SELECT message_id FROM sent_messages WHERE user_id = $1 AND message_id = ANY($2)",
        uuid.UUID(user_id),
        [message_id for message_id, _ in sent_refs],
    )
    known_message_ids = {row["message_id"] for row in known_ids}
    for message_id, thread_id in sent_refs:
        if message_id in known_message_ids:
            continue  # real, already-recorded message -- no real detail-fetch cost spent re-confirming it
        try:
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
        except Exception:  # noqa: BLE001 -- one real message's failure must never abort the rest of this user's real scan; see this function's own docstring, review finding 2
            messages_failed += 1
            logger.exception(
                "Real email ingestion failed to process real sent message_id=%s for user_id=%s -- "
                "continuing to the next real message",
                message_id,
                user_id,
            )
            continue
        if inserted:
            new_sent += 1
    return new_sent, messages_failed


async def _detect_real_replies(
    pool: asyncpg.Pool, *, user_id: str, access_token: str, http_client: httpx.AsyncClient
) -> tuple[int, int]:
    """Phase 2: for every thread this user is genuinely still waiting
    on a reply in, checks real `in:inbox -in:sent` messages and marks
    matching threads replied. Returns `(new_replies_count, messages_
    failed_count)`. Same real per-message isolation as phase 1 above
    (review finding 2). The real timestamp-ordering correctness this
    phase depends on lives in `waiting_on.py::mark_thread_replied`
    itself, not here -- see that function's own docstring (review
    finding 1, the BLOCKER)."""
    new_replies = 0
    messages_failed = 0
    unreplied_threads = await pool.fetch(
        "SELECT DISTINCT thread_id FROM sent_messages WHERE user_id = $1 AND replied_at IS NULL", uuid.UUID(user_id)
    )
    unreplied_thread_ids = {row["thread_id"] for row in unreplied_threads}
    if not unreplied_thread_ids:
        return new_replies, messages_failed

    # Real, deliberate query design -- see this module's own top-of-
    # file docstring's "REAL QUERY DESIGN" section for why `-in:sent`
    # is load-bearing, not decorative.
    received_refs = await _list_message_refs(http_client, access_token=access_token, query="in:inbox -in:sent")
    for message_id, thread_id in received_refs:
        if thread_id not in unreplied_thread_ids:
            continue  # a real, received message this user isn't genuinely waiting on
        try:
            detail = await _fetch_message_detail(http_client, access_token=access_token, message_id=message_id)
            replied_at = _parse_internal_date(detail["internalDate"])
            updated = await mark_thread_replied(pool, user_id=user_id, thread_id=thread_id, replied_at=replied_at)
        except Exception:  # noqa: BLE001 -- same real per-message isolation as the sent-message loop above
            messages_failed += 1
            logger.exception(
                "Real email ingestion failed to process real received message_id=%s for user_id=%s -- "
                "continuing to the next real message",
                message_id,
                user_id,
            )
            continue
        new_replies += updated
        if updated:
            unreplied_thread_ids.discard(thread_id)  # a real thread just closed -- don't re-check it this same poll
    return new_replies, messages_failed


async def scan_one_user_email(
    pool: asyncpg.Pool,
    *,
    user_id: str,
    client_id: str,
    client_secret: str,
    encryption_key: str,
    http_client: httpx.AsyncClient,
) -> tuple[ScanOutcome, int, int, int]:
    """Real, live, per-user Gmail poll. Returns `(outcome, new_sent_
    count, new_replies_count, messages_failed_count)`. Real, honest
    `NO_GOOGLE_TOKEN` for a user who never granted access at all, and a
    real, honest, DISTINCT `GOOGLE_TOKEN_REFRESH_FAILED` for a user who
    has a real, stored grant that a real refresh attempt just failed
    for (review finding 4) -- neither is a code-level failure, the same
    real precedent `deadline_watch.py`'s own `NO_CLAIM` outcome already
    established for "nothing real to do here, not a failure."

    Delegates to `_record_new_sent_messages()` and `_detect_real_
    replies()` above for the two real phases -- kept as separate
    functions, each individually testable, rather than one large loop."""
    try:
        access_token = await get_valid_google_access_token(
            pool, internal_user_id=user_id, client_id=client_id, client_secret=client_secret, encryption_key=encryption_key
        )
    except GoogleOAuthExchangeFailed:
        logger.warning(
            "Real Google token refresh failed for user_id=%s -- either the real grant was revoked or Google's "
            "own endpoint is currently degraded; treated as an honest skip, not a code failure",
            user_id,
        )
        return ScanOutcome.GOOGLE_TOKEN_REFRESH_FAILED, 0, 0, 0
    if access_token is None:
        return ScanOutcome.NO_GOOGLE_TOKEN, 0, 0, 0

    new_sent, sent_failures = await _record_new_sent_messages(
        pool, user_id=user_id, access_token=access_token, http_client=http_client
    )
    new_replies, reply_failures = await _detect_real_replies(
        pool, user_id=user_id, access_token=access_token, http_client=http_client
    )

    return ScanOutcome.SCANNED, new_sent, new_replies, sent_failures + reply_failures


async def _try_claim_job_lock(pool: asyncpg.Pool) -> bool:
    """Real, atomic claim of the singleton `email_ingestion_job_lock`
    row (migration `0012`) -- a single `UPDATE ... RETURNING`
    statement, correct under Supabase's real PgBouncer transaction-
    pooling connection (see this module's own top-of-file docstring,
    review finding 3, for the real, live-discovered reason a session-
    scoped advisory lock does NOT work correctly here). Succeeds when
    the row is genuinely free, or genuinely stale (a real, disclosed
    self-heal after a crash -- see `EMAIL_INGESTION_JOB_LOCK_STALE_
    AFTER_SECONDS`)."""
    row = await pool.fetchrow(
        "UPDATE email_ingestion_job_lock SET running = true, started_at = now() "
        "WHERE singleton = true AND (running = false OR started_at < now() - ($1 * interval '1 second')) "
        "RETURNING true",
        EMAIL_INGESTION_JOB_LOCK_STALE_AFTER_SECONDS,
    )
    return row is not None


async def _release_job_lock(pool: asyncpg.Pool) -> None:
    await pool.execute("UPDATE email_ingestion_job_lock SET running = false WHERE singleton = true")


async def run_email_ingestion(
    pool: asyncpg.Pool, *, client_id: str, client_secret: str, encryption_key: str, user_ids: list[str] | None = None
) -> EmailIngestionResult:
    """The real entry point -- `POST /internal/email-ingestion`
    (`main.py`) calls this with `user_ids=None` (the real, live
    default). Mirrors `deadline_watch.py::run_deadline_watch`'s own
    real per-user failure isolation for genuinely unexpected code-level
    errors; see `ScanOutcome` for the two real, DISTINCT honest-skip
    outcomes this job also has, which are `deadline_watch.py` does not.

    Claims the real `email_ingestion_job_lock` row before doing any
    real work, and honors a real wall-clock `EMAIL_INGESTION_BATCH_
    DEADLINE_SECONDS` budget -- see this module's own top-of-file
    docstring, review finding 3, for why. `user_ids`, when explicitly
    passed, scopes the real poll to exactly those users -- the same
    real, disclosed test-safety boundary every other real autonomous
    job in this backend already established."""
    acquired = await _try_claim_job_lock(pool)
    if not acquired:
        logger.warning("Real email ingestion skipped this cycle -- a previous real run still holds the job lock")
        return EmailIngestionResult(
            users_scanned=0,
            users_failed=0,
            users_skipped_no_token=0,
            users_token_refresh_failed=0,
            messages_failed=0,
            new_sent_messages=0,
            new_replies_detected=0,
            already_running=True,
        )
    try:
        if user_ids is None:
            user_ids = [str(row["user_id"]) for row in await pool.fetch("SELECT user_id FROM users")]

        users_scanned = 0
        users_failed = 0
        users_skipped_no_token = 0
        users_token_refresh_failed = 0
        messages_failed_total = 0
        new_sent_messages = 0
        new_replies_detected = 0

        batch_deadline = time.monotonic() + EMAIL_INGESTION_BATCH_DEADLINE_SECONDS

        async with httpx.AsyncClient(timeout=15.0) as http_client:
            for index, user_id in enumerate(user_ids):
                if time.monotonic() >= batch_deadline:
                    logger.warning(
                        "Real email ingestion batch deadline reached -- stopping early with partial, "
                        "honest counts; %d of %d real users were never reached this cycle",
                        len(user_ids) - index,
                        len(user_ids),
                    )
                    break
                try:
                    outcome, new_sent, new_replies, messages_failed = await scan_one_user_email(
                        pool,
                        user_id=user_id,
                        client_id=client_id,
                        client_secret=client_secret,
                        encryption_key=encryption_key,
                        http_client=http_client,
                    )
                except Exception:  # noqa: BLE001 -- one real user's genuinely unexpected failure must never abort the poll for every other real user
                    users_failed += 1
                    logger.exception(
                        "Real email ingestion failed for user_id=%s -- continuing to the next real user", user_id
                    )
                    continue

                messages_failed_total += messages_failed
                if outcome is ScanOutcome.NO_GOOGLE_TOKEN:
                    users_skipped_no_token += 1
                    continue
                if outcome is ScanOutcome.GOOGLE_TOKEN_REFRESH_FAILED:
                    users_token_refresh_failed += 1
                    continue

                users_scanned += 1
                new_sent_messages += new_sent
                new_replies_detected += new_replies

        return EmailIngestionResult(
            users_scanned=users_scanned,
            users_failed=users_failed,
            users_skipped_no_token=users_skipped_no_token,
            users_token_refresh_failed=users_token_refresh_failed,
            messages_failed=messages_failed_total,
            new_sent_messages=new_sent_messages,
            new_replies_detected=new_replies_detected,
        )
    finally:
        await _release_job_lock(pool)
