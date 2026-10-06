"""Real tests for features/expenses.py -- the redesign's own new
"Finance hub" work. Real inserts/reads against the real, live database
throughout, matching `test_tasks.py`'s own established fixture shape."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.features.expenses import fetch_recent_expenses


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-expenses-{uuid.uuid4()}"
    uid = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield uid
    await pool.execute("DELETE FROM expenses WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(uid))


async def _seed_expense(pool, *, user_id: str, payee: str, amount: float, occurred_at: datetime) -> str:
    expense_id = str(uuid.uuid4())
    await pool.execute(
        "INSERT INTO expenses (expense_id, user_id, payee, amount, occurred_at, source) VALUES ($1, $2, $3, $4, $5, 'manual')",
        uuid.UUID(expense_id), uuid.UUID(user_id), payee, amount, occurred_at,
    )
    return expense_id


async def test_fetch_recent_expenses_a_real_user_with_no_expenses_gets_a_real_empty_list(pool, user_id):
    records = await fetch_recent_expenses(pool, user_id=user_id)
    assert records == []


async def test_fetch_recent_expenses_returns_real_most_recent_first(pool, user_id):
    older = await _seed_expense(pool, user_id=user_id, payee="Older payee", amount=10.0, occurred_at=datetime.now(timezone.utc) - timedelta(days=5))
    newer = await _seed_expense(pool, user_id=user_id, payee="Newer payee", amount=20.0, occurred_at=datetime.now(timezone.utc) - timedelta(days=1))

    records = await fetch_recent_expenses(pool, user_id=user_id)

    assert [r.expense_id for r in records] == [newer, older]
    assert records[0].payee == "Newer payee"
    assert records[0].amount == 20.0


async def test_fetch_recent_expenses_respects_a_real_limit(pool, user_id):
    for i in range(5):
        await _seed_expense(pool, user_id=user_id, payee=f"Payee {i}", amount=float(i), occurred_at=datetime.now(timezone.utc) - timedelta(days=i))

    records = await fetch_recent_expenses(pool, user_id=user_id, limit=3)

    assert len(records) == 3


async def test_fetch_recent_expenses_never_leaks_another_real_users_rows(pool, user_id):
    other_sub = f"test-expenses-other-{uuid.uuid4()}"
    other_uid = await get_or_create_user(pool, google_sub=other_sub, email=None)
    try:
        await _seed_expense(pool, user_id=other_uid, payee="Another real user's payee", amount=99.0, occurred_at=datetime.now(timezone.utc))

        records = await fetch_recent_expenses(pool, user_id=user_id)

        assert records == []
    finally:
        await pool.execute("DELETE FROM expenses WHERE user_id = $1", uuid.UUID(other_uid))
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(other_uid))
