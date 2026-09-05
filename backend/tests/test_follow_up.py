"""Real tests for features/follow_up.py (Phase 2, DEC-163) -- real,
live-database integration tests proving the real per-user stale-message
count and the real, per-user failure isolation, against real Postgres
rows, per CLAUDE.md Rule 5. This module deliberately takes no real
action on what it finds (see its own top-of-file docstring for why);
these tests prove the real counting/wiring, not any action-taking,
since none exists yet.

Same real, deliberate safety boundary `test_deadline_watch.py`/`test_
spend_alert.py`/`test_briefing.py` already established: every test
below scopes `run_follow_up()`'s own `user_ids` explicitly to
test-owned rows, never exercising the real, live, whole-`users`-table
default."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.features.follow_up import count_stale_messages_for_user, run_follow_up
from quorum_backend.features.waiting_on import record_sent_message


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-follow-up-{uuid.uuid4()}"
    uid = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield uid
    await pool.execute("DELETE FROM sent_messages WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(uid))


async def test_count_stale_messages_for_user_is_a_real_honest_zero_for_a_quiet_user(pool, user_id):
    assert await count_stale_messages_for_user(pool, user_id=user_id) == 0


async def test_count_stale_messages_for_user_counts_only_real_stale_unreplied_sends(pool, user_id):
    now = datetime.now(timezone.utc)
    await record_sent_message(
        pool, user_id=user_id, message_id="stale", thread_id="t1", recipient="a@x.com",
        subject="stale one", sent_at=now - timedelta(days=10),
    )
    await record_sent_message(
        pool, user_id=user_id, message_id="fresh", thread_id="t2", recipient="b@x.com",
        subject="fresh one", sent_at=now - timedelta(hours=1),
    )

    assert await count_stale_messages_for_user(pool, user_id=user_id) == 1


async def test_run_follow_up_scans_exactly_the_real_users_it_is_given_and_tallies_real_counts(pool, user_id):
    other_google_sub = f"test-follow-up-{uuid.uuid4()}"
    other_user_id = await get_or_create_user(pool, google_sub=other_google_sub, email=None)
    try:
        await record_sent_message(
            pool, user_id=user_id, message_id="stale", thread_id="t1", recipient="a@x.com",
            subject="stale one", sent_at=datetime.now(timezone.utc) - timedelta(days=10),
        )
        # other_user_id gets no real sent messages at all -- a real, honest zero.

        result = await run_follow_up(pool, user_ids=[user_id, other_user_id])

        assert result.users_scanned == 2
        assert result.users_failed == 0
        assert result.users_with_stale_messages == 1
        assert result.stale_messages_detected == 1
        assert result.action_taken is False
    finally:
        await pool.execute("DELETE FROM sent_messages WHERE user_id = $1", uuid.UUID(other_user_id))
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(other_user_id))


async def test_run_follow_up_a_real_failure_for_one_user_never_blocks_the_rest(pool, user_id):
    await record_sent_message(
        pool, user_id=user_id, message_id="stale", thread_id="t1", recipient="a@x.com",
        subject="stale one", sent_at=datetime.now(timezone.utc) - timedelta(days=10),
    )

    result = await run_follow_up(pool, user_ids=["not-a-real-uuid", user_id])

    assert result.users_failed == 1
    assert result.users_scanned == 1
    assert result.stale_messages_detected == 1
