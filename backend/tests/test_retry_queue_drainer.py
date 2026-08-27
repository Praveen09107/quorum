"""Real tests for features/retry_queue_drainer.py (DEC-127) -- pure-logic
unit tests plus real, live-database integration tests proving the real
`retry_queue` dequeue/success/failure mechanics against a real Postgres
transaction, per CLAUDE.md Rule 5. Real `Objection`/`GateVerdict`-typed
fake `critic_call`/`judge_call` are injected for deterministic outcomes
(the same real discipline `self_test_harness.py`'s own adversarial
scenarios already established) -- proving THIS module's own real
translate -> propose -> Stage A -> Stage B -> persist pipeline, not
re-proving Gemini/Groq's own output quality (covered separately by
`test_gate_llm_calls.py`/`test_downstream_translation.py`).
"""
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.features.retry_queue_drainer import (
    _mark_job_failed,
    _persist_verdict,
    available_hours_before_deadline,
    drain_due_jobs,
    map_verdict_to_outcome,
    validate_and_build_calendar_proposal,
    validate_and_build_finance_proposal,
    validate_and_build_task_proposal,
)
from quorum_backend.gate.schemas import (
    ActionProposal,
    ActionType,
    EvidenceRef,
    Finding,
    GateVerdict,
    Objection,
    Stakes,
)
from quorum_backend.negotiation.downstream_translation import DownstreamTranslationError


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-drainer-{uuid.uuid4()}"
    uid = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield uid
    await pool.execute("DELETE FROM action_events WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM retry_queue")  # no per-row user_id column to scope by -- see DEC-124's own disclosed limitation
    await pool.execute("DELETE FROM tasks WHERE user_id = $1", uuid.UUID(uid))
    # DEC-128: real execution now genuinely writes real expenses rows
    # for a real, approved log_expense verdict -- cleaned up here too.
    await pool.execute("DELETE FROM expenses WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(uid))


def _verdict(decision: str, *, revision_count: int = 0) -> GateVerdict:
    return GateVerdict(decision=decision, findings=[], objections=[], trace_id="test-trace", revision_count=revision_count)


async def _fake_translation_call_factory(responses: dict):
    async def call(domain: str, description: str) -> dict:
        return responses[domain]

    return call


async def _fake_critic_call(proposal, findings):
    return [Objection(category="completeness", severity="low", description="Reviewed, no issues.", signed_off=True)]


async def _fake_judge_approve(proposal, findings, objections):
    return _verdict("approve")


# --- Pure-logic unit tests ---


def test_available_hours_before_deadline_is_zero_for_a_past_deadline():
    now = datetime(2026, 8, 20, tzinfo=timezone.utc)
    past = datetime(2026, 8, 10, tzinfo=timezone.utc)
    assert available_hours_before_deadline(past, now=now) == 0.0


def test_available_hours_before_deadline_scales_with_real_calendar_days():
    now = datetime(2026, 8, 20, tzinfo=timezone.utc)
    deadline = datetime(2026, 8, 23, tzinfo=timezone.utc)
    assert available_hours_before_deadline(deadline, now=now) == 3 * 8.0


def test_map_verdict_to_outcome_is_exhaustive_over_every_real_decision():
    assert map_verdict_to_outcome(_verdict("approve", revision_count=0)) == ("approved_unchanged", True)
    assert map_verdict_to_outcome(_verdict("approve", revision_count=1)) == ("caught_by_gate", True)
    assert map_verdict_to_outcome(_verdict("reject")) == ("caught_by_gate", True)
    assert map_verdict_to_outcome(_verdict("revise")) == ("caught_by_gate", True)
    assert map_verdict_to_outcome(_verdict("escalate_to_human")) == (None, False)


def test_validate_and_build_finance_proposal_rejects_a_non_positive_amount():
    with pytest.raises(DownstreamTranslationError):
        validate_and_build_finance_proposal({"action": "log_expense", "amount": 0, "category": "food", "payee": None})
    with pytest.raises(DownstreamTranslationError):
        validate_and_build_finance_proposal({"action": "log_expense", "amount": -5, "category": "food", "payee": None})


def test_validate_and_build_finance_proposal_accepts_a_real_positive_amount():
    proposal = validate_and_build_finance_proposal({"action": "log_expense", "amount": 42.5, "category": "food", "payee": "Real Vendor"})
    assert proposal.payload["amount"] == 42.5


def test_validate_and_build_finance_proposal_rejects_an_amount_exceeding_the_real_numeric_10_2_column():
    """A real regression proof for a real bug found by this session's
    own CRITICAL-tier review: an unbounded, hallucinated amount must
    never reach the real `expenses.amount NUMERIC(10,2)` column."""
    with pytest.raises(DownstreamTranslationError):
        validate_and_build_finance_proposal({"action": "log_expense", "amount": 100_000_000.0, "category": "food", "payee": None})


def test_validate_and_build_task_proposal_rejects_non_positive_hours():
    with pytest.raises(DownstreamTranslationError):
        validate_and_build_task_proposal({"title": "x", "estimated_hours": 0, "deadline_iso": None})


def test_validate_and_build_task_proposal_rejects_estimated_hours_exceeding_the_real_numeric_4_1_column():
    """A real regression proof for the same class of bug: an unbounded,
    hallucinated `estimated_hours` (e.g. "handle onboarding through the
    quarter" -> 2000) must never reach the real `tasks.estimated_hours
    NUMERIC(4,1)` column."""
    with pytest.raises(DownstreamTranslationError):
        validate_and_build_task_proposal({"title": "x", "estimated_hours": 2000.0, "deadline_iso": None})


def test_validate_and_build_task_proposal_handles_a_real_null_deadline_honestly():
    proposal = validate_and_build_task_proposal({"title": "Follow up", "estimated_hours": 1.5, "deadline_iso": None})
    assert proposal.payload["deadline"] is None


def test_validate_and_build_calendar_proposal_rejects_end_before_or_equal_to_start():
    with pytest.raises(DownstreamTranslationError):
        validate_and_build_calendar_proposal(
            {"title": "x", "start_iso": "2026-09-01T10:00:00+00:00", "end_iso": "2026-09-01T09:00:00+00:00"}
        )


def test_validate_and_build_calendar_proposal_is_always_the_local_lower_stakes_variant():
    from quorum_backend.gate.schemas import ActionType

    proposal = validate_and_build_calendar_proposal(
        {"title": "Sync", "start_iso": "2026-09-01T09:00:00+00:00", "end_iso": "2026-09-01T09:30:00+00:00"}
    )
    assert proposal.action_type == ActionType.CREATE_CALENDAR_EVENT_LOCAL


# --- Real, live-database integration tests ---


async def _seed_job(pool, *, user_id: str, source_domains: list[str], description: str = "Real, chosen negotiation option") -> uuid.UUID:
    row = await pool.fetchrow(
        "INSERT INTO retry_queue (job_type, payload) VALUES ($1, $2::jsonb) RETURNING retry_id",
        "negotiation_downstream_action",
        json.dumps(
            {
                "negotiation_id": str(uuid.uuid4()),
                "user_id": user_id,
                "chosen_option_id": "option_a",
                "option_description": description,
                "source_domains": source_domains,
            }
        ),
    )
    return row["retry_id"]


async def test_drain_due_jobs_do_nothing_option_produces_zero_actions_and_deletes_the_job(pool, user_id):
    retry_id = await _seed_job(pool, user_id=user_id, source_domains=[])

    translation_call = await _fake_translation_call_factory({})
    result = await drain_due_jobs(pool, translation_call=translation_call, critic_call=_fake_critic_call, judge_call=_fake_judge_approve)

    assert result.jobs_seen == 1
    assert result.jobs_succeeded == 1
    assert result.downstream_actions_produced == 0
    assert await pool.fetchrow("SELECT 1 FROM retry_queue WHERE retry_id = $1", retry_id) is None


async def test_drain_due_jobs_an_unsupported_domain_fails_loud_via_the_real_retry_path(pool, user_id):
    """A real, structural guard: `source_domains` should only ever
    contain `finance`/`tasks`/`calendar` (`Position.domain`'s own real
    schema constraint), but a real, unrecognized value must still fail
    loud via `DownstreamDrainError`, retried via the queue, never
    silently skipped or guessed at."""
    retry_id = await _seed_job(pool, user_id=user_id, source_domains=["career"])
    translation_call = await _fake_translation_call_factory({})

    result = await drain_due_jobs(pool, translation_call=translation_call, critic_call=_fake_critic_call, judge_call=_fake_judge_approve)

    assert result.jobs_failed == 1
    row = await pool.fetchrow("SELECT attempt_count, last_error FROM retry_queue WHERE retry_id = $1", retry_id)
    assert row is not None
    assert row["attempt_count"] == 1
    assert "career" in row["last_error"]


async def test_drain_due_jobs_processes_a_real_single_domain_job_and_persists_a_real_action_event(pool, user_id):
    retry_id = await _seed_job(pool, user_id=user_id, source_domains=["finance"])
    translation_call = await _fake_translation_call_factory(
        {"finance": {"action": "log_expense", "amount": 25.0, "category": "food", "payee": None}}
    )

    result = await drain_due_jobs(pool, translation_call=translation_call, critic_call=_fake_critic_call, judge_call=_fake_judge_approve)

    assert result.jobs_succeeded == 1
    assert result.downstream_actions_produced == 1
    assert result.downstream_actions_executed == 1
    assert await pool.fetchrow("SELECT 1 FROM retry_queue WHERE retry_id = $1", retry_id) is None

    event = await pool.fetchrow(
        "SELECT action_type, stakes, gate_decision, outcome, resolved_at FROM action_events WHERE user_id = $1", uuid.UUID(user_id)
    )
    assert event["action_type"] == "log_expense"
    assert event["gate_decision"] == "approve"
    assert event["outcome"] == "approved_unchanged"
    assert event["resolved_at"] is not None

    # DEC-128: a real execution genuinely happened -- a real expenses
    # row, not just a recorded verdict. `category` is NOT asserted here
    # -- the real `expenses` table has no such column (confirmed
    # against `migrations/0001_initial_schema/up.sql`); the translated
    # category still survives in `action_events.payload` above, just
    # not in a dedicated `expenses` column, see `action_executor.py`'s
    # own disclosure.
    expense = await pool.fetchrow(
        "SELECT amount, source FROM expenses WHERE user_id = $1", uuid.UUID(user_id)
    )
    assert expense is not None
    assert float(expense["amount"]) == 25.0
    assert expense["source"] == "gate_approved"

    # DEC-146: real, live persistence of the Gate's own findings/
    # objections, closing the gap DEC-126 found -- LOG_EXPENSE is real
    # Stakes.S1, so Stage B (and therefore `_fake_critic_call`) never
    # runs; `objections` must be a real, honest empty list, never a
    # fabricated one, while `findings` reflects whatever real Stage A
    # checks apply to this domain.
    gate_reveal_row = await pool.fetchrow(
        "SELECT findings, objections FROM action_events WHERE user_id = $1", uuid.UUID(user_id)
    )
    assert json.loads(gate_reveal_row["objections"]) == []
    assert isinstance(json.loads(gate_reveal_row["findings"]), list)


async def test_persist_verdict_writes_real_findings_and_objections_matching_the_real_verdict(pool, user_id):
    """A real, direct unit test of `_persist_verdict()` itself (not the
    full `drain_due_jobs()` pipeline) -- proves the real persistence
    mechanism handles a genuinely non-empty `objections` list correctly,
    a real state no domain this drainer can currently translate ever
    reaches on its own (none of `finance`/`tasks`/`calendar-local` ever
    exceeds S2 -- real Stage-B Critic objections only exist for real S3
    actions, none of which `Position.domain`'s own schema lets this
    drainer produce; `finance` can also reach S2 via `UPDATE_BUDGET`,
    not just S1's `LOG_EXPENSE`). Disclosed here rather than silently
    left untested.

    Also covers the real, CRITICAL-tier review finding this test
    previously missed (`DEC-146`): a `Finding`/`Objection` carrying a
    real `EvidenceRef` (a real `datetime` in `retrieved_at`) must
    round-trip through `_persist_verdict()`'s `json.dumps(...,
    mode="json")` without a `TypeError` -- the bare, default
    `.model_dump()` this test originally exercised never surfaced that
    bug because neither field it used ever set `source_ref`/
    `evidence_ref`."""
    proposal = ActionProposal(
        action_type=ActionType.LOG_EXPENSE, payload={"amount": 10.0, "category": "food", "payee": "A real vendor"}
    )
    evidence_ref = EvidenceRef(source_type="budget", source_id="real-budget-row-id")
    verdict = GateVerdict(
        decision="approve",
        findings=[
            Finding(
                validator="ProvenanceCheck",
                claim="A real claim",
                evidence_state="verified_true",
                source_ref=evidence_ref,
                confidence=1.0,
            )
        ],
        objections=[
            Objection(
                category="tone",
                severity="low",
                description="A real, live-tested objection.",
                evidence_ref=evidence_ref,
                signed_off=True,
            )
        ],
        trace_id="test-trace",
        revision_count=0,
    )

    async with pool.acquire() as conn, conn.transaction():
        await _persist_verdict(conn, proposal=proposal, stakes=Stakes.S1, verdict=verdict, user_id=user_id)

    row = await pool.fetchrow(
        "SELECT findings, objections FROM action_events WHERE proposal_id = $1", proposal.proposal_id
    )
    findings = json.loads(row["findings"])
    objections = json.loads(row["objections"])
    assert findings[0]["validator"] == "ProvenanceCheck"
    assert findings[0]["source_ref"]["source_id"] == "real-budget-row-id"
    # mode="json" must render the real datetime as a real ISO-8601
    # string, never a raw Python datetime repr that json.dumps would
    # have rejected outright.
    assert isinstance(findings[0]["source_ref"]["retrieved_at"], str)
    assert len(objections) == 1
    assert objections[0]["category"] == "tone"
    assert objections[0]["signed_off"] is True
    assert objections[0]["evidence_ref"]["source_type"] == "budget"


async def test_drain_due_jobs_processes_a_real_multi_domain_job_and_persists_one_action_event_per_domain(pool, user_id):
    await _seed_job(pool, user_id=user_id, source_domains=["finance", "tasks"])
    translation_call = await _fake_translation_call_factory(
        {
            "finance": {"action": "log_expense", "amount": 10.0, "category": "food", "payee": None},
            "tasks": {"title": "Real follow-up", "estimated_hours": 1.0, "deadline_iso": None},
        }
    )

    result = await drain_due_jobs(pool, translation_call=translation_call, critic_call=_fake_critic_call, judge_call=_fake_judge_approve)

    assert result.downstream_actions_produced == 2
    assert result.downstream_actions_executed == 2
    events = await pool.fetch("SELECT action_type FROM action_events WHERE user_id = $1 ORDER BY action_type", uuid.UUID(user_id))
    assert {e["action_type"] for e in events} == {"log_expense", "create_task"}

    # DEC-128: both real writes genuinely happened.
    assert await pool.fetchrow("SELECT 1 FROM expenses WHERE user_id = $1", uuid.UUID(user_id)) is not None
    real_task = await pool.fetchrow("SELECT title, status FROM tasks WHERE user_id = $1", uuid.UUID(user_id))
    assert real_task is not None
    assert real_task["title"] == "Real follow-up"
    assert real_task["status"] == "open"


async def test_drain_due_jobs_a_real_multi_domain_job_persists_nothing_at_all_when_a_later_domain_fails(pool, user_id):
    """A real, live regression proof for a real bug found and fixed
    during this session's own self-review: the first domain succeeding
    must never leave a real, durable `action_events` row behind when a
    later domain in the SAME job genuinely fails -- the whole job must
    retry cleanly from scratch, with zero partial state, or a later
    successful retry would duplicate the first domain's own row."""
    retry_id = await _seed_job(pool, user_id=user_id, source_domains=["finance", "tasks"])

    async def failing_second_domain_translation(domain: str, description: str) -> dict:
        if domain == "finance":
            return {"action": "log_expense", "amount": 10.0, "category": "food", "payee": None}
        raise DownstreamTranslationError("simulated real failure on the second domain")

    result = await drain_due_jobs(
        pool, translation_call=failing_second_domain_translation, critic_call=_fake_critic_call, judge_call=_fake_judge_approve
    )

    assert result.jobs_failed == 1
    assert result.downstream_actions_produced == 0
    assert result.downstream_actions_executed == 0
    # The real, load-bearing assertion: finance's own successful review
    # must NOT have left a real, orphaned row behind, even though its
    # own translation/Gate review genuinely succeeded before tasks' own
    # translation failed -- DEC-128 extends this same guarantee to the
    # real expenses write, not just the action_events record.
    assert await pool.fetchrow("SELECT 1 FROM action_events WHERE user_id = $1", uuid.UUID(user_id)) is None
    assert await pool.fetchrow("SELECT 1 FROM expenses WHERE user_id = $1", uuid.UUID(user_id)) is None
    # The real job survives for a clean retry, not silently dropped.
    row = await pool.fetchrow("SELECT attempt_count FROM retry_queue WHERE retry_id = $1", retry_id)
    assert row is not None
    assert row["attempt_count"] == 1


async def test_drain_due_jobs_escalate_to_human_leaves_a_real_still_open_action_event(pool, user_id):
    await _seed_job(pool, user_id=user_id, source_domains=["finance"])
    translation_call = await _fake_translation_call_factory(
        {"finance": {"action": "update_budget", "amount": 500.0, "category": "discretionary", "payee": None}}
    )

    async def judge_escalate(proposal, findings, objections):
        return _verdict("escalate_to_human")

    await drain_due_jobs(pool, translation_call=translation_call, critic_call=_fake_critic_call, judge_call=judge_escalate)

    event = await pool.fetchrow(
        "SELECT gate_decision, outcome, resolved_at FROM action_events WHERE user_id = $1", uuid.UUID(user_id)
    )
    assert event["gate_decision"] == "escalate_to_human"
    assert event["outcome"] is None
    assert event["resolved_at"] is None  # genuinely still needs a human -- would surface via GET /today's needs_you_now


async def test_drain_due_jobs_real_translation_failure_retries_via_the_queue_not_dropped(pool, user_id):
    retry_id = await _seed_job(pool, user_id=user_id, source_domains=["finance"])

    async def failing_translation_call(domain, description):
        raise DownstreamTranslationError("simulated real translation failure")

    result = await drain_due_jobs(pool, translation_call=failing_translation_call, critic_call=_fake_critic_call, judge_call=_fake_judge_approve)

    assert result.jobs_failed == 1
    row = await pool.fetchrow("SELECT attempt_count, next_attempt_at, last_error FROM retry_queue WHERE retry_id = $1", retry_id)
    assert row is not None  # NOT deleted -- a real, live retry opportunity remains
    assert row["attempt_count"] == 1
    assert row["next_attempt_at"] > datetime.now(timezone.utc)
    assert "simulated real translation failure" in row["last_error"]


async def test_drain_due_jobs_an_unknown_job_type_fails_loud_via_the_same_real_retry_path(pool, user_id):
    row = await pool.fetchrow(
        "INSERT INTO retry_queue (job_type, payload) VALUES ($1, $2::jsonb) RETURNING retry_id",
        "some_future_job_type_this_drainer_does_not_know",
        json.dumps({}),
    )
    retry_id = row["retry_id"]
    try:
        translation_call = await _fake_translation_call_factory({})
        result = await drain_due_jobs(pool, translation_call=translation_call, critic_call=_fake_critic_call, judge_call=_fake_judge_approve)
        assert result.jobs_failed == 1
        stored = await pool.fetchrow("SELECT last_error FROM retry_queue WHERE retry_id = $1", retry_id)
        assert "some_future_job_type_this_drainer_does_not_know" in stored["last_error"]
    finally:
        await pool.execute("DELETE FROM retry_queue WHERE retry_id = $1", retry_id)


async def test_mark_job_failed_succeeds_after_a_real_transaction_genuinely_aborts_and_rolls_back(pool, user_id):
    """A real, live regression proof for a real, structural bug this
    session's own CRITICAL-tier review found: `_mark_job_failed()` must
    genuinely succeed even immediately after a real Postgres transaction
    aborted (a genuine SQL-level error, not a Python exception) and
    rolled back on the SAME connection. Before the fix, `drain_due_
    jobs()` called this from INSIDE the still-open, now-aborted
    transaction -- every subsequent statement on it, including this
    real recovery UPDATE, would itself fail with a second, uncaught
    exception, permanently wedging the job at `attempt_count=0` instead
    of genuinely backing off."""
    retry_id = await _seed_job(pool, user_id=user_id, source_domains=[])
    async with pool.acquire() as conn:
        try:
            async with conn.transaction():
                # A real, genuine Postgres-level error -- division by
                # zero -- not a Python-side exception.
                await conn.execute("SELECT 1/0")
        except Exception:
            pass  # a real ROLLBACK already happened via the transaction context manager exiting here
        # The real, load-bearing assertion: this must NOT raise. Before
        # the fix, this would fail with a real
        # "current transaction is aborted" error.
        await _mark_job_failed(conn, retry_id, "simulated real DB-level failure")

    row = await pool.fetchrow("SELECT attempt_count, last_error FROM retry_queue WHERE retry_id = $1", retry_id)
    assert row is not None
    assert row["attempt_count"] == 1
    assert "simulated real DB-level failure" in row["last_error"]


async def test_drain_due_jobs_deadline_conflict_check_genuinely_uses_real_committed_task_hours(pool, user_id):
    """A real, live proof that the tasks-domain Stage A check is
    genuinely backed by the real `tasks` table, not a synthetic
    placeholder: a real, already-committed 40-hour task due the same
    real day as the translated proposal's own deadline should make Stage
    A's own `deadline_conflict_check` genuinely fail (verified_false),
    forcing a real Stage-A-only `revise` -- proven via the real,
    resulting `caught_by_gate` outcome, not by inspecting internals."""
    deadline = datetime.now(timezone.utc) + timedelta(days=1)
    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, $5, 'open')",
        uuid.uuid4(), uuid.UUID(user_id), "A real, already-committed task", 40.0, deadline,
    )
    await _seed_job(pool, user_id=user_id, source_domains=["tasks"])
    translation_call = await _fake_translation_call_factory(
        {"tasks": {"title": "Another real task", "estimated_hours": 4.0, "deadline_iso": deadline.isoformat()}}
    )

    # judge_call should never even be reached for S0/S1 stakes with a
    # real Stage A hard fail -- CREATE_TASK is a low-stakes action type,
    # confirmed via router.STAKES_TABLE, so a failing critic/judge here
    # would itself prove a real bug if ever actually called.
    async def judge_should_not_be_called(proposal, findings, objections):
        raise AssertionError("Judge should not be reached for a real Stage-A hard fail")

    result = await drain_due_jobs(
        pool, translation_call=translation_call, critic_call=_fake_critic_call, judge_call=judge_should_not_be_called
    )

    assert result.jobs_succeeded == 1
    event = await pool.fetchrow("SELECT gate_decision, outcome FROM action_events WHERE user_id = $1", uuid.UUID(user_id))
    assert event["gate_decision"] == "revise"
    assert event["outcome"] == "caught_by_gate"
