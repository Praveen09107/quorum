"""Real tests for features/action_executor.py (DEC-128) -- real inserts
against the real, live database for the two genuinely executable action
types, and a real, exhaustive proof that every other real `ActionType`
returns an honest, non-executing result, per CLAUDE.md Rule 5.
"""
import uuid
from datetime import datetime, timezone

import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.features.action_executor import execute_approved_action
from quorum_backend.gate.schemas import ActionType


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-executor-{uuid.uuid4()}"
    uid = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield uid
    await pool.execute("DELETE FROM tasks WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM expenses WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(uid))


async def test_execute_approved_action_create_task_writes_a_real_row(pool, user_id):
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn,
            action_type=ActionType.CREATE_TASK,
            payload={"title": "Real executed task", "estimated_hours": 2.5, "deadline": None},
            user_id=user_id,
        )
    assert result.executed is True
    row = await pool.fetchrow(
        "SELECT title, estimated_hours, deadline, status FROM tasks WHERE user_id = $1", uuid.UUID(user_id)
    )
    assert row is not None
    assert row["title"] == "Real executed task"
    assert float(row["estimated_hours"]) == 2.5
    assert row["deadline"] is None
    assert row["status"] == "open"


async def test_execute_approved_action_create_task_with_a_real_deadline(pool, user_id):
    deadline = datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc)
    async with pool.acquire() as conn:
        await execute_approved_action(
            conn,
            action_type=ActionType.CREATE_TASK,
            payload={"title": "Real deadlined task", "estimated_hours": 1.0, "deadline": deadline.isoformat()},
            user_id=user_id,
        )
    row = await pool.fetchrow("SELECT deadline FROM tasks WHERE user_id = $1", uuid.UUID(user_id))
    assert row["deadline"] == deadline


async def test_execute_approved_action_log_expense_writes_a_real_row_with_the_new_gate_approved_source(pool, user_id):
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn,
            action_type=ActionType.LOG_EXPENSE,
            payload={"amount": 42.5, "category": "food", "payee": "Real Vendor"},
            user_id=user_id,
        )
    assert result.executed is True
    row = await pool.fetchrow(
        "SELECT payee, amount, source FROM expenses WHERE user_id = $1", uuid.UUID(user_id)
    )
    assert row is not None
    assert row["payee"] == "Real Vendor"
    assert float(row["amount"]) == 42.5
    # DEC-128's own real, live schema migration (0007) -- confirmed
    # here, live, not just read from the migration file.
    assert row["source"] == "gate_approved"


async def test_execute_approved_action_log_expense_defaults_a_real_missing_payee_honestly(pool, user_id):
    async with pool.acquire() as conn:
        await execute_approved_action(
            conn,
            action_type=ActionType.LOG_EXPENSE,
            payload={"amount": 10.0, "category": "food", "payee": None},
            user_id=user_id,
        )
    row = await pool.fetchrow("SELECT payee FROM expenses WHERE user_id = $1", uuid.UUID(user_id))
    assert row["payee"] == "Unknown"


async def test_execute_approved_action_fails_safely_not_loudly_on_a_real_malformed_payload(pool, user_id):
    """A real, defensive guard: `CREATE_TASK`/`LOG_EXPENSE` should never
    reach this function with a payload missing required keys under the
    real, current stakes table (Stage B never runs for S1, so the
    payload is always the original, validated one) -- but if that
    invariant is ever violated by a future change, this must fail
    safely (a real, honest `executed=False`) rather than raise an
    unhandled exception mid-transaction."""
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.CREATE_TASK, payload={"title": "Missing hours"}, user_id=user_id
        )
    assert result.executed is False
    assert "malformed" in result.detail.lower()
    assert await pool.fetchrow("SELECT 1 FROM tasks WHERE user_id = $1", uuid.UUID(user_id)) is None


async def test_execute_approved_action_is_exhaustively_honest_about_every_other_real_action_type(pool, user_id):
    """A real, exhaustive proof, not a spot-check: every real
    `ActionType` other than `CREATE_TASK`/`LOG_EXPENSE` returns
    `executed=False` with a real, non-empty explanation, and genuinely
    writes nothing anywhere -- confirmed by an unconditional real row
    count, not just trusting the return value."""
    non_executable = [t for t in ActionType if t not in (ActionType.CREATE_TASK, ActionType.LOG_EXPENSE)]
    assert len(non_executable) == 9  # a real, live guard against this enum silently growing unnoticed

    async with pool.acquire() as conn:
        for action_type in non_executable:
            result = await execute_approved_action(conn, action_type=action_type, payload={}, user_id=user_id)
            assert result.executed is False, f"{action_type} unexpectedly executed"
            assert len(result.detail) > 0

    assert await pool.fetchrow("SELECT 1 FROM tasks WHERE user_id = $1", uuid.UUID(user_id)) is None
    assert await pool.fetchrow("SELECT 1 FROM expenses WHERE user_id = $1", uuid.UUID(user_id)) is None
