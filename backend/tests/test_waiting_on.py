"""Real tests for features/waiting_on.py (Phase 4, DEC-13x)."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.features.waiting_on import (
    WAITING_ON_STALENESS_THRESHOLD_DAYS,
    SentMessage,
    fetch_stale_waiting_on,
    fetch_unreplied_sent_messages,
    find_stale_waiting_on,
    mark_thread_replied,
    record_sent_message,
)


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-waiting-on-{uuid.uuid4()}"
    uid = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield uid
    await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(uid))


# --- Pure function: find_stale_waiting_on ---


def test_find_stale_waiting_on_excludes_a_message_sent_within_the_real_threshold():
    now = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
    fresh = SentMessage(recipient="a@x.com", subject="fresh", sent_at=now - timedelta(days=1))
    assert find_stale_waiting_on([fresh], now=now) == []


def test_find_stale_waiting_on_includes_a_message_sent_exactly_at_the_real_threshold():
    now = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
    at_threshold = SentMessage(recipient="a@x.com", subject="at threshold", sent_at=now - timedelta(days=WAITING_ON_STALENESS_THRESHOLD_DAYS))
    assert find_stale_waiting_on([at_threshold], now=now) == [at_threshold]


def test_find_stale_waiting_on_includes_a_message_sent_well_past_the_real_threshold():
    now = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
    old = SentMessage(recipient="a@x.com", subject="old", sent_at=now - timedelta(days=10))
    assert find_stale_waiting_on([old], now=now) == [old]


def test_find_stale_waiting_on_a_real_custom_threshold_is_honored():
    now = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
    message = SentMessage(recipient="a@x.com", subject="s", sent_at=now - timedelta(days=2))
    assert find_stale_waiting_on([message], now=now, threshold_days=4) == []
    assert find_stale_waiting_on([message], now=now, threshold_days=1) == [message]


def test_find_stale_waiting_on_an_empty_list_returns_empty_not_a_crash():
    assert find_stale_waiting_on([]) == []


def test_find_stale_waiting_on_defaults_now_to_the_real_current_time():
    old = SentMessage(recipient="a@x.com", subject="s", sent_at=datetime.now(timezone.utc) - timedelta(days=30))
    assert find_stale_waiting_on([old]) == [old]


# --- Real, live-database tests ---


async def test_record_sent_message_inserts_and_is_idempotent_on_a_real_repeat_call(pool, user_id):
    inserted_first = await record_sent_message(
        pool, user_id=user_id, message_id="msg-1", thread_id="thread-1",
        recipient="a@x.com", subject="Hello", sent_at=datetime.now(timezone.utc),
    )
    assert inserted_first is True

    inserted_second = await record_sent_message(
        pool, user_id=user_id, message_id="msg-1", thread_id="thread-1",
        recipient="a@x.com", subject="Hello", sent_at=datetime.now(timezone.utc),
    )
    assert inserted_second is False  # a real, honest no-op -- already recorded

    count = await pool.fetchval("SELECT COUNT(*) FROM sent_messages WHERE user_id = $1", uuid.UUID(user_id))
    assert count == 1  # never a duplicate row


async def test_fetch_unreplied_sent_messages_excludes_a_real_already_replied_message(pool, user_id):
    now = datetime.now(timezone.utc)
    await record_sent_message(pool, user_id=user_id, message_id="unreplied", thread_id="t1", recipient="a@x.com", subject="s1", sent_at=now)
    await record_sent_message(pool, user_id=user_id, message_id="replied", thread_id="t2", recipient="b@x.com", subject="s2", sent_at=now)
    await pool.execute("UPDATE sent_messages SET replied_at = $1 WHERE user_id = $2 AND message_id = 'replied'", now, uuid.UUID(user_id))

    messages = await fetch_unreplied_sent_messages(pool, user_id=user_id)

    assert [m.subject for m in messages] == ["s1"]


async def test_fetch_unreplied_sent_messages_orders_oldest_first(pool, user_id):
    now = datetime.now(timezone.utc)
    await record_sent_message(pool, user_id=user_id, message_id="newer", thread_id="t1", recipient="a@x.com", subject="newer", sent_at=now - timedelta(days=1))
    await record_sent_message(pool, user_id=user_id, message_id="older", thread_id="t2", recipient="a@x.com", subject="older", sent_at=now - timedelta(days=5))

    messages = await fetch_unreplied_sent_messages(pool, user_id=user_id)

    assert [m.subject for m in messages] == ["older", "newer"]


async def test_mark_thread_replied_marks_every_real_unreplied_message_in_the_same_thread(pool, user_id):
    """A single real incoming reply answers every prior real message
    this user sent in that same thread, not just the most recent one --
    a real, deliberate design choice, not an oversight."""
    now = datetime.now(timezone.utc)
    await record_sent_message(pool, user_id=user_id, message_id="m1", thread_id="shared-thread", recipient="a@x.com", subject="first", sent_at=now - timedelta(days=2))
    await record_sent_message(pool, user_id=user_id, message_id="m2", thread_id="shared-thread", recipient="a@x.com", subject="follow-up", sent_at=now - timedelta(days=1))

    updated_count = await mark_thread_replied(pool, user_id=user_id, thread_id="shared-thread", replied_at=now)

    assert updated_count == 2
    remaining = await fetch_unreplied_sent_messages(pool, user_id=user_id)
    assert remaining == []


async def test_mark_thread_replied_never_touches_a_different_real_thread(pool, user_id):
    now = datetime.now(timezone.utc)
    await record_sent_message(pool, user_id=user_id, message_id="m1", thread_id="thread-a", recipient="a@x.com", subject="a", sent_at=now)
    await record_sent_message(pool, user_id=user_id, message_id="m2", thread_id="thread-b", recipient="b@x.com", subject="b", sent_at=now)

    await mark_thread_replied(pool, user_id=user_id, thread_id="thread-a", replied_at=now)

    remaining = await fetch_unreplied_sent_messages(pool, user_id=user_id)
    assert [m.subject for m in remaining] == ["b"]


async def test_mark_thread_replied_returns_zero_for_a_thread_with_no_real_unreplied_messages(pool, user_id):
    assert await mark_thread_replied(pool, user_id=user_id, thread_id="never-existed", replied_at=datetime.now(timezone.utc)) == 0


async def test_mark_thread_replied_never_touches_a_different_real_users_thread(pool, user_id):
    other_google_sub = f"test-waiting-on-bystander-{uuid.uuid4()}"
    other_user_id = await get_or_create_user(pool, google_sub=other_google_sub, email=None)
    now = datetime.now(timezone.utc)
    try:
        await record_sent_message(pool, user_id=user_id, message_id="m1", thread_id="shared-thread-id", recipient="a@x.com", subject="mine", sent_at=now)
        await record_sent_message(pool, user_id=other_user_id, message_id="m2", thread_id="shared-thread-id", recipient="b@x.com", subject="bystanders", sent_at=now)

        await mark_thread_replied(pool, user_id=user_id, thread_id="shared-thread-id", replied_at=now)

        mine_remaining = await fetch_unreplied_sent_messages(pool, user_id=user_id)
        bystander_remaining = await fetch_unreplied_sent_messages(pool, user_id=other_user_id)
        assert mine_remaining == []
        assert [m.subject for m in bystander_remaining] == ["bystanders"]
    finally:
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(other_user_id))


async def test_fetch_stale_waiting_on_composes_the_real_query_and_the_real_pure_filter(pool, user_id):
    now = datetime.now(timezone.utc)
    await record_sent_message(pool, user_id=user_id, message_id="stale", thread_id="t1", recipient="a@x.com", subject="stale one", sent_at=now - timedelta(days=10))
    await record_sent_message(pool, user_id=user_id, message_id="fresh", thread_id="t2", recipient="b@x.com", subject="fresh one", sent_at=now - timedelta(hours=1))

    stale = await fetch_stale_waiting_on(pool, user_id=user_id, now=now)

    assert [m.subject for m in stale] == ["stale one"]
