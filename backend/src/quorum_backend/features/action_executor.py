"""The real execution layer -- `STATUS_INDEX.md` open item #28, closed
here for the two real domains that are genuinely safe to close it for
(`DEC-128`), extended to real Gmail execution (`DEC-142`, Phase 4's
"execution half"), and now to a real budget-ceiling write (`DEC-148`,
Phase 6). Confirmed by direct search before `DEC-127` even started
designing the `retry_queue` drainer: no code anywhere in this backend
had ever carried out a Gate-approved `ActionProposal`'s real effect --
every layer built so far (all 5 agents, the Gate, negotiation, the
drainer) stopped at producing a real, verified decision.

SEVEN REAL ACTION TYPES ARE NOW GENUINELY, SAFELY EXECUTABLE --
`CREATE_TASK`, `LOG_EXPENSE` (`DEC-128`), `SEND_EMAIL`/`ARCHIVE_EMAIL`/
`LABEL_EMAIL` (`DEC-142`, real Gmail API calls, using Phase 3's stored
token), `UPDATE_BUDGET` (`DEC-148`, a real, direct `users.
monthly_budget_limit` write, migration `0015`, closing the exact gap
this docstring's own earlier version named -- "no `budgets`-ceiling
table exists anywhere in this schema" -- by adding the real, small
column that gap actually needed, not a separate table), and
`CREATE_CALENDAR_EVENT_EXTERNAL` (`DEC-151`, Phase 5, a real Google
Calendar API call, also using Phase 3's stored token). Confirmed by
checking every other real `ActionType`'s real execution target before
writing a line of code:
  - `CREATE_CALENDAR_EVENT_LOCAL` still has no real execution target:
    no `calendar_events` table exists anywhere in this schema, and a
    real local event's own ground truth genuinely belongs on-device
    (the mobile `device_calendar` integration, `mobile/lib/features/
    calendar_sync.dart`), not server-side -- a real, deliberate Phase 5
    scope boundary, not an oversight; see this docstring's own
    `CREATE_CALENDAR_EVENT_EXTERNAL` section below for why only the
    external case genuinely needs a server-side Google API call at all.
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

REAL GOOGLE CALENDAR API SHAPES, confirmed live against the real
sandbox account (`quorum.dev.sandbox@gmail.com`) before writing this
module's own `CREATE_CALENDAR_EVENT_EXTERNAL` branch (`DEC-151`) -- a
real test event was created with the sandbox account itself as the
invitee (to avoid emailing a real, uninvolved person) and then really
deleted afterward as cleanup, confirming the full create-then-verify-
then-clean-up cycle works, not just the create call in isolation:
- `POST https://www.googleapis.com/calendar/v3/calendars/primary/
  events` with `{"summary": title, "start": {"dateTime": iso}, "end":
  {"dateTime": iso}, "attendees": [{"email": invitee_email}]}` returns
  a real `200 {"id", "htmlLink", "status": "confirmed", "attendees":
  [...], ...}`.
- `DELETE .../events/{event_id}` returns a real `204 No Content` on
  success (used only for this session's own live verification cleanup,
  not by any code in this module -- Quorum never deletes a real
  external booking on a user's behalf today).

A REAL, DISCLOSED CALLER GAP FOR `CREATE_CALENDAR_EVENT_EXTERNAL`,
matching the exact "real execution capability, no real caller path
yet" pattern `SEND_EMAIL` already disclosed before `DEC-142`:
`retry_queue_drainer.py`'s own calendar domain translation always sets
`has_external_invitee=False` (a real, disclosed, deliberate choice --
a negotiation option's free text never names a real external
attendee's email address, and guessing one would be a real
fabrication), so no real code path in this backend can produce a
`CREATE_CALENDAR_EVENT_EXTERNAL` proposal today. This branch's own
real execution is genuinely correct and live-verified regardless --
Quorum's own architecture separates "can this be carried out safely"
from "does anything ask for it yet" throughout, and this is another
real instance of that same separation, not a mistake.

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
persist_gate_verdict`'s own real pattern). A real Gmail send can genuinely
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

# The same real, already-established value `retry_queue_drainer.py::
# _MAX_FINANCE_AMOUNT` uses -- defined again here, not imported,
# because `retry_queue_drainer.py` already imports `execute_approved_
# action` from this module, so importing the reverse direction would
# be a real circular import. Reused deliberately, not re-derived: this
# module's own real S2 `UPDATE_BUDGET` finding (CRITICAL-tier review,
# `DEC-148`) is that a real, Judge-authored `revised_payload` can reach
# this function having skipped `retry_queue_drainer.py`'s own pre-Gate
# `validate_and_build_finance_proposal()` bound entirely -- this is the
# real, structural backstop for that path, not a duplicate check for
# the same path.
_MAX_BUDGET_LIMIT = 99_999_999.99

# A real, live-confirmed shape for both a real Gmail message id and a
# real Gmail label id -- neither one this project has ever seen
# contain anything but this real, narrow character set. Rejected
# outright rather than interpolated unchecked into a real URL path.
_REAL_GMAIL_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

# No `calendar_ingestion.py` module exists in this codebase (unlike
# Gmail's own `email_ingestion.py::GMAIL_MESSAGES_URL`) -- Calendar has
# no real polling/ingestion counterpart yet (`DEC-151`'s own top-of-
# file docstring section explains why only the external-booking case
# needs a real Google Calendar API call at all), so this constant is
# defined here directly rather than imported from a sibling module.
_GOOGLE_CALENDAR_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


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


def _truncate_for_error(value: str, *, limit: int = 200) -> str:
    """A real, disclosed fix (CRITICAL-tier review, `DEC-151`, L1): an
    unbounded offending value echoed straight into a real `ValueError`
    message can amplify -- a real, malicious or malformed multi-
    megabyte `start`/`end` string would otherwise produce an equally
    huge `ExecutionResult.detail`. Today's one real caller (`retry_
    queue_drainer.py`) discards `.detail` on a non-executed result, so
    the real impact is memory-only, but any future caller persisting
    `detail` onto `action_events` would amplify straight into Postgres.
    Truncated here rather than left for a future caller to discover."""
    if len(value) <= limit:
        return value
    return f"{value[:limit]}... (truncated, {len(value)} chars total)"


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
    """Real, live writes for the seven real, safely-executable action
    types; a real, honest non-execution for every other real
    `ActionType`. Runs on the SAME connection/transaction the caller is
    already inside for `CREATE_TASK`/`LOG_EXPENSE`/`UPDATE_BUDGET`
    (matching `retry_queue_drainer.py`'s own atomicity discipline) --
    the four real Google-API-calling branches (three Gmail, one
    Calendar) never touch `conn` at all; see this module's own
    top-of-file docstring for why.

    `approved_by_user_id`/`google_access_token`/`http_client` are all
    optional, defaulting to `None` -- the one real caller today
    (`retry_queue_drainer.py`) never produces a real Gmail- or
    Calendar-executable action type (neither email nor an external
    calendar booking is a real negotiation domain today), so it never
    needs to pass them; a real, honest `executed=False` is returned for
    `SEND_EMAIL`/`ARCHIVE_EMAIL`/`LABEL_EMAIL`/`CREATE_CALENDAR_EVENT_
    EXTERNAL` when they're genuinely needed but missing, never a crash
    from an unexpected `None`.

    A REAL, VERIFIED SAFETY PROPERTY THIS FUNCTION RELIES ON FOR FOUR
    OF ITS SEVEN REAL BRANCHES, STATED EXPLICITLY RATHER THAN LEFT
    IMPLICIT, CORRECTED HERE (DEC-151 CRITICAL-tier review, M1 -- an
    earlier version of this exact paragraph miscounted this same
    grouping, and separately implied the S3 backstop answers the
    payload-trust question for `SEND_EMAIL`, which it does not: that
    backstop is about human APPROVAL, never about payload PROVENANCE):
    `CREATE_TASK`/`LOG_EXPENSE`/`ARCHIVE_EMAIL` are real `Stakes.S1`,
    and `LABEL_EMAIL` is real `Stakes.S0` (confirmed against `router.
    STAKES_TABLE`) -- `gate/orchestration.py`'s own real state machine
    means Stage B never runs for S0/S1, so `payload` here is always the
    original, already-validated `proposal.payload` for these four.

    A REAL, DIFFERENT, WEAKER GUARANTEE FOR THE REMAINING THREE --
    `UPDATE_BUDGET` (S2), `SEND_EMAIL` (S3), and `CREATE_CALENDAR_EVENT_
    EXTERNAL` (S3) all genuinely reach Stage B (S0/S1 skip it entirely;
    S2/S3 both run the real Judge, and only S3 also runs the real
    Critic -- `run_stage_b()`'s own real logic, confirmed directly),
    and `orchestration.py`'s own real `review()` can turn a Judge
    `decision="revise"` into a final `approve` carrying that Judge's
    own `revised_payload` -- a real `dict` with no schema guarantee
    beyond being one, for S2 exactly as much as for S3. `payload`
    reaching any of these three branches below is therefore NOT always
    the original, pre-Gate-validated value; each branch carries its own
    real, independent checks as its actual defense (a CRITICAL-tier
    review finding for `UPDATE_BUDGET`, `DEC-148`; a real header-
    injection fix for `SEND_EMAIL`, `DEC-142`; the same discipline
    applied up front for `CREATE_CALENDAR_EVENT_EXTERNAL`, `DEC-151`),
    not a restatement of a guarantee this docstring no longer makes for
    any of them. The real, structural, once-checked S3 backstop
    (`approved_by_user_id` above) is a SEPARATE, additional guarantee
    for `SEND_EMAIL`/`CREATE_CALENDAR_EVENT_EXTERNAL` specifically --
    it establishes that a real human approved the DECISION to act, not
    that the resulting PAYLOAD is trustworthy; both guarantees are
    needed, and neither substitutes for the other. Still handled
    defensively below regardless (a real `KeyError`/`TypeError`/
    `ValueError` returns a real, honest `executed=False` rather than an
    unhandled exception)."""
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


async def _real_google_calendar_post(
    http_client: httpx.AsyncClient,
    url: str,
    body: dict,
    *,
    access_token: str,
    action_type: ActionType,
    user_id: str,
) -> ExecutionResult:
    """The real, Google-Calendar-side mirror of `_real_gmail_post`
    above -- identical three-valued-outcome discipline (a transport
    failure is genuinely UNKNOWN, never folded into `False`), against
    the real, live-verified Google Calendar API v3 shape confirmed
    this session (`DEC-151`, see this module's own top-of-file
    docstring): `POST .../calendars/primary/events` returns a real
    `200 {"id", "htmlLink", "status", "attendees", ...}` on success."""
    try:
        response = await http_client.post(url, json=body, headers={"Authorization": f"Bearer {access_token}"})
    except httpx.HTTPError as exc:
        return ExecutionResult(
            executed=None,
            detail=(
                f"Real execution for {action_type.value!r} is genuinely UNKNOWN -- a transport-level failure "
                f"happened while calling Google's real Calendar API; a real booking may or may not have gone "
                f"through, never assume it did not: {exc}"
            ),
        )
    if response.status_code != 200:
        return ExecutionResult(
            executed=False,
            detail=f"Real execution for {action_type.value!r} was genuinely rejected by Google's real Calendar "
            f"API ({response.status_code}), not carried out: {response.text}",
        )
    try:
        response_body = response.json()
    except ValueError:
        response_body = {}
    real_event_id = response_body.get("id", "<unknown>")
    real_html_link = response_body.get("htmlLink", "<unknown>")
    logger.warning(
        "Real Google Calendar event created for user_id=%s event_id=%s htmlLink=%s",
        user_id, real_event_id, real_html_link,
    )
    return ExecutionResult(
        executed=True,
        detail=f"Real Google Calendar event created (event_id={real_event_id!r}, htmlLink={real_html_link!r}).",
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
        # concept that never existed before. `payload["amount"]` is
        # read as the real NEW ceiling itself, never a delta --
        # `negotiation/downstream_translation.py`'s own real translation
        # prompt now says this explicitly ("DEC-148 review finding H1"
        # in that file's own docstring); this branch enforces the
        # reading, that file's prompt asks the model for it.
        #
        # A REAL, CRITICAL-TIER-REVIEW-FOUND GAP, FIXED HERE (`DEC-148`
        # review, BLOCKER B1): `UPDATE_BUDGET` is real `Stakes.S2`, so
        # -- unlike `CREATE_TASK`/`LOG_EXPENSE` (`Stakes.S1`, Stage B
        # never runs) -- the real Judge DOES run for this action type,
        # and `orchestration.py`'s own real `review()` can turn a Judge
        # `decision="revise"` into a final `approve` carrying that
        # Judge's own `revised_payload`, a real `dict` with no schema
        # guarantee beyond that (the same real fact this module's own
        # `SEND_EMAIL` handling already discloses for S3). The payload
        # reaching this branch is therefore NOT always the original,
        # already-validated `retry_queue_drainer.py::validate_and_
        # build_finance_proposal()` output -- it can be a real,
        # LLM-authored value that never passed that function's own
        # bound check at all. The checks below are this function's own
        # real, independent, last-line-of-defense validation, not a
        # restatement of a check already guaranteed to have run.
        #
        # `math.isfinite()` is load-bearing, not decorative: a real
        # `float('nan')` genuinely satisfies `nan <= 0 == False` in
        # live, hand-verified Python (NaN compares False against every
        # relational operator except `!=`), and `float('inf')` also
        # satisfies `inf <= 0 == False` -- both would silently slip past
        # a bare `new_limit <= 0` check. A real, disclosed, hand-checked
        # fact about the ONE real path that reaches this branch through
        # the Gate today (a Judge-authored `revised_payload`): Postgres's
        # own `jsonb` type genuinely rejects the literal `NaN`/`Infinity`
        # tokens Python's `json.dumps` would otherwise emit (`Invalid
        # TextRepresentationError: Token "NaN" is invalid`, confirmed
        # live against the real Supabase database), so `_persist_
        # verdict()`'s own `INSERT INTO action_events` already fails
        # first for THAT specific path -- the job fails and genuinely
        # retries, never silently writing or executing the hostile
        # value. `math.isfinite()` here is still real, necessary defense
        # in depth, not redundant, for two genuinely different reasons:
        # (1) a real, live-caught-but-not-yet-JSON-serialized value
        # reaching this function through any future caller that doesn't
        # route through that same jsonb insert first, and (2) this
        # function's own `float(new_limit)` write below would otherwise
        # be the very LAST point a `NaN`/`inf` could still be caught if
        # that upstream protection were ever weakened. `_MAX_BUDGET_
        # LIMIT` is the check that actually matters for THIS real path
        # today: a finite-but-implausibly-large amount encodes as
        # perfectly valid JSON, sails past Postgres's jsonb parser
        # untouched, and would otherwise corrupt every real downstream
        # division by this value (`compute_budget_state`, `_build_
        # baseline`'s own `budget_remaining_fraction`) -- bounded here
        # the identical way `retry_queue_drainer.py::_MAX_FINANCE_
        # AMOUNT` already bounds a translated finance amount, reused
        # not re-derived.
        new_limit = payload["amount"]
        if (
            isinstance(new_limit, bool)
            or not isinstance(new_limit, (int, float))
            or not math.isfinite(new_limit)
            or new_limit <= 0
            or new_limit > _MAX_BUDGET_LIMIT
        ):
            raise ValueError(
                f"real UPDATE_BUDGET amount must be a real, finite number in (0, {_MAX_BUDGET_LIMIT}], got {new_limit!r}"
            )

        # A real, honest, live-found fact, matching LOG_EXPENSE's own
        # already-disclosed precedent immediately below: `payload
        # ["category"]` (real, translated content) is genuinely NOT
        # persisted here -- this is a single, whole-account monthly
        # ceiling, not a per-category one. The real, translated category
        # still survives in the real `action_events.payload` JSONB the
        # caller already persists alongside this write.
        #
        # A REAL, CRITICAL-TIER-REVIEW-FOUND GAP, FIXED HERE (`DEC-148`
        # review, HIGH H2): `UPDATE ... WHERE user_id = $2` genuinely,
        # silently matches ZERO rows for a real, nonexistent `user_id`
        # -- unlike `CREATE_TASK`/`LOG_EXPENSE`'s own real `INSERT`s,
        # which fail loud on a bad foreign key, a real `UPDATE`'s own
        # real status tag (`"UPDATE 0"`) was previously discarded,
        # so this branch would have reported a real, honest-looking
        # `executed=True` for a write that never genuinely happened.
        # Checked here, structurally, the same "verify what actually
        # happened, never assume" discipline this whole project's Gate
        # architecture exists to enforce elsewhere.
        status = await conn.execute(
            "UPDATE users SET monthly_budget_limit = $1 WHERE user_id = $2",
            float(new_limit),
            uuid.UUID(user_id),
        )
        if status != "UPDATE 1":
            raise ValueError(f"real UPDATE_BUDGET matched no real users row for user_id={user_id!r} ({status!r})")
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

    if action_type == ActionType.CREATE_CALENDAR_EVENT_EXTERNAL:
        if google_access_token is None:
            return ExecutionResult(executed=False, detail="Real CREATE_CALENDAR_EVENT_EXTERNAL execution skipped -- no real Google access token was provided to this call.")
        if http_client is None:
            return ExecutionResult(executed=False, detail="Real CREATE_CALENDAR_EVENT_EXTERNAL execution skipped -- no real HTTP client was provided to this call.")

        # Real payload fields checked for real, sane types BEFORE any
        # network call -- see this module's own UPDATE_BUDGET branch
        # docstring for why an S3 payload reaching this function is not
        # always `agents/calendar_agent.py::build_event_proposal()`'s
        # own already-validated shape (a Judge-authored revised_payload
        # is a real dict with no schema guarantee beyond that). Unlike
        # SEND_EMAIL's raw MIME headers or the Gmail message/label ids
        # interpolated into a real URL path, none of these four fields
        # are ever used anywhere but a JSON request body here, so there
        # is no real header- or path-injection vector to guard against.
        #
        # A REAL, DISCLOSED RESIDUAL RISK, NOT ELIMINATED HERE, FOUND BY
        # CRITICAL-TIER REVIEW (`DEC-151`, M4): Google's own real API is
        # the correct source of truth for whether `title`/`invitee_
        # email` are syntactically well-formed, but it has no way to
        # judge whether they are LEGITIMATE -- a Judge-authored, real
        # `revised_payload` could carry a syntactically valid but
        # attacker-chosen `invitee_email` and an attacker-influenced
        # `title`, and this branch would genuinely send a real Google
        # Calendar invitation to that address with that subject line,
        # from the real user's own Google account. What actually holds
        # the line against that is the real, structural S3 human-
        # approval backstop checked once above (`approved_by_user_id`),
        # never a format check -- disclosed explicitly here rather than
        # implying `invitee_email`'s free-form nature is itself safe.
        title = payload["title"]
        invitee_email = payload["invitee_email"]
        start_iso = payload["start"]
        end_iso = payload["end"]
        if not isinstance(title, str) or not title.strip():
            raise ValueError("real CREATE_CALENDAR_EVENT_EXTERNAL title must be a real, non-empty string")
        if not isinstance(invitee_email, str) or not invitee_email.strip():
            raise ValueError("real CREATE_CALENDAR_EVENT_EXTERNAL invitee_email must be a real, non-empty string")
        if not isinstance(start_iso, str) or not isinstance(end_iso, str):
            raise ValueError("real CREATE_CALENDAR_EVENT_EXTERNAL start/end must be real ISO datetime strings")
        try:
            real_start = datetime.fromisoformat(start_iso)
            real_end = datetime.fromisoformat(end_iso)
        except ValueError as exc:
            raise ValueError(
                f"real CREATE_CALENDAR_EVENT_EXTERNAL start/end are not real, parseable ISO datetimes "
                f"(start={_truncate_for_error(start_iso)!r}, end={_truncate_for_error(end_iso)!r}): {exc}"
            ) from exc
        # A real, disclosed gap fixed here, found by CRITICAL-tier
        # review (`DEC-151`, L3): a real, timezone-NAIVE ISO string
        # parses without error, but this branch's own `body` below
        # sends it as a bare `dateTime` with no `timeZone` sibling --
        # Google's own real interpretation of that is genuinely
        # ambiguous. `agents/calendar_agent.py::build_event_proposal()`'s
        # own real payload always originates from a tz-aware datetime's
        # own `.isoformat()` (every real caller uses `datetime.now(
        # timezone.utc)` or equivalent) -- reject anything that reaches
        # this branch without one, the same "don't trust a Judge-
        # revised shape" discipline this branch already applies above.
        if real_start.tzinfo is None or real_end.tzinfo is None:
            raise ValueError(
                "real CREATE_CALENDAR_EVENT_EXTERNAL start/end must be real, timezone-aware ISO datetimes"
            )
        # A real, disclosed gap fixed here, found by CRITICAL-tier
        # review (`DEC-151`, M2, matching that same review's own DEC-148
        # precedent): `retry_queue_drainer.py::validate_and_build_
        # calendar_proposal()`'s own pre-Gate check already enforces a
        # real `end > start` for this exact domain, but a Judge-revised
        # `revised_payload` can bypass that function entirely (see this
        # branch's own docstring paragraph above) -- this branch's own
        # last-line-of-defense duty means it cannot assume that upstream
        # check already ran, the same reasoning `UPDATE_BUDGET`'s own
        # bound check already established at `DEC-148`.
        if real_end <= real_start:
            raise ValueError(
                f"real CREATE_CALENDAR_EVENT_EXTERNAL end ({real_end}) must be after start ({real_start})"
            )

        body = {
            "summary": title,
            "start": {"dateTime": start_iso},
            "end": {"dateTime": end_iso},
            "attendees": [{"email": invitee_email}],
        }
        # A real, disclosed gap fixed here, found by CRITICAL-tier
        # review (`DEC-151`, H1): Google's real Calendar API genuinely
        # does NOT email a real event's real attendees unless
        # `sendUpdates` is explicitly set on the request -- omitting it
        # (this branch's original version) silently books the event
        # with the attendee merely recorded, never actually notified.
        # Since this branch's entire real reason to exist is inviting a
        # real external attendee -- not merely recording one on a
        # calendar nobody else ever sees -- `sendUpdates=all` is a real,
        # deliberate choice, not decoration.
        return await _real_google_calendar_post(
            http_client, f"{_GOOGLE_CALENDAR_EVENTS_URL}?sendUpdates=all", body,
            access_token=google_access_token, action_type=action_type, user_id=user_id,
        )

    return ExecutionResult(
        executed=False,
        detail=f"No real execution path exists yet for {action_type.value!r} -- decision recorded, not carried out.",
    )
