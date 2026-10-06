"""Real tests for features/week_summary.py -- the redesign's own new
"This week across your agents" cross-domain strip. Real inserts/reads
against the real, live database throughout, matching this project's
other feature-module tests."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.features.week_summary import fetch_week_summary


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-week-summary-{uuid.uuid4()}"
    uid = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield uid
    await pool.execute("DELETE FROM tasks WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM expenses WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM applications WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM sent_messages WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(uid))


async def test_fetch_week_summary_a_real_fresh_user_gets_real_honest_zeros_everywhere(pool, user_id):
    """A real, brand-new user with no real tasks/expenses/applications/
    sent_messages anywhere gets a real, honest all-zero summary -- never
    a crash on an empty real corpus."""
    summary = await fetch_week_summary(pool, user_id=user_id)

    assert summary.tasks_due_this_week == 0
    assert summary.month_to_date_spend == 0.0
    assert summary.monthly_budget_limit > 0  # the real, migration-default limit
    assert summary.applications_in_progress == 0
    assert summary.waiting_on_count == 0


async def test_fetch_week_summary_counts_a_real_open_task_due_within_7_days(pool, user_id):
    due_soon = uuid.uuid4()
    due_later = uuid.uuid4()
    done_soon = uuid.uuid4()
    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, $5, 'open')",
        due_soon, uuid.UUID(user_id), "Due in 3 real days", 1.0, datetime.now(timezone.utc) + timedelta(days=3),
    )
    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, $5, 'open')",
        due_later, uuid.UUID(user_id), "Due in 30 real days", 1.0, datetime.now(timezone.utc) + timedelta(days=30),
    )
    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, $5, 'done')",
        done_soon, uuid.UUID(user_id), "Already done, due in 2 real days", 1.0, datetime.now(timezone.utc) + timedelta(days=2),
    )

    summary = await fetch_week_summary(pool, user_id=user_id)

    # Only the real, OPEN task due within 7 real days counts -- the
    # far-future one and the already-done one are both correctly
    # excluded.
    assert summary.tasks_due_this_week == 1


async def test_fetch_week_summary_sums_real_month_to_date_expenses_only(pool, user_id):
    this_month = uuid.uuid4()
    last_month = uuid.uuid4()
    await pool.execute(
        "INSERT INTO expenses (expense_id, user_id, payee, amount, occurred_at, source) VALUES ($1, $2, $3, $4, now(), 'manual')",
        this_month, uuid.UUID(user_id), "A real this-month payee", 150.0,
    )
    await pool.execute(
        "INSERT INTO expenses (expense_id, user_id, payee, amount, occurred_at, source) VALUES ($1, $2, $3, $4, now() - interval '2 months', 'manual')",
        last_month, uuid.UUID(user_id), "A real two-months-ago payee", 999.0,
    )

    summary = await fetch_week_summary(pool, user_id=user_id)

    assert summary.month_to_date_spend == 150.0


async def test_fetch_week_summary_counts_real_applications_not_rejected(pool, user_id):
    applied = uuid.uuid4()
    offer = uuid.uuid4()
    rejected = uuid.uuid4()
    await pool.execute(
        "INSERT INTO applications (application_id, user_id, company, role, status) VALUES ($1, $2, $3, $4, $5)",
        applied, uuid.UUID(user_id), "Real Co A", "Engineer", "applied",
    )
    await pool.execute(
        "INSERT INTO applications (application_id, user_id, company, role, status) VALUES ($1, $2, $3, $4, $5)",
        offer, uuid.UUID(user_id), "Real Co B", "Engineer", "offer",
    )
    await pool.execute(
        "INSERT INTO applications (application_id, user_id, company, role, status) VALUES ($1, $2, $3, $4, $5)",
        rejected, uuid.UUID(user_id), "Real Co C", "Engineer", "rejected",
    )

    summary = await fetch_week_summary(pool, user_id=user_id)

    assert summary.applications_in_progress == 2


async def test_fetch_week_summary_counts_real_stale_unreplied_sent_messages(pool, user_id):
    stale = ("stale-msg", "stale-thread", datetime.now(timezone.utc) - timedelta(days=10))
    fresh = ("fresh-msg", "fresh-thread", datetime.now(timezone.utc) - timedelta(days=1))
    replied = ("replied-msg", "replied-thread", datetime.now(timezone.utc) - timedelta(days=20))
    await pool.execute(
        "INSERT INTO sent_messages (user_id, message_id, thread_id, recipient, subject, sent_at, replied_at) VALUES ($1, $2, $3, $4, $5, $6, NULL)",
        uuid.UUID(user_id), stale[0], stale[1], "a@example.com", "stale", stale[2],
    )
    await pool.execute(
        "INSERT INTO sent_messages (user_id, message_id, thread_id, recipient, subject, sent_at, replied_at) VALUES ($1, $2, $3, $4, $5, $6, NULL)",
        uuid.UUID(user_id), fresh[0], fresh[1], "b@example.com", "fresh", fresh[2],
    )
    await pool.execute(
        "INSERT INTO sent_messages (user_id, message_id, thread_id, recipient, subject, sent_at, replied_at) VALUES ($1, $2, $3, $4, $5, $6, $7)",
        uuid.UUID(user_id), replied[0], replied[1], "c@example.com", "replied", replied[2], datetime.now(timezone.utc) - timedelta(days=5),
    )

    summary = await fetch_week_summary(pool, user_id=user_id)

    assert summary.waiting_on_count == 1


async def test_fetch_week_summary_never_leaks_another_real_users_rows(pool, user_id):
    other_sub = f"test-week-summary-other-{uuid.uuid4()}"
    other_uid = await get_or_create_user(pool, google_sub=other_sub, email=None)
    task_id = uuid.uuid4()
    try:
        await pool.execute(
            "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, $5, 'open')",
            task_id, uuid.UUID(other_uid), "Another real user's task", 1.0, datetime.now(timezone.utc) + timedelta(days=1),
        )

        summary = await fetch_week_summary(pool, user_id=user_id)

        assert summary.tasks_due_this_week == 0
    finally:
        await pool.execute("DELETE FROM tasks WHERE task_id = $1", task_id)
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(other_uid))
