"""Real tests for features/deadline_watch.py (Phase 2, DEC-13x) -- real,
live-database integration tests proving the real per-user scan, real
claim/domain-state construction, real trigger, and real idempotency
guard, all against real Postgres rows, per CLAUDE.md Rule 5. No LLM
calls anywhere in this module's own real logic, so no fake call
injection is needed here (unlike test_retry_queue_drainer.py).

A REAL, DELIBERATE SAFETY BOUNDARY, DISCLOSED HERE: every test below
either calls `scan_one_user()` directly, or calls `run_deadline_watch()`
with its `user_ids` explicitly scoped to specific, cleaned-up test-only
rows -- the real, live default (`user_ids=None`, the whole `users`
table) is never exercised here. Unlike `drain_due_jobs()` (`test_
retry_queue_drainer.py`), which only ever processes rows a test
explicitly enqueued into a real, naturally-empty `retry_queue`, an
unscoped `run_deadline_watch()` would touch the ENTIRE real `users`
table -- including this deployment's one real, live, non-test account
(`scripts/seed_demo_dataset.py`'s own established fact) -- risking a
real, unwanted write against real, production-meaningful data as a
side effect of running this test suite. `test_main.py`'s route-level
test covers the real, unscoped default path separately, via a
monkeypatched `run_deadline_watch()`, never a real, whole-table call
either.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.features.deadline_watch import ScanOutcome, run_deadline_watch, scan_one_user


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-deadline-watch-{uuid.uuid4()}"
    uid = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield uid
    await pool.execute("DELETE FROM negotiations WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM tasks WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM expenses WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(uid))


async def _seed_task(pool, *, user_id: str, hours: float, deadline_offset_days: int, status: str = "open") -> None:
    now = datetime.now(timezone.utc)
    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, $5, $6)",
        uuid.uuid4(), uuid.UUID(user_id), "real test task", hours,
        now + timedelta(days=deadline_offset_days), status,
    )


async def _seed_expense(pool, *, user_id: str, amount: float, occurred_days_ago: int = 0) -> None:
    now = datetime.now(timezone.utc)
    await pool.execute(
        "INSERT INTO expenses (expense_id, user_id, payee, amount, occurred_at, source) VALUES ($1, $2, $3, $4, $5, $6)",
        uuid.uuid4(), uuid.UUID(user_id), "real test payee", amount, now - timedelta(days=occurred_days_ago), "manual",
    )


async def test_scan_one_user_returns_no_claim_when_no_real_task_has_a_future_deadline(pool, user_id):
    # A real, done task with a past deadline -- genuinely no real, open,
    # future commitment to build a claim from.
    await _seed_task(pool, user_id=user_id, hours=2.0, deadline_offset_days=-3, status="done")

    async with pool.acquire() as conn:
        outcome, negotiation_id = await scan_one_user(conn, user_id=user_id)

    assert outcome is ScanOutcome.NO_CLAIM
    assert negotiation_id is None


async def test_scan_one_user_returns_no_conflict_for_real_light_commitments(pool, user_id):
    # A real task due in 5 real days needing only 2 hours -- 5 * 8.0 = 40
    # real available hours, genuinely not exceeded. A small real expense,
    # genuinely nowhere near half the real monthly budget.
    await _seed_task(pool, user_id=user_id, hours=2.0, deadline_offset_days=5)
    await _seed_expense(pool, user_id=user_id, amount=100.0)

    async with pool.acquire() as conn:
        outcome, negotiation_id = await scan_one_user(conn, user_id=user_id)

    assert outcome is ScanOutcome.NO_CONFLICT
    assert negotiation_id is None

    row = await pool.fetchrow("SELECT 1 FROM negotiations WHERE user_id = $1", uuid.UUID(user_id))
    assert row is None


async def test_scan_one_user_creates_a_real_negotiation_for_a_genuine_conflict(pool, user_id):
    # A real task due tomorrow (1 real day -> 8.0 real available hours)
    # needing 12 real hours -- genuinely exceeds real available capacity.
    await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)
    # A real expense this real month exceeding half the 50000.0 real
    # monthly budget limit (30000 > 25000).
    await _seed_expense(pool, user_id=user_id, amount=30000.0)

    async with pool.acquire() as conn:
        outcome, negotiation_id = await scan_one_user(conn, user_id=user_id)

    assert outcome is ScanOutcome.CREATED
    assert negotiation_id is not None

    row = await pool.fetchrow(
        "SELECT user_id, conflicted_domains, resolved_at, positions, options FROM negotiations WHERE negotiation_id = $1",
        uuid.UUID(negotiation_id),
    )
    assert row is not None
    assert str(row["user_id"]) == user_id
    assert set(row["conflicted_domains"]) == {"tasks", "finance"}
    assert row["resolved_at"] is None
    # A real, honest, bare negotiation -- detail generation is a real,
    # separate, still-open item, not silently fabricated here.
    assert row["positions"] is None
    assert row["options"] is None


async def test_scan_one_user_skips_when_a_real_unresolved_negotiation_already_exists(pool, user_id):
    await pool.execute(
        "INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at) VALUES ($1, $2, $3, $4)",
        uuid.uuid4(), uuid.UUID(user_id), ["finance", "tasks"], datetime.now(timezone.utc),
    )
    await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)
    await _seed_expense(pool, user_id=user_id, amount=30000.0)

    async with pool.acquire() as conn:
        outcome, negotiation_id = await scan_one_user(conn, user_id=user_id)

    assert outcome is ScanOutcome.ALREADY_NEGOTIATING
    assert negotiation_id is None

    count = await pool.fetchval("SELECT COUNT(*) FROM negotiations WHERE user_id = $1", uuid.UUID(user_id))
    assert count == 1  # never duplicated


async def test_scan_one_user_only_conflicts_tasks_domain_when_finance_is_genuinely_fine(pool, user_id):
    # Real overcommitted tasks, but real light spending -- a genuine
    # single-domain conflict never triggers a negotiation
    # (scan_for_conflicts requires 2+ conflicted domains by design).
    await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)
    await _seed_expense(pool, user_id=user_id, amount=100.0)

    async with pool.acquire() as conn:
        outcome, negotiation_id = await scan_one_user(conn, user_id=user_id)

    assert outcome is ScanOutcome.NO_CONFLICT
    assert negotiation_id is None


async def test_run_deadline_watch_scans_exactly_the_real_users_it_is_given_and_tallies_real_outcomes(pool, user_id):
    # A second, genuinely independent real test user, alongside the
    # fixture's own -- proves run_deadline_watch iterates every real
    # user IN ITS GIVEN SCOPE, not just the first one found. Scoped
    # explicitly to these two real, test-owned user_ids only -- see
    # this module's own top-of-file docstring for why the real,
    # whole-table default is never exercised here.
    other_google_sub = f"test-deadline-watch-{uuid.uuid4()}"
    other_user_id = await get_or_create_user(pool, google_sub=other_google_sub, email=None)
    try:
        await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)
        await _seed_expense(pool, user_id=user_id, amount=30000.0)
        # other_user_id gets no real tasks/expenses at all -- a real,
        # honest NO_CLAIM case.

        result = await run_deadline_watch(pool, user_ids=[user_id, other_user_id])

        assert result.users_scanned == 2
        assert result.users_failed == 0
        assert result.negotiations_created == 1
        assert result.outcome_counts["CREATED"] == 1
        assert result.outcome_counts["NO_CLAIM"] == 1

        row = await pool.fetchrow("SELECT 1 FROM negotiations WHERE user_id = $1", uuid.UUID(user_id))
        assert row is not None
    finally:
        await pool.execute("DELETE FROM negotiations WHERE user_id = $1", uuid.UUID(other_user_id))
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(other_user_id))


async def test_run_deadline_watch_a_real_failure_for_one_user_never_blocks_the_rest(pool, user_id):
    """Real regression test for the real bug this session's own
    adversarial self-review found and fixed, before any review
    subagent ran: a genuine per-user failure (here, a real,
    malformed user_id causing a real `uuid.UUID()` ValueError inside
    `scan_one_user`'s own real queries) must never abort the scan for
    every other real user in the same run."""
    await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)
    await _seed_expense(pool, user_id=user_id, amount=30000.0)

    result = await run_deadline_watch(pool, user_ids=["not-a-real-uuid", user_id])

    assert result.users_failed == 1
    assert result.users_scanned == 1  # only the real, valid user_id counts as genuinely scanned
    assert result.negotiations_created == 1
    assert result.outcome_counts["CREATED"] == 1

    row = await pool.fetchrow("SELECT 1 FROM negotiations WHERE user_id = $1", uuid.UUID(user_id))
    assert row is not None
