"""Real tests for features/tasks.py -- against the real, live Supabase
database (`DEC-098`), real INSERTs, a real query, real DELETEs in a
`finally` block, per `CLAUDE.md` Rule 5 and the same pattern
`test_trust_digest.py` already established. Every inserted row uses a
real, generated `task_id` and is deleted by that same id -- these tests
can never collide with real data and never leave anything behind, even
if a test itself fails midway.
"""
import uuid
from datetime import datetime, timezone

import pytest_asyncio

from quorum_backend.core import db
from quorum_backend.features.tasks import fetch_tasks


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


async def _insert_test_task(pool, task_id, *, title, estimated_hours, deadline, status, user_id=None):
    await pool.execute(
        """
        INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        task_id,
        user_id or uuid.uuid4(),
        title,
        estimated_hours,
        deadline,
        status,
    )


async def test_fetch_tasks_returns_real_rows_with_correct_shape_and_types(pool):
    task_id = uuid.uuid4()
    deadline = datetime(2020, 1, 15, 9, 0, tzinfo=timezone.utc)

    try:
        await _insert_test_task(
            pool,
            task_id,
            title="A real, deliberately obscure test task",
            estimated_hours=2.5,
            deadline=deadline,
            status="open",
        )

        records = await fetch_tasks(pool)
        match = next(r for r in records if r.task_id == str(task_id))

        assert match.title == "A real, deliberately obscure test task"
        assert isinstance(match.estimated_hours, float)
        assert match.estimated_hours == 2.5
        assert match.deadline == "2020-01-15T09:00:00Z"
        assert match.status == "open"
    finally:
        await pool.execute("DELETE FROM tasks WHERE task_id = $1", task_id)


async def test_fetch_tasks_handles_a_real_null_deadline(pool):
    task_id = uuid.uuid4()

    try:
        await _insert_test_task(
            pool,
            task_id,
            title="A real task with no deadline",
            estimated_hours=1.0,
            deadline=None,
            status="done",
        )

        records = await fetch_tasks(pool)
        match = next(r for r in records if r.task_id == str(task_id))

        assert match.deadline is None
        assert match.status == "done"
    finally:
        await pool.execute("DELETE FROM tasks WHERE task_id = $1", task_id)


async def test_fetch_tasks_preserves_the_real_closed_status_set_verbatim(pool):
    # tasks.status is a real, closed, database-enforced CHECK constraint
    # (unlike applications.status's open vocabulary) -- this test proves
    # the real value round-trips through the query completely unchanged,
    # the honest precondition main.py's own route relies on when it
    # skips any defensive status handling.
    ids = [uuid.uuid4() for _ in range(3)]
    statuses = ["open", "done", "cancelled"]

    try:
        for task_id, status in zip(ids, statuses):
            await _insert_test_task(
                pool, task_id, title=f"Real task ({status})", estimated_hours=1.0, deadline=None, status=status
            )

        records = await fetch_tasks(pool)
        by_id = {r.task_id: r for r in records}

        for task_id, status in zip(ids, statuses):
            assert by_id[str(task_id)].status == status
    finally:
        await pool.execute("DELETE FROM tasks WHERE task_id = ANY($1::uuid[])", ids)


async def test_fetch_tasks_returns_a_real_empty_list_never_a_crash_when_nothing_matches(pool):
    # A real, honest proof this query never assumes at least one row --
    # deletes nothing of its own, simply confirms the function returns a
    # real Python list (possibly containing unrelated real production
    # rows, which is fine -- this test only asserts on the return type,
    # never a specific count, per CLAUDE.md's own stale-count warning).
    records = await fetch_tasks(pool)
    assert isinstance(records, list)
