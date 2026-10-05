"""Real tests for features/task_status.py -- closes a real, previously-
undiscovered gap: `tasks.status` has never actually changed from
`'open'` anywhere in this backend's history. Real inserts/reads against
the real, live database throughout, matching `test_action_approval.py`'s
own established fixture shape."""
import asyncio
import uuid

import pytest
import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.features.task_status import (
    TaskNotFound,
    TaskNotUpdatable,
    cancel_task,
    complete_task,
)


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-task-status-{uuid.uuid4()}"
    uid = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield uid
    await pool.execute("DELETE FROM tasks WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(uid))


async def _seed_task(pool, *, user_id: str, status: str = "open") -> str:
    task_id = str(uuid.uuid4())
    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) "
        "VALUES ($1, $2, $3, $4, $5, $6)",
        uuid.UUID(task_id), uuid.UUID(user_id), "A real test task", 1.5, None, status,
    )
    return task_id


# --- complete_task ---


async def test_complete_task_raises_not_found_for_a_real_nonexistent_task_id(pool, user_id):
    with pytest.raises(TaskNotFound):
        await complete_task(pool, user_id=user_id, task_id=str(uuid.uuid4()))


async def test_complete_task_raises_not_found_when_the_row_belongs_to_a_different_real_user(pool, user_id):
    other_sub = f"test-task-status-other-{uuid.uuid4()}"
    other_uid = await get_or_create_user(pool, google_sub=other_sub, email=None)
    try:
        task_id = await _seed_task(pool, user_id=other_uid)
        with pytest.raises(TaskNotFound):
            await complete_task(pool, user_id=user_id, task_id=task_id)
        row = await pool.fetchrow("SELECT status FROM tasks WHERE task_id = $1", uuid.UUID(task_id))
        assert row["status"] == "open"  # never touched
    finally:
        await pool.execute("DELETE FROM tasks WHERE user_id = $1", uuid.UUID(other_uid))
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(other_uid))


async def test_complete_task_marks_a_real_open_task_done(pool, user_id):
    task_id = await _seed_task(pool, user_id=user_id)
    await complete_task(pool, user_id=user_id, task_id=task_id)
    row = await pool.fetchrow("SELECT status FROM tasks WHERE task_id = $1", uuid.UUID(task_id))
    assert row["status"] == "done"


async def test_complete_task_raises_not_updatable_when_already_done(pool, user_id):
    task_id = await _seed_task(pool, user_id=user_id, status="done")
    with pytest.raises(TaskNotUpdatable):
        await complete_task(pool, user_id=user_id, task_id=task_id)


async def test_complete_task_raises_not_updatable_when_already_cancelled(pool, user_id):
    task_id = await _seed_task(pool, user_id=user_id, status="cancelled")
    with pytest.raises(TaskNotUpdatable):
        await complete_task(pool, user_id=user_id, task_id=task_id)


async def test_complete_task_two_real_concurrent_completions_on_the_same_task_only_one_ever_wins(pool, user_id):
    """The real, conditional `UPDATE ... WHERE status = 'open'` is its
    own atomic claim -- no separate lock needed (unlike `action_
    approval.py`'s own multi-step flow), since there is no real external
    call in between to hold a lock across."""
    task_id = await _seed_task(pool, user_id=user_id)

    results = await asyncio.gather(
        complete_task(pool, user_id=user_id, task_id=task_id),
        complete_task(pool, user_id=user_id, task_id=task_id),
        return_exceptions=True,
    )

    successes = [r for r in results if r is None]
    failures = [r for r in results if isinstance(r, TaskNotUpdatable)]
    assert len(successes) == 1
    assert len(failures) == 1


# --- cancel_task ---


async def test_cancel_task_raises_not_found_for_a_real_nonexistent_task_id(pool, user_id):
    with pytest.raises(TaskNotFound):
        await cancel_task(pool, user_id=user_id, task_id=str(uuid.uuid4()))


async def test_cancel_task_marks_a_real_open_task_cancelled(pool, user_id):
    task_id = await _seed_task(pool, user_id=user_id)
    await cancel_task(pool, user_id=user_id, task_id=task_id)
    row = await pool.fetchrow("SELECT status FROM tasks WHERE task_id = $1", uuid.UUID(task_id))
    assert row["status"] == "cancelled"


async def test_cancel_task_raises_not_updatable_when_already_done(pool, user_id):
    task_id = await _seed_task(pool, user_id=user_id, status="done")
    with pytest.raises(TaskNotUpdatable):
        await cancel_task(pool, user_id=user_id, task_id=task_id)


async def test_cancel_task_never_touches_a_different_real_users_row(pool, user_id):
    other_sub = f"test-task-status-other-{uuid.uuid4()}"
    other_uid = await get_or_create_user(pool, google_sub=other_sub, email=None)
    try:
        task_id = await _seed_task(pool, user_id=other_uid)
        with pytest.raises(TaskNotFound):
            await cancel_task(pool, user_id=user_id, task_id=task_id)
        row = await pool.fetchrow("SELECT status FROM tasks WHERE task_id = $1", uuid.UUID(task_id))
        assert row["status"] == "open"
    finally:
        await pool.execute("DELETE FROM tasks WHERE user_id = $1", uuid.UUID(other_uid))
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(other_uid))
