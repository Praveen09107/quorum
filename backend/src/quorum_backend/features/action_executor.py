"""The real execution layer -- `STATUS_INDEX.md` open item #28, closed
here for the two real domains that are genuinely safe to close it for
(`DEC-128`), and now extended to real Gmail execution (`DEC-142`,
Phase 4's "execution half"). Confirmed by direct search before
`DEC-127` even started designing the `retry_queue` drainer: no code
anywhere in this backend had ever carried out a Gate-approved
`ActionProposal`'s real effect -- every layer built so far (all 5
agents, the Gate, negotiation, the drainer) stopped at producing a
real, verified decision.

FIVE REAL ACTION TYPES ARE NOW GENUINELY, SAFELY EXECUTABLE --
`CREATE_TASK`, `LOG_EXPENSE` (`DEC-128`), and `SEND_EMAIL`/
`ARCHIVE_EMAIL`/`LABEL_EMAIL` (`DEC-142`, real Gmail API calls, using
Phase 3's stored token via `auth/google_token_store.py`) -- confirmed
by checking every other real `ActionType`'s real execution target
before writing a line of code, not assumed:
  - `UPDATE_BUDGET` has no real execution target: no `budgets`-ceiling
    table exists anywhere in this schema (only `expenses`, which
    records transactions, not a ceiling to update) -- the exact same
    real gap `retry_queue_drainer.py`'s own Stage A scope note already
    disclosed for `budget_check`.
  - `CREATE_CALENDAR_EVENT_LOCAL`/`_EXTERNAL` have no real execution
    target either: no `calendar_events` table exists anywhere in this
    schema, and `_EXTERNAL` would additionally need a real Google
    Calendar API call -- real, external, Rule-5-gated scope for Phase 5,
    not this session's.
  - `UPDATE_TASK`/`UPDATE_APPLICATION_STATUS` are never produced by any
    real code path that reaches this function yet (the drainer's own
    translation always produces `CREATE_TASK`, never `UPDATE_TASK`, per
    `negotiation/downstream_translation.py`'s own disclosed reasoning;
    `career` is never a real negotiation domain at all).
  - `CREATE_NOTE` has no real execution target either: no `notes` table
    exists anywhere in this schema (only `note_embeddings`, a genuinely
    different real concept -- Search's own embedding store, not a place
    to persist a note's real content).

That's the 4 real `ActionType`s still genuinely non-executable -- every
one of those returns a real, honest `executed=False` with a real
explanation -- never silently skipped, never fabricated as done.

**A REAL, DISCLOSED GAP FOUND WHILE BUILDING THIS SESSION'S OWN
`SEND_EMAIL` EXECUTION, NOT SILENTLY FIXED OR SILENTLY IGNORED:**
`orchestration.py::review()`'s real Gate state machine does NOT itself
hardcode "S3 always escalates to a human" -- an S2/S3 proposal's final
`decision` (`approve`/`reject`/`revise`/`escalate_to_human`) comes
entirely from the Judge's own real verdict. `CLAUDE.md`'s own
architecture facts state, as an absolute, non-negotiable rule: "S3
(external-irreversible) actions always require explicit human
approval... No exception, ever, regardless of how confident any
automated check is." Nothing in the Gate's own code currently enforces
that as a hard, structural guarantee for S3 specifically -- the Judge
could, in principle, return `approve` for a real S3 action with zero
human ever involved. This is harmless in production TODAY only because
no real code path can currently produce a `SEND_EMAIL`/`CREATE_
CALENDAR_EVENT_EXTERNAL` proposal at all (email and calendar-external
are not real negotiation domains -- `Position.domain` only ever
resolves to `calendar`/`tasks`/`finance`, and no other real caller
exists). Since this module is exactly the function that would carry
out an "approved" S3 action, the missing backstop is added HERE,
structurally, rather than left for some future caller to remember:
`execute_approved_action()` now takes a real, explicit `human_approved`
flag, checked against the real `router.get_stakes()` table -- an S3
action_type is refused outright unless the caller explicitly passes
`human_approved=True`, which no real caller in this backend can
honestly do yet (no real "a human clicked approve on this escalated
action" endpoint exists -- the same already-disclosed, separate open
item this module's own docstring has named since `DEC-128`). This
directly implements a rule `CLAUDE.md` already states, not new,
invented policy.

REAL GMAIL API SHAPES, confirmed live against the real sandbox account
(`quorum.dev.sandbox@gmail.com`) before writing this module's own
`SEND_EMAIL`/`ARCHIVE_EMAIL`/`LABEL_EMAIL` branches, not assumed:
- `POST /gmail/v1/users/me/messages/send` with `{"raw": base64url(...)}`
  returns `200 {"id","threadId","labelIds"}` -- reused directly from
  `features/email_ingestion.py`'s own already-proven send path.
- `POST /gmail/v1/users/me/messages/{id}/modify` with
  `{"removeLabelIds": ["INBOX"]}` (real archive) or
  `{"addLabelIds": [label_id]}` (real label) both return
  `200 {"id","threadId","labelIds"}` with the real, updated label set.

REAL, DISCLOSED SCOPE BOUNDARIES for `ARCHIVE_EMAIL`/`LABEL_EMAIL`,
decided deliberately, not discovered as a blocker partway through: no
agent or route in this backend has ever proposed either of these two
action types (unlike `SEND_EMAIL`, which `agents/email_agent.py`
already proposes, just with no real caller wiring it to the Gate yet),
so this module's own payload shape (`message_id`, and `label_id` for
`LABEL_EMAIL`) is a real, reasoned design choice, not a match to any
pre-existing real contract: `message_id` is Gmail's own real message
identifier (the same real value `features/waiting_on.py`'s own
`sent_messages.message_id` column already stores); `LABEL_EMAIL` here
applies an already-existing real Gmail label by its real `label_id`
directly -- it does NOT create a new label or resolve one by display
name, a real, narrower scope than a hypothetical "label by name"
feature this session was never asked to build.

A REAL, DISCLOSED GAP IN `SEND_EMAIL`'S OWN EXISTING PAYLOAD CONTRACT,
FOUND HERE, NOT SILENTLY WORKED AROUND: `agents/email_agent.py::
build_reply_proposal()` constructs `ActionProposal.payload` as exactly
`{"to": recipient, "body": body}` -- no `subject`, and no `thread_id`
even though `EmailAgentState` carries one. This module honors that
real, existing contract exactly (`payload["to"]`/`payload["body"]`
required, `payload.get("subject", "")` optional), which means a
real, executed `SEND_EMAIL` today sends a genuinely NEW top-level
email, never a real Gmail reply threaded into an existing conversation
-- `email_agent.py`'s own `thread_id` state is real and available but
never actually reaches the real proposal it builds. A real, pre-
existing gap this session found while implementing execution, not
created by it; fixing `email_agent.py` itself is out of this session's
own scope (Rule 3) and is disclosed here rather than silently patched.

A REAL, DISCLOSED, STRUCTURAL RISK FOR ANY FUTURE CALLER, NOT FIXED
HERE (a genuinely new kind of risk `CREATE_TASK`/`LOG_EXPENSE` never
faced, since neither has a real external side effect): this function
runs on the SAME connection/transaction as the caller's own
`action_events` insert (see `retry_queue_drainer.py::_persist_verdict`'s
own real pattern). A real Gmail send can genuinely succeed and then
have the SURROUNDING transaction roll back for an unrelated reason (a
later domain's own persist failure, a dropped connection) -- the real,
already-sent email cannot be un-sent, but the `action_events` row
recording it would vanish, and a naive retry-from-scratch could
resend it. `CREATE_TASK`/`LOG_EXPENSE` never had this problem (a
duplicate internal row is a data-quality issue, not an irreversible
real-world effect visible to another person). ANY future real caller
of this function for `SEND_EMAIL` specifically should either commit
immediately after a successful send (before any other, unrelated work
in the same logical operation continues) or use its own dedicated,
short transaction scoped to just this one write -- the same real
"dual-write" problem `security/supabase_deletion_store.py`'s own
`DEC-113` atomicity gap already disclosed for a different pair of
operations, disclosed here rather than solved with new, unscoped
idempotency-ledger architecture this session was never asked to build.
"""
from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass
from datetime import datetime

import asyncpg
import httpx

from quorum_backend.auth.google_oauth import GoogleOAuthExchangeFailed
from quorum_backend.auth.google_token_store import get_valid_google_access_token
from quorum_backend.features.email_ingestion import GMAIL_MESSAGES_URL, GmailApiError
from quorum_backend.gate.schemas import ActionType, Stakes
from quorum_backend.router import get_stakes

_UNKNOWN_PAYEE = "Unknown"


@dataclass(frozen=True)
class ExecutionResult:
    executed: bool
    detail: str


async def execute_approved_action(
    conn: asyncpg.Connection,
    *,
    action_type: ActionType,
    payload: dict,
    user_id: str,
    human_approved: bool = False,
    google_client_id: str | None = None,
    google_client_secret: str | None = None,
    google_token_encryption_key: str | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> ExecutionResult:
    """Real, live writes for the five real, safely-executable action
    types; a real, honest non-execution for every other real
    `ActionType`. Runs on the SAME connection/transaction the caller is
    already inside (matching `retry_queue_drainer.py`'s own atomicity
    discipline: this write commits or rolls back together with the
    real `action_events` row recording the decision that authorized
    it, never independently) -- see this module's own top-of-file
    docstring for the real, disclosed dual-write risk this creates
    specifically for `SEND_EMAIL`.

    `google_client_id`/`google_client_secret`/`google_token_encryption_
    key`/`http_client` are all optional, defaulting to `None` -- the
    one real caller today (`retry_queue_drainer.py`) never produces a
    real Gmail-executable action type (email is not a real negotiation
    domain), so it never needs to pass them; a real, honest
    `executed=False` is returned for `SEND_EMAIL`/`ARCHIVE_EMAIL`/
    `LABEL_EMAIL` when they're genuinely needed but missing, never a
    crash from an unexpected `None`.

    A REAL, VERIFIED SAFETY PROPERTY THIS FUNCTION RELIES ON, STATED
    EXPLICITLY RATHER THAN LEFT IMPLICIT: `CREATE_TASK`/`LOG_EXPENSE`/
    `ARCHIVE_EMAIL` are all real `Stakes.S1`, and `LABEL_EMAIL` is real
    `Stakes.S0` (confirmed against `router.STAKES_TABLE` before writing
    this) -- `gate/orchestration.py`'s own real state machine means
    Stage B never runs for S0/S1, so `payload` here is always the
    original, already-validated `proposal.payload` for those four,
    never a Judge-revised payload with no schema guarantee. `SEND_
    EMAIL` is real `Stakes.S3` and is handled differently -- see
    `human_approved` above and this module's own top-of-file docstring.
    Still handled defensively below (a real `KeyError`/`TypeError`
    returns a real, honest `executed=False` rather than an unhandled
    exception) so a future stakes-table change fails safely instead of
    silently risking the exact retry-duplication class of bug this
    session's own self-review already found and fixed once in the
    review phase."""
    try:
        return await _execute_approved_action_unsafe(
            conn,
            action_type=action_type,
            payload=payload,
            user_id=user_id,
            human_approved=human_approved,
            google_client_id=google_client_id,
            google_client_secret=google_client_secret,
            google_token_encryption_key=google_token_encryption_key,
            http_client=http_client,
        )
    except (KeyError, TypeError, ValueError) as exc:
        return ExecutionResult(
            executed=False,
            detail=f"Real execution for {action_type.value!r} failed on a malformed payload, not carried out: {exc}",
        )
    except (GmailApiError, GoogleOAuthExchangeFailed, httpx.HTTPError) as exc:
        return ExecutionResult(
            executed=False,
            detail=f"Real execution for {action_type.value!r} failed against Google's real API, not carried out: {exc}",
        )


async def _real_gmail_access_token(
    conn: asyncpg.Connection,
    *,
    user_id: str,
    google_client_id: str | None,
    google_client_secret: str | None,
    google_token_encryption_key: str | None,
) -> tuple[str | None, str | None]:
    """Returns `(access_token, failure_detail)` -- exactly one is
    non-`None`. A real, shared preflight for every real Gmail-executing
    branch below: checks the three real Google config values are all
    present, then fetches a real, currently-usable access token (`None`
    honestly means this user never granted Google access, or it was
    revoked)."""
    if not google_client_id or not google_client_secret or not google_token_encryption_key:
        return None, "no real Google OAuth configuration was provided to this call -- not carried out."
    access_token = await get_valid_google_access_token(
        conn,
        internal_user_id=user_id,
        client_id=google_client_id,
        client_secret=google_client_secret,
        encryption_key=google_token_encryption_key,
    )
    if access_token is None:
        return None, "this user has no real, stored Google grant (never connected, or revoked) -- not carried out."
    return access_token, None


async def _execute_approved_action_unsafe(
    conn: asyncpg.Connection,
    *,
    action_type: ActionType,
    payload: dict,
    user_id: str,
    human_approved: bool,
    google_client_id: str | None,
    google_client_secret: str | None,
    google_token_encryption_key: str | None,
    http_client: httpx.AsyncClient | None,
) -> ExecutionResult:
    if action_type == ActionType.CREATE_TASK:
        deadline_iso = payload.get("deadline")
        await conn.execute(
            "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) "
            "VALUES ($1, $2, $3, $4, $5, 'open')",
            uuid.uuid4(),
            uuid.UUID(user_id),
            payload["title"],
            payload["estimated_hours"],
            datetime.fromisoformat(deadline_iso) if deadline_iso else None,
        )
        return ExecutionResult(executed=True, detail="Real task row created.")

    if action_type == ActionType.LOG_EXPENSE:
        # A real, honest, live-found fact, not a bug: `payload["category"]`
        # (real, translated content) is genuinely NOT persisted here --
        # the real `expenses` table (migration 0001) has no `category`
        # column at all, confirmed directly before writing this insert.
        # The translated category still survives in the real
        # `action_events.payload` JSONB the caller already persists
        # alongside this write, just not in a dedicated `expenses`
        # column -- disclosed here rather than silently dropped without
        # a trace, or worked around by inventing a new column this
        # session's real scope never called for.
        await conn.execute(
            "INSERT INTO expenses (expense_id, user_id, payee, amount, occurred_at, source) "
            "VALUES ($1, $2, $3, $4, now(), 'gate_approved')",
            uuid.uuid4(),
            uuid.UUID(user_id),
            payload.get("payee") or _UNKNOWN_PAYEE,
            payload["amount"],
        )
        return ExecutionResult(executed=True, detail="Real expense row created.")

    if action_type == ActionType.SEND_EMAIL:
        # See this module's own top-of-file docstring's "A REAL,
        # DISCLOSED GAP FOUND WHILE BUILDING..." section -- this is the
        # real, structural backstop CLAUDE.md's own absolute S3 rule
        # requires, since nothing in `gate/orchestration.py` itself
        # forces an S3 proposal to escalate.
        if get_stakes(action_type) == Stakes.S3 and not human_approved:
            return ExecutionResult(
                executed=False,
                detail=(
                    "SEND_EMAIL is real Stakes.S3 (external, irreversible) and requires a real, explicit "
                    "human_approved=True this call did not provide -- never auto-executed on a Gate verdict "
                    "alone, per CLAUDE.md's own absolute rule. No real 'a human clicked approve on this "
                    "escalated action' endpoint exists yet either."
                ),
            )
        access_token, failure = await _real_gmail_access_token(
            conn,
            user_id=user_id,
            google_client_id=google_client_id,
            google_client_secret=google_client_secret,
            google_token_encryption_key=google_token_encryption_key,
        )
        if failure is not None:
            return ExecutionResult(executed=False, detail=f"Real SEND_EMAIL execution skipped -- {failure}")
        if http_client is None:
            return ExecutionResult(executed=False, detail="Real SEND_EMAIL execution skipped -- no real HTTP client was provided to this call.")

        # Real, honest match to `agents/email_agent.py::build_reply_
        # proposal()`'s own existing payload shape -- see this module's
        # own top-of-file docstring for the real, disclosed `subject`/
        # `thread_id` gap that shape carries.
        raw_message = (
            f"To: {payload['to']}\r\n"
            f"Subject: {payload.get('subject', '')}\r\n"
            "Content-Type: text/plain; charset=UTF-8\r\n\r\n"
            f"{payload['body']}"
        )
        encoded = base64.urlsafe_b64encode(raw_message.encode()).decode()
        response = await http_client.post(
            f"{GMAIL_MESSAGES_URL}/send",
            json={"raw": encoded},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.status_code != 200:
            raise GmailApiError(f"Gmail messages.send failed ({response.status_code}): {response.text}")
        real_message_id = response.json()["id"]
        return ExecutionResult(executed=True, detail=f"Real email sent via Gmail (message_id={real_message_id!r}).")

    if action_type in (ActionType.ARCHIVE_EMAIL, ActionType.LABEL_EMAIL):
        access_token, failure = await _real_gmail_access_token(
            conn,
            user_id=user_id,
            google_client_id=google_client_id,
            google_client_secret=google_client_secret,
            google_token_encryption_key=google_token_encryption_key,
        )
        if failure is not None:
            return ExecutionResult(executed=False, detail=f"Real {action_type.value} execution skipped -- {failure}")
        if http_client is None:
            return ExecutionResult(
                executed=False, detail=f"Real {action_type.value} execution skipped -- no real HTTP client was provided to this call."
            )

        message_id = payload["message_id"]
        modify_body = (
            {"removeLabelIds": ["INBOX"]}
            if action_type == ActionType.ARCHIVE_EMAIL
            else {"addLabelIds": [payload["label_id"]]}
        )
        response = await http_client.post(
            f"{GMAIL_MESSAGES_URL}/{message_id}/modify",
            json=modify_body,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.status_code != 200:
            raise GmailApiError(f"Gmail messages.modify failed ({response.status_code}): {response.text}")
        verb = "archived" if action_type == ActionType.ARCHIVE_EMAIL else "labeled"
        return ExecutionResult(executed=True, detail=f"Real Gmail message {verb} (message_id={message_id!r}).")

    return ExecutionResult(
        executed=False,
        detail=f"No real execution path exists yet for {action_type.value!r} -- decision recorded, not carried out.",
    )
