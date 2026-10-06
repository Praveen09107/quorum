"""Real, live human approval/rejection for a pending action -- closes a
real, previously-undiscovered gap: no backend route anywhere has ever
let a real, signed-in user actually approve or reject the real
`action_events` row the Gate itself flagged as needing their approval.
"Needs you now" cards have always been real and correctly populated
(`DEC-119`/`127`/`171`) -- there was simply nothing on the other end of
the tap. `action_executor.py`'s own S3 human-approval backstop
(`approved_by_user_id == user_id`) has existed since it was written;
no real caller has ever supplied it. This module is that caller.

REAL, DELIBERATE SCOPE BOUNDARY for `approve_pending_action()`: it only
ever executes a genuine Gate `approve` verdict that did NOT execute
because no human had approved it yet -- today that means exactly
`SEND_EMAIL` and `CREATE_CALENDAR_EVENT_EXTERNAL` (confirmed directly
against `router.STAKES_TABLE`: the only two real S3 action types).
Deliberately does NOT cover an `escalate_to_human` verdict (the Gate
itself couldn't decide -- overriding that is a materially different,
riskier "a human overrides the Gate's own non-decision" design,
genuinely out of scope here, not silently folded in) or
`CREATE_CALENDAR_EVENT_LOCAL` (real, deliberate: no execution target
exists for it anywhere in `action_executor.py` -- there is nothing for
"approve" to actually do).

`reject_pending_action()` is deliberately broader: ANY real, still-
unresolved `action_events` row this user owns can be rejected,
regardless of `gate_decision`/`action_type` -- this is also the one
real, genuine way to clear a `CREATE_CALENDAR_EVENT_LOCAL` row (or an
`escalate_to_human` one) out of "Needs you now" at all, since neither
has a real "approve" path. Rejecting never executes anything; it is a
real, honest "a human looked at this and chose not to act," recorded
as its own new outcome value, not conflated with the Gate's own
`caught_by_gate` (that one must only ever mean the Gate caught a
problem -- a human override is a genuinely different fact, and
`trust_digest.py`'s own real success-rate count would be corrupted by
mislabeling one as the other)."""
from __future__ import annotations

import json
import logging
import uuid

import asyncpg
import httpx

from quorum_backend.auth.google_oauth import GoogleOAuthExchangeFailed
from quorum_backend.auth.google_token_store import get_valid_google_access_token
from quorum_backend.features.action_executor import ExecutionResult, execute_approved_action
from quorum_backend.gate.schemas import ActionType

logger = logging.getLogger("quorum_backend")

# The real, closed set of action types a human can actually approve
# into real execution -- see this module's own top-of-file docstring
# for exactly why `CREATE_CALENDAR_EVENT_LOCAL`/`escalate_to_human`
# rows are deliberately excluded.
_HUMAN_APPROVABLE_ACTION_TYPES = frozenset({ActionType.SEND_EMAIL, ActionType.CREATE_CALENDAR_EVENT_EXTERNAL})

_ALREADY_RESOLVED_DETAIL = "This action has already been resolved."


class PendingActionNotFound(Exception):
    """No real `action_events` row with this `proposal_id` exists for
    this exact user -- deliberately indistinguishable from "exists but
    belongs to someone else," matching `GET /gate_reveal`'s own
    already-established "never confirm another user's data exists"
    discipline."""


class PendingActionNotApprovable(Exception):
    """A real row was found, but it is not a genuine "Gate-approved,
    blocked only on human approval" case: either it's already
    resolved, its `action_type` has no real human-approval execution
    path (`CREATE_CALENDAR_EVENT_LOCAL`), or the Gate itself never
    approved it in the first place (`escalate_to_human`/`reject`/
    `revise`)."""


async def _fetch_and_lock_row(conn: asyncpg.Connection, *, user_id: str, proposal_id: str) -> asyncpg.Record:
    """REAL, DISCLOSED FIX (CRITICAL-tier cross-model review, HIGH-1):
    the original version of this helper was a plain, lock-free SELECT,
    called outside any transaction. Cloud Run's own real `--concurrency
    =1 --max-instances=2` means two real concurrent requests for the
    SAME proposal (a client retry after a slow 15-second Gmail send, two
    devices, a dropped-response retry) can land on two different
    instances, each getting its own DB connection -- both would read
    `resolved_at IS NULL`, and both would go on to execute. Worse, an
    approve and a reject racing the same row could each read NULL, then
    whichever write lands second would silently overwrite the other's
    real outcome -- a real "Rejected -- this will not happen" shown to
    the user while the email had already gone out underneath it, or the
    reverse (a real sent email's `approved_unchanged` row overwritten to
    `rejected_by_user`, corrupting `trust_digest.py`'s own count).

    `FOR UPDATE` makes this a real, genuine row-level lock, enforced by
    Postgres itself across connections/instances (not merely within one
    process) -- the caller MUST hold this inside a transaction and keep
    that transaction open across any later resolution check/write, which
    both `approve_pending_action` and `reject_pending_action` below now
    do."""
    row = await conn.fetchrow(
        "SELECT action_type, payload, gate_decision, resolved_at FROM action_events "
        "WHERE proposal_id = $1 AND user_id = $2 FOR UPDATE",
        uuid.UUID(proposal_id),
        uuid.UUID(user_id),
    )
    if row is None:
        raise PendingActionNotFound(f"No real action_events row {proposal_id!r} exists for this user.")
    return row


async def _resolve_row(
    conn: asyncpg.Connection, *, user_id: str, proposal_id: str, outcome: str, artifact: dict | None = None
) -> None:
    """The real, conditional write side of the same fix: `AND
    resolved_at IS NULL` is real defense in depth (the `FOR UPDATE` lock
    above already makes a genuine race impossible for any caller that
    holds it correctly, but this guards against a future caller that
    doesn't), and checking the real `UPDATE n` status tag -- rather than
    trusting the earlier read -- means a logic error here fails loud
    instead of silently reporting success for a write that touched zero
    rows.

    `artifact` (`DEC-191`, migration `0022`) is the real, structured
    external id Google's own API returned on a successful execution --
    `None` for every non-executed outcome and every action type that
    never calls a Google API, matching the column's own genuinely
    nullable, no-default design."""
    status = await conn.execute(
        "UPDATE action_events SET outcome = $3, resolved_at = now(), artifact = $4::jsonb "
        "WHERE proposal_id = $1 AND user_id = $2 AND resolved_at IS NULL",
        uuid.UUID(proposal_id),
        uuid.UUID(user_id),
        outcome,
        json.dumps(artifact) if artifact is not None else None,
    )
    if status != "UPDATE 1":
        raise PendingActionNotApprovable(_ALREADY_RESOLVED_DETAIL)


async def approve_pending_action(
    pool: asyncpg.Pool,
    *,
    user_id: str,
    proposal_id: str,
    client_id: str | None,
    client_secret: str | None,
    encryption_key: str | None,
    http_client: httpx.AsyncClient | None = None,
) -> ExecutionResult:
    """The real, live approval path. Raises `PendingActionNotFound`/
    `PendingActionNotApprovable` for every real, honest reason this
    specific row cannot be approved right now -- never silently
    no-ops. A real `ExecutionResult` with `executed=False` (never an
    exception) is returned for a genuine, anticipated real-world
    failure during execution itself (no Google account connected, a
    real Google API error, Google OAuth genuinely not configured on
    this deployment) -- the row is deliberately left unresolved in that
    case so a real retry (after re-authorizing, say) remains possible,
    matching `action_executor.py`'s own "never fabricate success"
    discipline.

    REAL, DISCLOSED FIX (found live by this session's own CI run):
    `client_id`/`client_secret`/`encryption_key` are genuinely `None`-
    able -- the real caller (`main.py`'s own route) used to pre-check
    these and refuse with a real 503 before ever reaching this
    function at all, which incorrectly blocked the real 404/409 cases
    below (neither needs a real Google credential). The not-found/
    not-approvable checks below still run first, exactly as before;
    only once execution has genuinely reached the point of needing a
    real Google credential does a missing one produce an honest,
    non-resolving failure, the same shape as "no Google account
    connected."

    REAL, DISCLOSED FIX (CRITICAL-tier cross-model review, HIGH-1/
    HIGH-2): the entire real row-claim-through-resolution sequence now
    runs inside ONE transaction holding a real `FOR UPDATE` lock on this
    row (see `_fetch_and_lock_row`'s own docstring for the exact real
    double-send/mislabel races this closes) -- including the real
    Google API call itself, so a concurrent approve/reject on the same
    row genuinely blocks until this one commits, rather than racing it.
    `execute_approved_action`'s own four Gmail/Calendar branches never
    touch `conn` (confirmed directly against its own docstring), so
    holding `conn`'s transaction open across that real HTTP call creates
    no conflict with the call itself -- it only serializes other real
    requests for this same row.

    A real, third case this fix also closes: `result.executed is None`
    -- `action_executor.py`'s own docstring is explicit that `None`
    means GENUINELY UNKNOWN (a real timeout/dropped connection after the
    real request may already have reached Gmail/Calendar), never
    equivalent to `False`. The original version of this function treated
    anything non-truthy the same way, leaving a real `None` outcome
    unresolved and still `canApprove` -- a real user tapping Approve
    again on a row that may have already sent could cause a genuine
    double-send. `None` is now resolved to the new, honest, distinct
    `outcome_unknown` terminal state (migration `0020`) -- never
    retryable again through this path, and never conflated with a
    confirmed success.

    `http_client` is an optional, real, injectable test seam (`None` in
    every real caller today, including `main.py`'s own route -- a real
    `httpx.AsyncClient` is constructed internally in that case) --
    mirrors `execute_approved_action()`'s own already-established
    injectable `http_client` parameter, letting this module's own tests
    deterministically exercise the real `executed is None` path with a
    fake transport-level failure, the same real double `test_action_
    executor.py` already uses, rather than depending on a genuine live
    Gmail/Calendar timeout to occur."""
    async with pool.acquire() as conn, conn.transaction():
        row = await _fetch_and_lock_row(conn, user_id=user_id, proposal_id=proposal_id)
        if row["resolved_at"] is not None:
            raise PendingActionNotApprovable(_ALREADY_RESOLVED_DETAIL)
        if row["gate_decision"] != "approve":
            raise PendingActionNotApprovable(
                f"The Gate's own verdict on this action was {row['gate_decision']!r}, not 'approve' -- there is "
                "nothing here for a human approval to execute."
            )
        action_type = ActionType(row["action_type"])
        if action_type not in _HUMAN_APPROVABLE_ACTION_TYPES:
            raise PendingActionNotApprovable(
                f"{action_type.value!r} has no real human-approval execution path -- nothing to do here."
            )

        if client_id is None or client_secret is None or encryption_key is None:
            return ExecutionResult(
                executed=False,
                detail="Approving a real action isn't available yet -- Google OAuth isn't fully configured on this deployment.",
            )

        try:
            access_token = await get_valid_google_access_token(
                pool, internal_user_id=user_id, client_id=client_id, client_secret=client_secret, encryption_key=encryption_key
            )
        except GoogleOAuthExchangeFailed:
            logger.warning(
                "Real Google token refresh failed for user_id=%s approving proposal_id=%s -- treated as an "
                "honest execution failure, not a code error.",
                user_id,
                proposal_id,
            )
            return ExecutionResult(executed=False, detail="Your Google account needs to be reconnected before this can be approved.")
        if access_token is None:
            return ExecutionResult(executed=False, detail="No real Google account is connected -- sign in with Google again to approve this.")

        if http_client is not None:
            # The real, injectable test seam (matching `execute_
            # approved_action()`'s own already-established pattern) --
            # used by this module's own real concurrency/outcome-mapping
            # tests to deterministically exercise the `executed is None`
            # path without a real Gmail/Calendar call.
            result = await execute_approved_action(
                conn,
                action_type=action_type,
                payload=json.loads(row["payload"]),
                user_id=user_id,
                approved_by_user_id=user_id,
                google_access_token=access_token,
                http_client=http_client,
            )
        else:
            async with httpx.AsyncClient(timeout=15.0) as real_http_client:
                result = await execute_approved_action(
                    conn,
                    action_type=action_type,
                    payload=json.loads(row["payload"]),
                    user_id=user_id,
                    approved_by_user_id=user_id,
                    google_access_token=access_token,
                    http_client=real_http_client,
                )

        if result.executed is True:
            await _resolve_row(
                conn, user_id=user_id, proposal_id=proposal_id, outcome="approved_unchanged", artifact=result.artifact
            )
        elif result.executed is None:
            await _resolve_row(conn, user_id=user_id, proposal_id=proposal_id, outcome="outcome_unknown")
        # `result.executed is False` is the one real case left
        # deliberately unresolved: a genuine, confirmed non-send
        # (no Google account connected, a real Google API rejection)
        # where a real retry after fixing the real cause remains
        # both safe and possible -- never silently marking a
        # confirmed-failed real execution as done.
        return result


async def reject_pending_action(pool: asyncpg.Pool, *, user_id: str, proposal_id: str) -> None:
    """A real, deliberately broad dismissal: works for ANY real,
    still-unresolved `action_events` row this user owns, regardless of
    `gate_decision`/`action_type` -- including a `CREATE_CALENDAR_
    EVENT_LOCAL` row (no real execution target exists for it; this is
    the one real way to ever clear it from "Needs you now") and an
    `escalate_to_human` row. Never executes anything.

    REAL, DISCLOSED FIX (CRITICAL-tier cross-model review, HIGH-1): now
    also claims the row with a real `FOR UPDATE` lock inside a
    transaction before checking/writing -- without this, a reject
    racing a concurrent approve on the same row could read `resolved_at
    IS NULL` before the approve committed, then overwrite the approve's
    real, already-executed `approved_unchanged` outcome with
    `rejected_by_user`, telling the user "this will not happen" about
    something that already did."""
    async with pool.acquire() as conn, conn.transaction():
        row = await _fetch_and_lock_row(conn, user_id=user_id, proposal_id=proposal_id)
        if row["resolved_at"] is not None:
            raise PendingActionNotApprovable(_ALREADY_RESOLVED_DETAIL)
        await _resolve_row(conn, user_id=user_id, proposal_id=proposal_id, outcome="rejected_by_user")
