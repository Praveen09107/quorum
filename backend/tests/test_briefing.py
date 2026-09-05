"""Real tests for features/briefing.py (Phase 2, DEC-163) -- real,
live-database integration tests proving the real per-user composition
and the real, per-user failure isolation, against real Postgres rows,
per CLAUDE.md Rule 5. No LLM calls anywhere in this module's own real
logic, so no fake call injection is needed here.

Same real, deliberate safety boundary `test_deadline_watch.py`/`test_
spend_alert.py` already established: every test below scopes `run_
briefing()`'s own `user_ids` explicitly to test-owned rows, never
exercising the real, live, whole-`users`-table default."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.features.briefing import BriefingUserNotFoundError, compose_briefing_for_user, run_briefing


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-briefing-{uuid.uuid4()}"
    uid = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield uid
    await pool.execute("DELETE FROM negotiations WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM tasks WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM expenses WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(uid))


async def _seed_task(pool, *, user_id: str, hours: float, deadline_offset_days: int = 0) -> None:
    deadline = datetime.now(timezone.utc) + timedelta(days=deadline_offset_days)
    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, $5, 'open')",
        uuid.uuid4(), uuid.UUID(user_id), "real test task", hours, deadline,
    )


async def _seed_expense(pool, *, user_id: str, amount: float) -> None:
    await pool.execute(
        "INSERT INTO expenses (expense_id, user_id, payee, amount, occurred_at, source) VALUES ($1, $2, $3, $4, $5, $6)",
        uuid.uuid4(), uuid.UUID(user_id), "real test payee", amount, datetime.now(timezone.utc), "manual",
    )


async def _seed_negotiation(pool, *, user_id: str) -> None:
    await pool.execute(
        "INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at, trigger_source) VALUES ($1, $2, $3, $4, $5)",
        uuid.uuid4(), uuid.UUID(user_id), ["finance", "tasks"], datetime.now(timezone.utc), "deadline_watch",
    )


async def test_compose_briefing_for_user_reflects_real_zero_state_for_a_genuinely_quiet_user(pool, user_id):
    data = await compose_briefing_for_user(pool, user_id=user_id)

    assert data.user_id == user_id
    assert data.capacity.hours_remaining_today == 8.0  # a real, genuinely free day
    assert data.budget.amount_remaining == 50000.0  # the real migration default, untouched
    assert data.pending_action_count == 0
    assert data.active_negotiation_count == 0


async def test_compose_briefing_for_user_reflects_real_committed_hours_and_spend(pool, user_id):
    await _seed_task(pool, user_id=user_id, hours=3.0, deadline_offset_days=0)
    await _seed_expense(pool, user_id=user_id, amount=1000.0)
    await _seed_negotiation(pool, user_id=user_id)

    data = await compose_briefing_for_user(pool, user_id=user_id)

    assert data.capacity.hours_remaining_today == 5.0  # 8.0 real working hours minus a real 3-hour commitment
    assert data.budget.amount_remaining == 49000.0  # 50000.0 minus a real 1000.0 spend
    assert data.active_negotiation_count == 1


async def test_run_briefing_scans_exactly_the_real_users_it_is_given_and_tallies_real_counts(pool, user_id):
    other_google_sub = f"test-briefing-{uuid.uuid4()}"
    other_user_id = await get_or_create_user(pool, google_sub=other_google_sub, email=None)
    try:
        await _seed_negotiation(pool, user_id=user_id)
        # other_user_id gets no real negotiations/tasks -- a real, honest
        # all-quiet briefing.

        result = await run_briefing(pool, user_ids=[user_id, other_user_id])

        assert result.users_scanned == 2
        assert result.users_failed == 0
        assert result.users_with_active_negotiations == 1
        assert result.users_with_pending_actions == 0
    finally:
        await pool.execute("DELETE FROM negotiations WHERE user_id = $1", uuid.UUID(other_user_id))
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(other_user_id))


async def test_compose_briefing_for_user_raises_a_real_specific_error_for_a_genuinely_nonexistent_user(pool):
    """Real regression test for this PR's own CRITICAL-tier review
    (MEDIUM M2): pins the SPECIFIC real exception type this module now
    raises for its own explicit existence check, so a future change
    that breaks this guarantee in some other way (a fabricated all-zero
    briefing coming back cleanly instead) fails this test for the right
    reason, not just "some exception happened."""
    ghost_user_id = str(uuid.uuid4())  # syntactically real, genuinely no real users row

    with pytest.raises(BriefingUserNotFoundError):
        await compose_briefing_for_user(pool, user_id=ghost_user_id)


async def test_run_briefing_a_real_nonexistent_user_id_is_a_real_tallied_failure_not_a_silent_all_zero_briefing(pool, user_id):
    """Real proof a syntactically real but genuinely nonexistent
    user_id surfaces as a real, tallied failure, never as a fabricated
    "0 pending actions, 0 negotiations" briefing that looks identical to
    a real, quiet user."""
    ghost_user_id = str(uuid.uuid4())  # syntactically real, genuinely no real users row

    result = await run_briefing(pool, user_ids=[ghost_user_id, user_id])

    assert result.users_failed == 1
    assert result.users_scanned == 1


async def test_run_briefing_a_real_failure_for_one_user_never_blocks_the_rest(pool, user_id):
    await _seed_negotiation(pool, user_id=user_id)

    result = await run_briefing(pool, user_ids=["not-a-real-uuid", user_id])

    assert result.users_failed == 1
    assert result.users_scanned == 1
    assert result.users_with_active_negotiations == 1
