"""The real execution layer -- `STATUS_INDEX.md` open item #28, closed
here for the two real domains that are genuinely safe to close it for
(`DEC-128`), extended to real Gmail execution (`DEC-142`, Phase 4's
"execution half"), and now to a real budget-ceiling write (`DEC-148`,
Phase 6). Confirmed by direct search before `DEC-127` even started
designing the `retry_queue` drainer: no code anywhere in this backend
had ever carried out a Gate-approved `ActionProposal`'s real effect --
every layer built so far (all 5 agents, the Gate, negotiation, the
drainer) stopped at producing a real, verified decision.

SIX REAL ACTION TYPES ARE NOW GENUINELY, SAFELY EXECUTABLE --
`CREATE_TASK`, `LOG_EXPENSE` (`DEC-128`), `SEND_EMAIL`/`ARCHIVE_EMAIL`/
`LABEL_EMAIL` (`DEC-142`, real Gmail API calls, using Phase 3's stored
token), and `UPDATE_BUDGET` (`DEC-148`, a real, direct `users.
monthly_budget_limit` write, migration `0015`, closing the exact gap
this docstring's own earlier version named -- "no `budgets`-ceiling
table exists anywhere in this schema" -- by adding the real, small
column that gap actually needed, not a separate table). Confirmed by
checking every other real `ActionType`'s real execution target before
writing a line of code:
  - `CREATE_CALENDAR_EVENT_LOCAL`/`_EXTERNAL` have no real execution
    target either: no `calendar_events` table exists anywhere in this
    schema, and `_EXTERNAL` would additionally need a real Google
    Calendar API call -- real, external, Rule-5-gated scope for Phase 5.
  - `UPDATE_TASK`/`UPDATE_APPLICATION_STATUS` are never produced by any
    real code path that reaches this function yet.
  - `CREATE_NOTE` has no real execution target either: no `notes` table
    exists anywhere in this schema.

**A REAL, DISCLOSED GAP FOUND WHILE BUILDING THIS SESSION'S OWN
`SEND_EMAIL` EXECUTION:** `orchestration.py::review()`'s real Gate
state machine does NOT itself hardcode "S3 always escalates to a
human" -- an S2/S3 proposal's final `decision` comes entirely from the
Judge's own real verdict, confirmed directly by reading `review()`
(S2/S3 both reach `run_stage_b()` and its returned `GateVerdict` is
used as-is; nothing there forces `escalate_to_human` for S3
specifically). `CLAUDE.md`'s own architecture facts state, as an
absolute, non-negotiable rule: "S3 (external-irreversible) actions
always require explicit human approval... No exception, ever." This is
harmless in production TODAY only because no real code path can
currently produce a `SEND_EMAIL`/`CREATE_CALENDAR_EVENT_EXTERNAL`
proposal at all (neither is a real negotiation domain). Since this
module is exactly the function that would carry out an "approved" S3
action, the missing backstop is added HERE, structurally -- checked
ONCE, before every branch below, for ANY real S3 action type (not
hand-added inside one branch, which a future `CREATE_CALENDAR_EVENT_
EXTERNAL` branch could easily forget): `execute_approved_action()`
takes a real, explicit `approved_by_user_id` -- an S3 action_type is
refused outright unless it equals the real `user_id` this call is
already scoped to, meaning a caller must hold a genuine, verified
identity for who approved it, not merely a bare `True`/`False` that
could be set to `verdict.decision == "approve"` by mistake (the exact
confusion this fix exists to prevent). No real caller in this backend
can honestly provide this yet (no real "a human clicked approve on
this escalated action" endpoint exists), so `SEND_EMAIL` still can't
fire through any real path today.

REAL GMAIL API SHAPES, confirmed live against the real sandbox account
(`quorum.dev.sandbox@gmail.com`) before writing this module's own
`SEND_EMAIL`/`ARCHIVE_EMAIL`/`LABEL_EMAIL` branches:
- `POST /gmail/v1/users/me/messages/send` with `{"raw": base64url(...)}`
  returns `200 {"id","threadId","labelIds"}`.
- `POST /gmail/v1/users/me/messages/{id}/modify` with
  `{"removeLabelIds": ["INBOX"]}` (real archive) or
  `{"addLabelIds": [label_id]}` (real label) both return
  `200 {"id","threadId","labelIds"}` with the real, updated label set.

REAL, DISCLOSED SCOPE BOUNDARIES for `ARCHIVE_EMAIL`/`LABEL_EMAIL`: no
agent or route in this backend has ever proposed either action type
(unlike `SEND_EMAIL`, which `agents/email_agent.py` already proposes,
just with no real caller wiring it to the Gate yet), so this module's
own payload shape (`message_id`, and `label_id` for `LABEL_EMAIL`) is a
real, reasoned design choice: `message_id` is Gmail's own real message
identifier; `LABEL_EMAIL` applies an already-existing real Gmail label
by its real `label_id` directly -- it does NOT create a new label or
resolve one by display name. A real, disclosed gap this leaves open:
no `labels.list` call or label-id constant exists anywhere in this
codebase yet, so a real future caller has no discovery path today and
must already know a valid real Gmail label id (a system label like
`IMPORTANT`, or a real user label's own real id) -- a real, narrower
scope than a hypothetical "label by name" feature this session was
never asked to build.

A REAL, DISCLOSED GAP IN `SEND_EMAIL`'S OWN EXISTING PAYLOAD CONTRACT:
`agents/email_agent.py::build_reply_proposal()` constructs `ActionProposal.
payload` as exactly `{"to": recipient, "body": body}` -- no `subject`,
and no `thread_id` even though `EmailAgentState` carries one. This
module honors that real, existing contract exactly (`payload["to"]`/
`payload["body"]` required, `payload.get("subject", "")` optional),
which means a real, executed `SEND_EMAIL` today sends a genuinely NEW
top-level email, never a real Gmail reply threaded into an existing
conversation. A real, pre-existing gap this session found while
implementing execution, not created by it; fixing `email_agent.py`
itself is out of this session's own scope (Rule 3).

A REAL, LIVE-FOUND SECURITY GAP, FIXED HERE BEFORE ANY REAL SEND EVER
HAPPENED: `payload["to"]`/`payload.get("subject")` were originally
interpolated directly into raw RFC 5322 header lines -- a real header-
injection vector (a real `to` value containing an embedded `\r\n` could
inject an arbitrary `Bcc:` header, or terminate the header block early
and replace the entire message body) into a real, irreversible S3
send. Reachable in two real ways: `agents/email_agent.py`'s own
`recipient` is real, external, untrusted text in any real wiring (an
inbound message's own `From` header); and a genuine S3 `approve`
verdict can carry a Judge-authored `revised_payload` with no schema
guarantee beyond being a `dict` (`gate/orchestration.py`'s own real
`review()`, confirmed directly). Fixed by building the real MIME
message via the stdlib `email.message.EmailMessage` (which genuinely
raises `ValueError` on an embedded CR/LF in a header value -- confirmed
directly, not assumed) plus an explicit, defensive pre-check.

A REAL, DISCLOSED, THREE-VALUED OUTCOME FOR THE GMAIL NETWORK CALLS,
matching this project's own `Finding.evidence_state` discipline (never
collapse "genuinely unknown" into a flat pass or fail): a real Gmail
API call returning any HTTP response (even a non-200, even one whose
body fails to parse) settles the outcome definitely -- `executed=True`
for a real `200`, `executed=False` for anything else. A genuine
TRANSPORT-level failure (a timeout, a dropped connection) settles
NOTHING -- Gmail may have already processed the request -- so
`ExecutionResult.executed` is `None` in that one specific case, never
silently folded into `False` (which a caller could misread as "no real
email was sent").

A REAL, DISCLOSED, DURABLE LOG for every real, executed Gmail action --
`ExecutionResult.detail` alone lives only in the SAME transaction that
can roll back (see the dual-write risk below); a `logger.warning()`
right after a real, successful Gmail call is written to Cloud Run's
own real, transaction-independent log sink, giving a human a real,
greppable record to reconcile against even if the surrounding
transaction is later lost.

A REAL, DISCLOSED, STRUCTURAL RISK FOR ANY FUTURE CALLER, NOT
STRUCTURALLY FIXED HERE (a genuinely new kind of risk `CREATE_TASK`/
`LOG_EXPENSE` never faced, since neither has a real external side
effect): this function runs on the SAME connection/transaction as the
caller's own `action_events` insert (see `retry_queue_drainer.py::
_persist_verdict`'s own real pattern). A real Gmail send can genuinely
succeed and then have the SURROUNDING transaction roll back for an
unrelated reason -- the real, already-sent email cannot be un-sent, but
the `action_events` row recording it would vanish, and a naive retry-
from-scratch could resend it. Mitigated, not eliminated, by the real,
durable log above. ANY future real caller of this function for `SEND_
EMAIL` specifically should either commit immediately after a
successful send or use its own dedicated, short transaction scoped to
just this one write -- the same real "dual-write" problem `security/
supabase_deletion_store.py`'s own `DEC-113` atomicity gap already
disclosed for a different pair of operations.

A REAL, DELIBERATE DESIGN CHOICE ABOUT HOW A REAL GOOGLE ACCESS TOKEN
REACHES THIS FUNCTION, changed during this session's own CRITICAL-tier
review: this function takes an ALREADY-RESOLVED `google_access_token`,
never a client id/secret/encryption key to resolve one itself. An
earlier version called `auth/google_token_store.py::get_valid_google_
access_token()` directly on the caller's own `conn` -- which meant a
real token-refresh write (when the stored token was near expiry) ran
INSIDE the caller's own transaction, so a later, unrelated rollback in
that same transaction would discard a real, already-issued Google
access token, and `access_token_expires_at` would never advance
(worsening that function's own already-disclosed "burns refresh grants
with zero forward progress" risk from "only under a degraded database"
to "on any ordinary rollback"). Fixed by pushing token resolution to
the CALLER: any future real caller must resolve a real access token via
`get_valid_google_access_token(pool, ...)` against the real POOL,
BEFORE opening its own transaction, then pass the resulting string in
here -- this function itself never touches `google_oauth_tokens` at
all, so it has no transaction-coupling risk to disclose in the first
place.
"""
from __future__ import annotations

import base64
import logging
import math
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage

import asyncpg
import httpx

from quorum_backend.features.email_ingestion import GMAIL_MESSAGES_URL
from quorum_backend.gate.schemas import ActionType, Stakes
from quorum_backend.router import get_stakes

logger = logging.getLogger("quorum_backend")

_UNKNOWN_PAYEE = "Unknown"

# A real, live-confirmed shape for both a real Gmail message id and a
# real Gmail label id -- neither one this project has ever seen
# contain anything but this real, narrow character set. Rejected
# outright rather than interpolated unchecked into a real URL path.
_REAL_GMAIL_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class ExecutionResult:
    # `None` is a real, distinct, third state -- see this module's own
    # top-of-file docstring's "THREE-VALUED OUTCOME" section. Never
    # treat `None` as equivalent to `False`: it means genuinely
    # UNKNOWN, not "did not happen."
    executed: bool | None
    detail: str


def _reject_header_injection(value: str, *, field_name: str) -> None:
    if "\r" in value or "\n" in value:
        raise ValueError(
            f"Real {field_name!r} value contains an embedded newline -- refused as a real header-injection "
            "attempt, not carried out."
        )


def _reject_malformed_gmail_id(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or not _REAL_GMAIL_ID_PATTERN.fullmatch(value):
        raise ValueError(f"Real {field_name!r} value {value!r} does not look like a real Gmail id -- not carried out.")


async def execute_approved_action(
    conn: asyncpg.Connection,
    *,
    action_type: ActionType,
    payload: dict,
    user_id: str,
    approved_by_user_id: str | None = None,
    google_access_token: str | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> ExecutionResult:
    """Real, live writes for the five real, safely-executable action
    types; a real, honest non-execution for every other real
    `ActionType`. Runs on the SAME connection/transaction the caller is
    already inside for `CREATE_TASK`/`LOG_EXPENSE` (matching `retry_
    queue_drainer.py`'s own atomicity discipline) -- the three real
    Gmail-executing branches never touch `conn` at all; see this
    module's own top-of-file docstring for why.

    `approved_by_user_id`/`google_access_token`/`http_client` are all
    optional, defaulting to `None` -- the one real caller today
    (`retry_queue_drainer.py`) never produces a real Gmail-executable
    action type (email is not a real negotiation domain), so it never
    needs to pass them; a real, honest `executed=False` is returned for
    `SEND_EMAIL`/`ARCHIVE_EMAIL`/`LABEL_EMAIL` when they're genuinely
    needed but missing, never a crash from an unexpected `None`.

    A REAL, VERIFIED SAFETY PROPERTY THIS FUNCTION RELIES ON, STATED
    EXPLICITLY RATHER THAN LEFT IMPLICIT: `CREATE_TASK`/`LOG_EXPENSE`/
    `ARCHIVE_EMAIL` are all real `Stakes.S1`, and `LABEL_EMAIL` is real
    `Stakes.S0` (confirmed against `router.STAKES_TABLE`) --
    `gate/orchestration.py`'s own real state machine means Stage B
    never runs for S0/S1, so `payload` here is always the original,
    already-validated `proposal.payload` for those four. `SEND_EMAIL`
    is real `Stakes.S3` and is checked once, structurally, before every
    branch -- see `approved_by_user_id` above and this module's own
    top-of-file docstring. Still handled defensively below (a real
    `KeyError`/`TypeError`/`ValueError` returns a real, honest
    `executed=False` rather than an unhandled exception)."""
    try:
        return await _execute_approved_action_unsafe(
            conn,
            action_type=action_type,
            payload=payload,
            user_id=user_id,
            approved_by_user_id=approved_by_user_id,
            google_access_token=google_access_token,
            http_client=http_client,
        )
    except (KeyError, TypeError, ValueError) as exc:
        return ExecutionResult(
            executed=False,
            detail=f"Real execution for {action_type.value!r} failed on a malformed payload, not carried out: {exc}",
        )


async def _real_gmail_post(
    http_client: httpx.AsyncClient,
    url: str,
    body: dict,
    *,
    access_token: str,
    action_type: ActionType,
    user_id: str,
) -> ExecutionResult:
    """The real, shared core for every Gmail-modifying call this
    module makes -- see this module's own top-of-file docstring's
    "THREE-VALUED OUTCOME" section for why a transport failure and a
    definite Gmail-side rejection are genuinely different real
    outcomes, never collapsed into one."""
    try:
        response = await http_client.post(url, json=body, headers={"Authorization": f"Bearer {access_token}"})
    except httpx.HTTPError as exc:
        return ExecutionResult(
            executed=None,
            detail=(
                f"Real execution for {action_type.value!r} is genuinely UNKNOWN -- a transport-level failure "
                f"happened while calling Google's real API; a real send/modify may or may not have gone "
                f"through, never assume it did not: {exc}"
            ),
        )
    if response.status_code != 200:
        return ExecutionResult(
            executed=False,
            detail=f"Real execution for {action_type.value!r} was genuinely rejected by Google's real API "
            f"({response.status_code}), not carried out: {response.text}",
        )
    try:
        response_body = response.json()
    except ValueError:
        response_body = {}
    real_message_id = response_body.get("id", "<unknown>")
    real_label_ids = response_body.get("labelIds", [])
    logger.warning(
        "Real Gmail %s executed for user_id=%s message_id=%s labelIds=%s",
        action_type.value, user_id, real_message_id, real_label_ids,
    )
    return ExecutionResult(
        executed=True,
        detail=f"Real Gmail {action_type.value} call succeeded (message_id={real_message_id!r}); "
        f"real, current labelIds={real_label_ids!r}.",
    )


async def _execute_approved_action_unsafe(
    conn: asyncpg.Connection,
    *,
    action_type: ActionType,
    payload: dict,
    user_id: str,
    approved_by_user_id: str | None,
    google_access_token: str | None,
    http_client: httpx.AsyncClient | None,
) -> ExecutionResult:
    # A real, structural, checked-once backstop for EVERY real S3
    # action type, not one hand-added inside a single branch -- see
    # this module's own top-of-file docstring for the real Gate gap
    # this closes.
    if get_stakes(action_type) == Stakes.S3 and approved_by_user_id != user_id:
        return ExecutionResult(
            executed=False,
            detail=(
                f"{action_type.value!r} is real Stakes.S3 (external, irreversible) and requires a real, "
                f"verified approved_by_user_id matching this exact user -- this call did not provide one. "
                "Never auto-executed on a Gate verdict alone, per CLAUDE.md's own absolute rule. No real "
                "'a human clicked approve on this escalated action' endpoint exists yet either."
            ),
        )

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

    if action_type == ActionType.UPDATE_BUDGET:
        # RESOLVED, `DEC-148`: closes the real gap this module's own
        # top-of-file docstring named -- `users.monthly_budget_limit`
        # (migration `0015`) is the real, genuine, small budgets-ceiling
        # concept that never existed before. `payload["amount"]`, per
        # `agents/finance_agent.py::build_finance_proposal`'s own real,
        # existing contract, is the real NEW ceiling itself (not a
        # delta) -- confirmed directly against that function and
        # `negotiation/downstream_translation.py`'s own real translation
        # prompt ("changing a real budget ceiling itself") before
        # writing this branch, not assumed.
        #
        # A real, structural safety check, not left implicit: every
        # real per-user computation that divides by this value
        # (`today.py::compute_budget_state`, `negotiation_detail_
        # backfill.py::_build_baseline`'s own `budget_remaining_
        # fraction`) would produce a real division-by-zero or an
        # inverted-sign fraction for a non-positive real ceiling -- a
        # genuinely different, worse failure mode than a merely
        # implausible one, so rejected here before any real write,
        # the same "reject a structurally unsafe value outright" choice
        # `_reject_header_injection`/`_reject_malformed_gmail_id` above
        # already make for their own real inputs. Raising `ValueError`
        # here is deliberate, not an oversight -- the shared `except`
        # in `execute_approved_action()` above turns it into the same
        # real, honest `executed=False` every other malformed-payload
        # case already gets.
        new_limit = payload["amount"]
        # `math.isfinite()` is load-bearing, not decorative: a real
        # `float('nan')` genuinely satisfies `nan <= 0 == False` in
        # live, hand-verified Python (NaN compares False against every
        # relational operator except `!=`), and `float('inf')` also
        # satisfies `inf <= 0 == False` -- both would silently slip past
        # a bare `new_limit <= 0` check and then corrupt every real
        # downstream division by this value (`compute_budget_state`,
        # `_build_baseline`'s own `budget_remaining_fraction`) with a
        # real, silent `NaN`/`0.0` result, never a loud failure.
        if (
            isinstance(new_limit, bool)
            or not isinstance(new_limit, (int, float))
            or not math.isfinite(new_limit)
            or new_limit <= 0
        ):
            raise ValueError(f"real UPDATE_BUDGET amount must be a real, finite, positive number, got {new_limit!r}")

        # A real, honest, live-found fact, matching LOG_EXPENSE's own
        # already-disclosed precedent immediately below: `payload
        # ["category"]` (real, translated content) is genuinely NOT
        # persisted here -- this is a single, whole-account monthly
        # ceiling, not a per-category one. The real, translated category
        # still survives in the real `action_events.payload` JSONB the
        # caller already persists alongside this write.
        await conn.execute(
            "UPDATE users SET monthly_budget_limit = $1 WHERE user_id = $2",
            float(new_limit),
            uuid.UUID(user_id),
        )
        return ExecutionResult(executed=True, detail=f"Real monthly budget limit updated to {float(new_limit)!r}.")

    if action_type == ActionType.LOG_EXPENSE:
        # A real, honest, live-found fact, not a bug: `payload["category"]`
        # (real, translated content) is genuinely NOT persisted here --
        # the real `expenses` table (migration 0001) has no `category`
        # column at all. The translated category still survives in the
        # real `action_events.payload` JSONB the caller already
        # persists alongside this write.
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
        if google_access_token is None:
            return ExecutionResult(executed=False, detail="Real SEND_EMAIL execution skipped -- no real Google access token was provided to this call.")
        if http_client is None:
            return ExecutionResult(executed=False, detail="Real SEND_EMAIL execution skipped -- no real HTTP client was provided to this call.")

        # Real, honest match to `agents/email_agent.py::build_reply_
        # proposal()`'s own existing payload shape -- see this module's
        # own top-of-file docstring for the real, disclosed `subject`/
        # `thread_id` gap that shape carries. Real fields validated
        # BEFORE any network call, and BEFORE building a real MIME
        # message, per this module's own real header-injection fix.
        to = payload["to"]
        body_text = payload["body"]
        subject = payload.get("subject", "")
        _reject_header_injection(to, field_name="to")
        _reject_header_injection(subject, field_name="subject")

        message = EmailMessage()
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body_text)
        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()

        return await _real_gmail_post(
            http_client, f"{GMAIL_MESSAGES_URL}/send", {"raw": encoded},
            access_token=google_access_token, action_type=action_type, user_id=user_id,
        )

    if action_type in (ActionType.ARCHIVE_EMAIL, ActionType.LABEL_EMAIL):
        if google_access_token is None:
            return ExecutionResult(executed=False, detail=f"Real {action_type.value} execution skipped -- no real Google access token was provided to this call.")
        if http_client is None:
            return ExecutionResult(executed=False, detail=f"Real {action_type.value} execution skipped -- no real HTTP client was provided to this call.")

        # Real payload fields validated BEFORE any network call.
        message_id = payload["message_id"]
        _reject_malformed_gmail_id(message_id, field_name="message_id")
        if action_type == ActionType.ARCHIVE_EMAIL:
            modify_body = {"removeLabelIds": ["INBOX"]}
        else:
            label_id = payload["label_id"]
            _reject_malformed_gmail_id(label_id, field_name="label_id")
            modify_body = {"addLabelIds": [label_id]}

        return await _real_gmail_post(
            http_client, f"{GMAIL_MESSAGES_URL}/{message_id}/modify", modify_body,
            access_token=google_access_token, action_type=action_type, user_id=user_id,
        )

    return ExecutionResult(
        executed=False,
        detail=f"No real execution path exists yet for {action_type.value!r} -- decision recorded, not carried out.",
    )
