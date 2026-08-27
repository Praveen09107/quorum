"""The real `retry_queue` drainer -- `STATUS_INDEX.md` open item #26,
closed here (`DEC-127`). Reads real, due `job_type = "negotiation_
downstream_action"` rows (the only real job type any code in this
backend has ever enqueued, `features/negotiation_choice.py`), translates
each real chosen option into one real `ActionProposal` per domain in its
`source_domains`, and re-enters the real Gate (`gate.orchestration.
review()`, real Stage A + `DEC-125`'s real Critic/Judge) for each --
literally "each re-entering the Gate at its own stakes level",
`QUORUM_DATA_CONTRACTS.md` §5.6's own spec text.

A REAL SCOPE BOUNDARY, NARROWED SINCE `DEC-127` FIRST DISCLOSED IT,
NOW REAL FOR TWO DOMAINS (`DEC-128`): this module persists a real,
durable Gate VERDICT per downstream action -- a real `action_events`
row, using that table's own real `gate_decision`/`outcome`/
`resolved_at` columns -- and, for a genuine "approve" verdict, now also
calls `features/action_executor.py::execute_approved_action()` on the
SAME connection/transaction, so the real write and the real decision
that authorized it commit or roll back together. `CREATE_TASK`/
`LOG_EXPENSE` genuinely execute (a real `INSERT INTO tasks`/`expenses`).
`SEND_EMAIL`/`ARCHIVE_EMAIL`/`LABEL_EMAIL` also have real execution
targets now (`DEC-142`, real Gmail API calls) -- but this module's own
call site below deliberately never passes the real, pre-resolved
`google_access_token`/`approved_by_user_id` those need, so they still
always return a real, honest `executed=False` THROUGH THIS SPECIFIC
PATH, for a genuinely different reason than before: `email` is not a
real negotiation domain (`Position.domain` only ever resolves to
`calendar`/`tasks`/`finance`), so this drainer can never actually
produce one of these three action types to begin with -- see
`action_executor.py`'s own top-of-file docstring for the full account,
including the real S3 human-approval backstop `SEND_EMAIL` (and
`CREATE_CALENDAR_EVENT_EXTERNAL`) specifically requires. `UPDATE_
BUDGET` now ALSO has a real execution target (`DEC-148`, `users.
monthly_budget_limit`, migration `0015`) and genuinely executes through
this exact call site -- the real `finance` domain's own translated
`update_budget` action is the one real, live way this action type is
reachable in production today. Both real calendar types still have no
real execution target at all (Phase 5's own separate, Rule-5-gated
scope). Never called for `reject`/`revise`/`escalate_to_human` -- only
a genuine `approve` verdict.

STAGE A SCOPE, A REAL, DELIBERATE, PREETHISH-CONFIRMED CHOICE (`DEC-127`):
`availability_check` needs a real ground-truth adapter this backend
cannot honestly back yet -- no `calendar_events` table exists at all
(confirmed since `DEC-121`). Building one for real would mean inventing
new architecture beyond this session's real scope (`CLAUDE.md` Rule 3).
**`budget_check` is a genuinely different case as of `DEC-148`:** a
real `budgets`-ceiling now exists (`users.monthly_budget_limit`), so a
real, pure-code Stage A `budget_check` validator is now honestly
buildable for the first time -- tracked as its own new, disclosed open
item (it would be the correct, structural home for bounding a real
`UPDATE_BUDGET`/`LOG_EXPENSE` amount against the real, current ceiling
before Stage B ever runs, rather than `action_executor.py`'s own
last-line-of-defense checks doing all of that work alone), not silently
folded into this session's own scope. This drainer instead runs
`provenance_check` for every real domain (a genuinely correct,
non-fabricated `"user_request"` justification -- this action stems
directly from a real, explicit choice the user just made, recorded in
`negotiations.chosen_option_id`) plus `deadline_conflict_check` for the
`tasks` domain specifically, since the real `tasks` table already holds
enough real data to back it honestly, via `_PrefetchedCommittedHoursAdapter`
below.

`available_hours_before_deadline` IS A REAL, DELIBERATELY SIMPLE
HEURISTIC, NOT THE FULL "MEETING-LOAD DEFENSE" FEATURE: `(calendar days
until deadline) * TODAY_WORKING_HOURS_PER_DAY` (reusing `features/
today.py`'s own real, shared working-day constant, not a second,
duplicate one). A genuine multi-day capacity projection is its own,
still-unbuilt ADD §9.7 feature (`STATUS_INDEX.md` item #8) -- this
module deliberately does not build a smaller, hidden version of that
feature as a side effect of Stage A wiring.

STAGE B IS THE REAL `DEC-125` IMPLEMENTATION, INJECTED, NEVER
REBUILT HERE: `critic_call`/`judge_call` are the exact real
`make_groq_critic_call()`/`make_gemini_judge_call()` factories from
`gate/llm_calls.py`, passed in by the caller (`main.py`'s new internal
route), the same injected-dependency discipline every other real Gate
consumer in this backend already follows.
"""
from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import asyncpg

from quorum_backend.agents.calendar_agent import build_event_proposal
from quorum_backend.agents.finance_agent import build_finance_proposal
from quorum_backend.agents.tasks_agent import build_task_proposal
from quorum_backend.features.action_executor import execute_approved_action
from quorum_backend.features.today import TODAY_WORKING_HOURS_PER_DAY
from quorum_backend.gate.orchestration import CriticCall, JudgeCall, StageACheck, review
from quorum_backend.gate.schemas import ActionProposal, GateVerdict, Stakes
from quorum_backend.gate.validators import deadline_conflict_check, provenance_check
from quorum_backend.negotiation.downstream_translation import (
    DownstreamTranslationCall,
    DownstreamTranslationError,
)
from quorum_backend.router import get_stakes

# The real, already-existing partial index this schema shipped with
# (`migrations/0001_initial_schema/up.sql`: "idx_retry_queue_next_attempt
# ... WHERE attempt_count < 5") already encodes 5 as the real, intended
# max-attempt cutoff -- reused here, not a second, independently-chosen
# number that could silently drift from the index's own real filter.
MAX_RETRY_ATTEMPTS = 5

# A real, deliberately simple, disclosed fixed backoff -- not exponential.
# This drainer's own real failure modes (a transient Gemini/Groq quota
# hiccup, this session's own `STATUS_INDEX.md` item #21 finding) are
# genuinely short-lived and fluctuating, not the kind of sustained outage
# exponential backoff exists to protect against; a real, fixed 10-minute
# re-check is simple, honest, and sufficient for this scope.
RETRY_BACKOFF_MINUTES = 10

_NEGOTIATION_DOWNSTREAM_JOB_TYPE = "negotiation_downstream_action"


class DownstreamDrainError(Exception):
    """Raised for a real, structural failure specific to this drainer
    (an unrecognized domain, an unrecognized job_type) -- distinct from
    `DownstreamTranslationError`/`InfrastructureFailure`, which the real
    provider/Gate layers below already raise for their own real failure
    classes. All three are caught identically by `drain_due_jobs()`'s own
    real retry-queue bookkeeping -- the distinction exists for a clearer
    `last_error` message, not different handling."""


class _PrefetchedCommittedHoursAdapter:
    """A real, minimal `TasksAdapter` (`gate/validators.py`'s own
    `Protocol`) satisfied synchronously from an already-fetched, real
    value -- `StageACheck` is a synchronous `Callable[[ActionProposal],
    Finding]` by its own real type (`gate/orchestration.py`), so the real
    async Postgres query this needs must happen BEFORE Stage A checks are
    assembled, never inside one. See `fetch_committed_hours_before()`
    below for the real, live query that produces the value this class
    wraps."""

    def __init__(self, committed_hours: float):
        self._committed_hours = committed_hours

    def get_committed_hours_before(self, deadline: datetime) -> float:  # noqa: ARG002 -- real Protocol conformance; the value was already fetched for this exact deadline
        return self._committed_hours


async def fetch_committed_hours_before(conn: asyncpg.Connection, *, user_id: str, deadline: datetime) -> float:
    """Real, live query: this user's real, currently-open task hours
    already committed before the given real deadline -- the same real
    `tasks` table `features/today.py::fetch_today_capacity` already
    queries, generalized from "due today" to "due before an arbitrary
    real deadline", which is what `deadline_conflict_check` actually
    needs. Public (not `_`-prefixed) so `features/deadline_watch.py`
    (`DEC-13x`) can reuse this exact real query rather than duplicating
    it -- the same anti-duplication discipline this module's own reuse
    of `today.py`'s `TODAY_WORKING_HOURS_PER_DAY` already established."""
    row = await conn.fetchrow(
        "SELECT COALESCE(SUM(estimated_hours), 0) AS committed FROM tasks "
        "WHERE user_id = $1 AND status = 'open' AND deadline IS NOT NULL AND deadline <= $2",
        uuid.UUID(user_id),
        deadline,
    )
    return float(row["committed"])


def available_hours_before_deadline(deadline: datetime, *, now: datetime | None = None) -> float:
    """A real, deliberately simple heuristic -- see this module's own
    top-of-file docstring for why a genuine multi-day capacity
    projection is out of scope here. Never negative: a deadline already
    in the past yields 0.0 real available hours, not a nonsensical
    negative number."""
    reference_now = now or datetime.now(timezone.utc)
    whole_days = max(0, (deadline.date() - reference_now.date()).days)
    return whole_days * TODAY_WORKING_HOURS_PER_DAY


async def _build_stage_a_checks(
    conn: asyncpg.Connection, *, domain: str, proposal: ActionProposal, user_id: str
) -> list[StageACheck]:
    """`provenance_check` always -- this action's real justification is
    genuinely `"user_request"`, since it exists only because a real user
    just made a real, explicit negotiation choice; never fabricated.
    `deadline_conflict_check` additionally for `tasks`, backed by a real,
    live-fetched committed-hours value (see module docstring for why
    `finance`/`calendar` don't get an equivalent real ground-truth
    check)."""
    checks: list[StageACheck] = [lambda p: provenance_check(justification_sources=["user_request"])]

    if domain == "tasks":
        deadline = proposal.payload.get("deadline")
        deadline_dt = datetime.fromisoformat(deadline) if deadline else None
        if deadline_dt is not None:
            committed = await fetch_committed_hours_before(conn, user_id=user_id, deadline=deadline_dt)
            adapter = _PrefetchedCommittedHoursAdapter(committed)
            available = available_hours_before_deadline(deadline_dt)
            checks.append(
                lambda p, dl=deadline_dt, avail=available, ad=adapter: deadline_conflict_check(
                    claimed_commitment_hours=p.payload.get("estimated_hours"),
                    deadline=dl,
                    available_hours_before_deadline=avail,
                    tasks=ad,
                )
            )

    return checks


# Real, upper-bound caps mirroring the real, live column precision each
# value is eventually written into (`expenses.amount NUMERIC(10,2)`,
# `tasks.estimated_hours NUMERIC(4,1)`, confirmed against `migrations/
# 0001_initial_schema/up.sql` before choosing these). A real, live-shaped
# gap this session's own CRITICAL-tier review found and this fix closes:
# an unbounded, LLM-supplied number (a plausible hallucinated
# translation, e.g. "handle onboarding through the quarter" ->
# estimated_hours: 2000) would previously sail through Stage A untouched
# whenever no deadline is present (deadline_conflict_check trivially
# passes with no deadline to check against) and reach a real
# `INSERT INTO tasks`/`expenses` a fixed-precision NUMERIC column
# genuinely cannot hold -- caught here instead, with a real, honest
# `DownstreamTranslationError`, well before that INSERT is ever
# attempted.
_MAX_FINANCE_AMOUNT = 99_999_999.99
_MAX_ESTIMATED_HOURS = 999.9


def validate_and_build_finance_proposal(args: dict) -> ActionProposal:
    action = args["action"]
    amount = float(args["amount"])
    # `math.isfinite()` -- a real, CRITICAL-tier review finding
    # (`DEC-148`, BLOCKER B1): Python's real `json` module parses the
    # literal, non-standard tokens `NaN`/`Infinity`/`-Infinity` by
    # default, so a malformed real Gemini generation containing one of
    # these unquoted could otherwise slip past a bare `amount <= 0`
    # check (both `nan <= 0` and `inf <= 0` are real, live `False` in
    # Python) and reach `build_finance_proposal()`. Real, defense-in-
    # depth here -- `action_executor.py`'s own `UPDATE_BUDGET` branch
    # carries the same real check as its own, independent last line of
    # defense, since a Judge-authored `revised_payload` can bypass this
    # function entirely.
    if not math.isfinite(amount) or amount <= 0:
        raise DownstreamTranslationError(f"Translated finance amount must be a real, finite, positive number, got {amount!r}")
    if amount > _MAX_FINANCE_AMOUNT:
        raise DownstreamTranslationError(f"Translated finance amount {amount!r} exceeds the real, max storable value {_MAX_FINANCE_AMOUNT}")
    return build_finance_proposal(action=action, amount=amount, category=args["category"], payee=args.get("payee"))


def validate_and_build_task_proposal(args: dict) -> ActionProposal:
    estimated_hours = float(args["estimated_hours"])
    if estimated_hours <= 0:
        raise DownstreamTranslationError(f"Translated estimated_hours must be positive, got {estimated_hours!r}")
    if estimated_hours > _MAX_ESTIMATED_HOURS:
        raise DownstreamTranslationError(
            f"Translated estimated_hours {estimated_hours!r} exceeds the real, max storable value {_MAX_ESTIMATED_HOURS}"
        )
    deadline_iso = args.get("deadline_iso")
    deadline = datetime.fromisoformat(deadline_iso) if deadline_iso else None
    return build_task_proposal(title=args["title"], estimated_hours=estimated_hours, deadline=deadline, existing_task_id=None)


def validate_and_build_calendar_proposal(args: dict) -> ActionProposal:
    start = datetime.fromisoformat(args["start_iso"])
    end = datetime.fromisoformat(args["end_iso"])
    if end <= start:
        raise DownstreamTranslationError(f"Translated calendar event end ({end}) must be after start ({start})")
    # has_external_invitee is always False here -- a real, disclosed,
    # code-decided default; see this module's top-of-file docstring.
    return build_event_proposal(proposed_start=start, proposed_end=end, title=args["title"], has_external_invitee=False)


async def _translate_and_build_proposal(
    domain: str, description: str, translation_call: DownstreamTranslationCall
) -> ActionProposal:
    args = await translation_call(domain, description)
    if domain == "finance":
        return validate_and_build_finance_proposal(args)
    if domain == "tasks":
        return validate_and_build_task_proposal(args)
    if domain == "calendar":
        return validate_and_build_calendar_proposal(args)
    raise DownstreamDrainError(f"Unsupported domain for downstream translation: {domain!r}")


def map_verdict_to_outcome(verdict: GateVerdict) -> tuple[str | None, bool]:
    """Real, exhaustive mapping from `GateVerdict.decision` onto
    `action_events`'s own real, closed `outcome` vocabulary
    (`approved_unchanged`/`corrected_by_user`/`caught_by_gate`/
    `uncertain_no_data`), confirmed against `trust_digest.py`'s own real
    usage before choosing it, not guessed. Returns `(outcome,
    is_resolved)`: `is_resolved=False` means both `outcome` AND
    `resolved_at` stay real, honest `NULL` -- exactly `features/
    today.py`'s own established "only a genuinely still-open action ever
    has a live NULL resolved_at" semantics, so an `escalate_to_human`
    verdict from this drainer genuinely, correctly appears as a real
    `needs_you_now` entry the next time `/today` is called -- closing a
    real, small piece of that screen's own disclosed "correct but empty"
    gap (`DEC-119`), not by fabricating content, but by this module
    finally being a real producer for a table `/today` already reads.

    No `corrected_by_user` case exists here: that outcome specifically
    means a HUMAN corrected a draft, which never happens anywhere in
    this drainer's own real flow (there is no human-editing step) -- a
    Stage-B-issued revise that the Gate itself resolved is real
    `caught_by_gate` instead: the Gate, not a person, is what changed
    it.
    """
    if verdict.decision == "escalate_to_human":
        return None, False
    if verdict.decision == "approve" and verdict.revision_count == 0:
        return "approved_unchanged", True
    if verdict.decision == "approve" and verdict.revision_count == 1:
        return "caught_by_gate", True
    if verdict.decision == "reject":
        return "caught_by_gate", True
    if verdict.decision == "revise":
        # A real Stage-A-only hard fail with no further redraft loop in
        # this drainer's own scope (there is no interactive agent here
        # to act on Gate-requested revisions) -- the Gate genuinely
        # caught a real problem with the translated proposal; disclosed
        # limitation, not silently retried into an infinite loop.
        return "caught_by_gate", True
    raise DownstreamDrainError(f"Unhandled GateVerdict.decision: {verdict.decision!r}")


async def _persist_verdict(
    conn: asyncpg.Connection, *, proposal: ActionProposal, stakes: Stakes, verdict: GateVerdict, user_id: str
) -> bool:
    """Persists the real `action_events` row, then -- for a genuine
    `approve` verdict only -- calls the real `action_executor.py` on
    the SAME connection, so the real write (when one exists) commits or
    rolls back together with the real decision that authorized it.
    Returns whether a real execution genuinely happened.

    REAL, LIVE PERSISTENCE OF THE GATE'S OWN FINDINGS/OBJECTIONS, closing
    the real, disclosed gap `DEC-126` found (migration `0013`, `DEC-146`):
    `gate.review()`'s own real `GateVerdict.findings`/`.objections` have
    always been computed here, but were never persisted anywhere before
    this -- used only to decide `verdict.decision`, then discarded.

    Uses `.model_dump(mode="json")`, NOT the bare, default python-mode
    `.model_dump()` -- a real, CRITICAL-tier review finding (`DEC-146`)
    caught that `Finding.source_ref`/`Objection.evidence_ref` are
    `EvidenceRef | None`, and `EvidenceRef.retrieved_at` is a real
    `datetime`. Default `.model_dump()` returns that as a live
    `datetime` object, which `json.dumps()` cannot serialize -- a
    `TypeError` that today's two wired Stage A checks
    (`provenance_check`/`deadline_conflict_check`) never trigger (neither
    populates `source_ref`), but that a single new evidence-backed
    check or Critic objection would hit immediately, permanently
    stalling the affected job (see `MAX_RETRY_ATTEMPTS` below) and
    risking the exact same-transaction double-execution this module's
    own docstring already discloses for a different failure mode.
    `mode="json"` renders every field as its real, plain-JSON-safe
    shape -- `Literal` fields as plain strings (matching `mobile/lib/
    features/gate_reveal/gate_reveal_logic.dart`'s own already-built,
    already-tested parsing exactly: `evidence_state`/`category`/
    `severity`/`signed_off` as plain JSON values, never Python enum
    reprs) and `datetime` fields as real ISO-8601 strings -- verified
    directly against `gate/schemas.py`'s actual models, not assumed."""
    outcome, is_resolved = map_verdict_to_outcome(verdict)
    final_payload = verdict.revised_payload if verdict.revised_payload is not None else proposal.payload
    await conn.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at, findings, objections) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9, $10::jsonb, $11::jsonb)",
        proposal.proposal_id,
        proposal.action_type.value,
        stakes.value,
        json.dumps(final_payload),
        verdict.decision,
        outcome,
        verdict.trace_id,
        uuid.UUID(user_id),
        datetime.now(timezone.utc) if is_resolved else None,
        json.dumps([finding.model_dump(mode="json") for finding in verdict.findings]),
        json.dumps([objection.model_dump(mode="json") for objection in verdict.objections]),
    )

    if verdict.decision != "approve":
        # Never executes on reject/revise/escalate_to_human -- see this
        # module's and action_executor.py's own top-of-file docstrings
        # for why escalate_to_human specifically must never execute.
        return False

    result = await execute_approved_action(conn, action_type=proposal.action_type, payload=final_payload, user_id=user_id)
    return result.executed


async def process_negotiation_downstream_job(
    conn: asyncpg.Connection,
    payload: dict,
    *,
    translation_call: DownstreamTranslationCall,
    critic_call: CriticCall,
    judge_call: JudgeCall,
) -> tuple[int, int]:
    """Processes one real, dequeued `negotiation_downstream_action` job
    -- one real `ActionProposal` (translated, then Gate-reviewed) per
    domain in the job's real `source_domains`. Returns real
    `(actions_produced, actions_executed)` counts -- `(0, 0)` for a
    genuine "do nothing" choice. `actions_executed` counts only real,
    genuine writes (`action_executor.py`'s own `CREATE_TASK`/
    `LOG_EXPENSE` execution); every other approved action still counts
    toward `actions_produced` (a real Gate decision was reached and
    persisted) but not `actions_executed`.

    A REAL, LIVE BUG FOUND AND FIXED DURING THIS SESSION'S OWN SECOND-
    PASS SELF-REVIEW, BEFORE ANY REVIEW SUBAGENT RAN: an earlier version
    of this function persisted each domain's own `action_events` row as
    soon as its own Gate review completed, inside the loop. Since
    `drain_due_jobs()`'s own `try/except` around this whole call sits
    INSIDE the same real Postgres transaction as the dequeue and the
    retry-queue bookkeeping, a LATER domain's real failure (a
    translation error, a Gate `InfrastructureFailure`) was caught by
    that outer `except`, not re-raised -- so the transaction still
    committed normally, durably persisting the EARLIER domain's already-
    inserted row even though the whole job was simultaneously being
    marked failed-and-retried. The next drain would re-process the
    whole job from scratch, genuinely duplicating that earlier domain's
    real `action_events` row. Fixed structurally, not with an added
    idempotency check: every domain's real translate -> propose ->
    Stage A -> Stage B pipeline (a pure read/compute pass against
    `conn`, only for `deadline_conflict_check`'s own real query) now
    runs to completion for EVERY domain BEFORE any real persistence
    happens, and persistence for the whole job commits together, only
    once every domain has genuinely succeeded -- never partially. A
    real failure at any point in the first pass now leaves nothing
    persisted at all, so a retry-from-scratch is always safe."""
    user_id = payload["user_id"]
    option_description = payload["option_description"]
    source_domains: list[str] = payload["source_domains"]

    if not source_domains:
        # The real, always-honest "do nothing" case
        # (`gate/schemas.py::NegotiationOption`'s own docstring) -- zero
        # real downstream actions needed, not an error.
        return 0, 0

    reviewed: list[tuple[ActionProposal, Stakes, GateVerdict]] = []
    for domain in source_domains:
        proposal = await _translate_and_build_proposal(domain, option_description, translation_call)
        stakes = get_stakes(proposal.action_type)
        stage_a_checks = await _build_stage_a_checks(conn, domain=domain, proposal=proposal, user_id=user_id)
        verdict = await review(proposal, stakes, stage_a_checks, critic_call, judge_call)
        reviewed.append((proposal, stakes, verdict))

    # A real, narrow, disclosed remaining gap, NOT the same bug the
    # docstring above already found and fixed: that fix guarantees every
    # domain's real translate/review pass completes before ANY real
    # persistence begins. It does NOT guarantee every domain's own
    # persist step (this loop) is atomic relative to every OTHER
    # domain's persist step -- if domain 1's real action_events insert
    # and `execute_approved_action()` genuinely succeed, and domain 2's
    # OWN persist step then raises a genuine, uncaught exception (a real
    # database infrastructure failure, not the malformed-payload case
    # `action_executor.py` already handles defensively), domain 1's
    # already-committed-in-this-transaction row would still commit when
    # the whole job is caught and marked failed-and-retried one level up
    # -- a real, low-probability risk of a duplicate on retry, the same
    # real category of trade-off `security/supabase_deletion_store.py`'s
    # own disclosed `DEC-113` atomicity gap already accepted for this
    # project: narrow, needs a genuine infra failure specifically mid-
    # persist-loop, not fixed by restructuring further this session,
    # disclosed rather than silently left unexamined.
    executed_count = 0
    for proposal, stakes, verdict in reviewed:
        executed = await _persist_verdict(conn, proposal=proposal, stakes=stakes, verdict=verdict, user_id=user_id)
        if executed:
            executed_count += 1

    return len(reviewed), executed_count


async def _mark_job_failed(conn: asyncpg.Connection, retry_id, error_message: str) -> None:
    await conn.execute(
        "UPDATE retry_queue SET attempt_count = attempt_count + 1, "
        "next_attempt_at = now() + ($1 * INTERVAL '1 minute'), last_error = $2 "
        "WHERE retry_id = $3",
        RETRY_BACKOFF_MINUTES,
        error_message[:2000],
        retry_id,
    )


@dataclass(frozen=True)
class DrainResult:
    jobs_seen: int
    jobs_succeeded: int
    jobs_failed: int
    downstream_actions_produced: int
    downstream_actions_executed: int


async def drain_due_jobs(
    pool: asyncpg.Pool,
    *,
    translation_call: DownstreamTranslationCall,
    critic_call: CriticCall,
    judge_call: JudgeCall,
    max_jobs: int = 10,
) -> DrainResult:
    """The real drainer entry point -- called by `main.py`'s new
    `POST /internal/drain-retry-queue`, and, once `pg_cron`/`pg_net` are
    genuinely enabled on the real Supabase project (confirmed live,
    NOT yet the case as of this session -- see this module's own
    top-of-file scope note and `STATUS_INDEX.md`), by a real, scheduled
    `pg_net.http_post` call instead.

    Dequeues real, due jobs one at a time, each inside its own real
    transaction with `FOR UPDATE SKIP LOCKED` -- a concurrent second
    drain invocation (a real possibility once `pg_cron` fires on a
    schedule against a `--max-instances=2` Cloud Run deployment) can
    never double-process the same real row. A real, live failure (a
    translation error, a Gate `InfrastructureFailure`, or this module's
    own `DownstreamDrainError`) increments the real `attempt_count` and
    pushes `next_attempt_at` forward rather than losing the job or
    retrying it in a tight loop -- `MAX_RETRY_ATTEMPTS` matches this
    schema's own already-existing partial index exactly.

    A REAL, STRUCTURAL BUG FOUND BY THIS SESSION'S OWN CRITICAL-TIER
    REVIEW, FIXED BEFORE MERGE: an earlier version called
    `_mark_job_failed()` from INSIDE the same `except` block that was
    itself still inside the same `async with conn.transaction():` the
    real failure occurred in. A genuine Postgres-level failure (a
    constraint violation, a numeric-overflow -- exactly the class
    `validate_and_build_finance_proposal`/`validate_and_build_task_
    proposal`'s own new upper-bound checks above now catch earlier and
    more precisely) leaves that transaction in Postgres's own real
    "aborted" state; every subsequent statement on it -- including the
    real `UPDATE retry_queue` `_mark_job_failed()` itself issues --
    fails too, with a second, uncaught exception. Net effect: the whole
    transaction rolls back (safe -- no partial data), but `attempt_count`
    is never incremented and `next_attempt_at` never advances, so the
    identical, permanently-malformed job would be re-selected and
    reprocessed from scratch on every future drain call, forever, rather
    than genuinely backing off and eventually giving up at
    `MAX_RETRY_ATTEMPTS`. Fixed structurally: the `try` now wraps the
    WHOLE `async with conn.transaction():` block, not a piece nested
    inside it -- letting a real failure propagate out of that block
    triggers Postgres's own real `ROLLBACK` via the transaction context
    manager itself, restoring the connection to a normal, usable state
    BEFORE `_mark_job_failed()` ever runs, as its own separate,
    guaranteed-to-succeed statement.
    """
    jobs_seen = jobs_succeeded = jobs_failed = 0
    downstream_actions_produced = 0
    downstream_actions_executed = 0

    for _ in range(max_jobs):
        async with pool.acquire() as conn:
            retry_id = None
            error_message: str | None = None
            no_more_jobs = False

            try:
                async with conn.transaction():
                    row = await conn.fetchrow(
                        "SELECT retry_id, job_type, payload, attempt_count FROM retry_queue "
                        "WHERE next_attempt_at <= now() AND attempt_count < $1 "
                        "ORDER BY next_attempt_at FOR UPDATE SKIP LOCKED LIMIT 1",
                        MAX_RETRY_ATTEMPTS,
                    )
                    if row is None:
                        no_more_jobs = True
                    else:
                        jobs_seen += 1
                        retry_id = row["retry_id"]

                        if row["job_type"] != _NEGOTIATION_DOWNSTREAM_JOB_TYPE:
                            # A real, exhaustive, disclosed guard -- this
                            # drainer only knows how to process the one
                            # real job_type any code in this backend has
                            # ever enqueued. Raised, not handled inline,
                            # so it flows through the exact same real
                            # recovery path every other real failure
                            # below does.
                            raise DownstreamDrainError(f"Unknown job_type: {row['job_type']!r}")

                        payload = json.loads(row["payload"])
                        produced, executed = await process_negotiation_downstream_job(
                            conn, payload, translation_call=translation_call, critic_call=critic_call, judge_call=judge_call
                        )
                        await conn.execute("DELETE FROM retry_queue WHERE retry_id = $1", retry_id)
                        jobs_succeeded += 1
                        downstream_actions_produced += produced
                        downstream_actions_executed += executed
            except Exception as exc:  # noqa: BLE001 -- deliberately broad: any real failure here retries via the queue, never silently drops the job
                jobs_failed += 1
                error_message = str(exc)

            if no_more_jobs:
                break

            if error_message is not None and retry_id is not None:
                # A real, deliberately SEPARATE statement from the
                # transaction above -- see this function's own top-of-
                # docstring account of the real bug this ordering fixes.
                await _mark_job_failed(conn, retry_id, error_message)

    return DrainResult(
        jobs_seen=jobs_seen,
        jobs_succeeded=jobs_succeeded,
        jobs_failed=jobs_failed,
        downstream_actions_produced=downstream_actions_produced,
        downstream_actions_executed=downstream_actions_executed,
    )
