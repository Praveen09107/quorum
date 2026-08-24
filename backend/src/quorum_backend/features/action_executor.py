"""The real execution layer -- `STATUS_INDEX.md` open item #28, closed
here for the two real domains that are genuinely safe to close it for
(`DEC-128`). Confirmed by direct search before `DEC-127` even started
designing the `retry_queue` drainer: no code anywhere in this backend
had ever carried out a Gate-approved `ActionProposal`'s real effect --
every layer built so far (all 5 agents, the Gate, negotiation, the
drainer) stopped at producing a real, verified decision.

ONLY TWO REAL ACTION TYPES ARE GENUINELY, SAFELY EXECUTABLE TODAY --
`CREATE_TASK` and `LOG_EXPENSE` -- confirmed by checking every other
real `ActionType`'s real execution target before writing a line of
code, not assumed:
  - `UPDATE_BUDGET` has no real execution target: no `budgets`-ceiling
    table exists anywhere in this schema (only `expenses`, which
    records transactions, not a ceiling to update) -- the exact same
    real gap `retry_queue_drainer.py`'s own Stage A scope note already
    disclosed for `budget_check`.
  - `CREATE_CALENDAR_EVENT_LOCAL`/`_EXTERNAL` have no real execution
    target either: no `calendar_events` table exists anywhere in this
    schema, and `_EXTERNAL` would additionally need a real Google
    Calendar API call -- a genuine external, irreversible action
    needing a dedicated sandbox test account per `CLAUDE.md` Rule 5,
    a real, separate decision, not something to build as a side effect
    of this pass.
  - `SEND_EMAIL`/`ARCHIVE_EMAIL`/`LABEL_EMAIL` need a real Gmail API
    call -- the same real, external, Rule-5-gated decision as Calendar.
  - `UPDATE_TASK`/`UPDATE_APPLICATION_STATUS` are never produced by any
    real code path that reaches this function yet (the drainer's own
    translation always produces `CREATE_TASK`, never `UPDATE_TASK`, per
    `negotiation/downstream_translation.py`'s own disclosed reasoning;
    `career` is never a real negotiation domain at all).

Every one of those returns a real, honest `executed=False` with a real
explanation -- never silently skipped, never fabricated as done.

A REAL, DISCLOSED SCHEMA GAP FOUND AND CLOSED HERE, NOT SILENTLY
ROUTED AROUND: `expenses.source`'s real, live `CHECK` constraint
(migration `0001`) is a closed 3-value vocabulary --
`on_device`/`manual`/`extracted` -- none of which honestly describes a
real expense row this function is about to start creating: not typed
in by a person, not captured on-device, not extracted from a document.
Migration `0007` (new) adds a real, precisely-named fourth value,
`gate_approved`, applied live to the real Supabase database before
this module was written -- the same real, disclosed enum-extension
precedent `DEC-120`'s own `SearchItemType.application` addition
already established for this project, not a silent reuse of the
closest existing value.

CALLED ONLY FOR A GENUINE, TERMINAL "approve" VERDICT -- never for
`reject`/`revise`/`escalate_to_human`. An `escalate_to_human` decision
in particular must NEVER execute: it is this system's own real
human-in-the-loop gate, and no real "a human clicked approve on this
escalated action" endpoint exists yet either (a further, separate,
disclosed open item) -- executing on escalation would silently defeat
the entire reason Stage B can escalate in the first place.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

import asyncpg

from quorum_backend.gate.schemas import ActionType

_UNKNOWN_PAYEE = "Unknown"


@dataclass(frozen=True)
class ExecutionResult:
    executed: bool
    detail: str


async def execute_approved_action(
    conn: asyncpg.Connection, *, action_type: ActionType, payload: dict, user_id: str
) -> ExecutionResult:
    """Real, live writes for the two real, safely-executable action
    types; a real, honest non-execution for every other real
    `ActionType`. Runs on the SAME connection/transaction the caller is
    already inside (matching `retry_queue_drainer.py`'s own atomicity
    discipline: this write commits or rolls back together with the
    real `action_events` row recording the decision that authorized
    it, never independently).

    A REAL, VERIFIED SAFETY PROPERTY THIS FUNCTION RELIES ON, STATED
    EXPLICITLY RATHER THAN LEFT IMPLICIT: `CREATE_TASK`/`LOG_EXPENSE`
    are both real `Stakes.S1` (confirmed against `router.STAKES_TABLE`
    before writing this) -- `gate/orchestration.py`'s own real state
    machine means Stage B never runs for S0/S1, so `payload` here is
    always the original, already-validated `proposal.payload`
    (`retry_queue_drainer.py`'s own `validate_and_build_*_proposal()`
    guarantees its required keys exist), never a Judge-revised payload
    with no schema guarantee. Still handled defensively below (a real
    `KeyError`/`TypeError` returns a real, honest `executed=False`
    rather than an unhandled exception) so a future stakes-table change
    fails safely instead of silently risking the exact retry-
    duplication class of bug this session's own self-review already
    found and fixed once in the review phase."""
    try:
        return await _execute_approved_action_unsafe(conn, action_type=action_type, payload=payload, user_id=user_id)
    except (KeyError, TypeError, ValueError) as exc:
        return ExecutionResult(
            executed=False,
            detail=f"Real execution for {action_type.value!r} failed on a malformed payload, not carried out: {exc}",
        )


async def _execute_approved_action_unsafe(
    conn: asyncpg.Connection, *, action_type: ActionType, payload: dict, user_id: str
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

    return ExecutionResult(
        executed=False,
        detail=f"No real execution path exists yet for {action_type.value!r} -- decision recorded, not carried out.",
    )
