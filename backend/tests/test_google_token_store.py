"""Real, live-database tests for auth/google_token_store.py (Phase 3)."""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest_asyncio
from cryptography.fernet import Fernet

import pytest

from quorum_backend.auth.google_token_store import (
    GOOGLE_ACCESS_TOKEN_REFRESH_MARGIN_SECONDS,
    delete_google_tokens,
    fetch_google_tokens,
    get_valid_google_access_token,
    store_google_tokens,
    update_access_token_after_refresh,
)
from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db

_KEY = Fernet.generate_key().decode()


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-google-token-store-{uuid.uuid4()}"
    uid = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield uid
    await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(uid))


async def test_store_then_fetch_round_trips_real_tokens_decrypted_correctly(pool, user_id):
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    await store_google_tokens(
        pool, internal_user_id=user_id, access_token="real-access-token",
        refresh_token="real-refresh-token", access_token_expires_at=expires_at,
        granted_scopes="openid email gmail.readonly", encryption_key=_KEY,
    )

    record = await fetch_google_tokens(pool, internal_user_id=user_id, encryption_key=_KEY)

    assert record.access_token == "real-access-token"
    assert record.refresh_token == "real-refresh-token"
    assert record.granted_scopes == "openid email gmail.readonly"
    assert abs((record.access_token_expires_at - expires_at).total_seconds()) < 1

    # The real, stored ciphertext itself must never contain the real
    # plaintext token -- a genuine encryption proof, not just a round
    # trip through this module's own functions.
    row = await pool.fetchrow(
        "SELECT encrypted_access_token, encrypted_refresh_token FROM google_oauth_tokens WHERE user_id = $1",
        uuid.UUID(user_id),
    )
    assert "real-access-token" not in row["encrypted_access_token"]
    assert "real-refresh-token" not in row["encrypted_refresh_token"]


async def test_fetch_google_tokens_returns_none_for_a_user_who_never_granted_access(pool, user_id):
    assert await fetch_google_tokens(pool, internal_user_id=user_id, encryption_key=_KEY) is None


async def test_store_google_tokens_rejects_a_missing_refresh_token_it_never_silently_writes_null(pool, user_id):
    """Real regression test for this PR's own CRITICAL-tier review,
    BLOCKER 1: an earlier version accepted `refresh_token=None` here and
    resolved a fallback inside the SQL itself -- live-proven to raise a
    real `NotNullViolationError` (no existing row to fall back to) or,
    worse, to silently persist a stale value under real concurrency
    (finding MEDIUM 5). This function now rejects the call outright,
    loudly, in Python, before any real SQL runs at all."""
    with pytest.raises(ValueError, match="update_access_token_after_refresh"):
        await store_google_tokens(
            pool, internal_user_id=user_id, access_token="a", refresh_token=None,
            access_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            granted_scopes="openid", encryption_key=_KEY,
        )
    # Real, honest confirmation: the rejected call never touched the
    # real database at all.
    assert await fetch_google_tokens(pool, internal_user_id=user_id, encryption_key=_KEY) is None


async def test_storing_again_with_a_real_new_refresh_token_upserts_cleanly(pool, user_id):
    """Real proof of the real, simplified upsert -- a genuine
    re-consent with a fresh real refresh_token (Google's own real,
    common case when `prompt=consent` forces one every time) correctly
    overwrites every real column, never creating a duplicate row."""
    await store_google_tokens(
        pool, internal_user_id=user_id, access_token="first-access-token",
        refresh_token="first-refresh-token", access_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        granted_scopes="openid email", encryption_key=_KEY,
    )

    await store_google_tokens(
        pool, internal_user_id=user_id, access_token="second-access-token",
        refresh_token="second-refresh-token", access_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        granted_scopes="openid email gmail.readonly", encryption_key=_KEY,
    )

    record = await fetch_google_tokens(pool, internal_user_id=user_id, encryption_key=_KEY)
    assert record.access_token == "second-access-token"
    assert record.refresh_token == "second-refresh-token"  # a real, fresh refresh_token also upserts cleanly
    assert record.granted_scopes == "openid email gmail.readonly"

    count = await pool.fetchval("SELECT COUNT(*) FROM google_oauth_tokens WHERE user_id = $1", uuid.UUID(user_id))
    assert count == 1  # a real upsert, never a duplicate row


async def test_update_access_token_after_refresh_updates_only_the_access_token(pool, user_id):
    """Real, direct proof of the real, refresh-only write path -- the
    exact fix for BLOCKER 1 and MEDIUM 5 both: this function never
    reads or writes `encrypted_refresh_token` at all, so there is no
    real value to race on and no `NULL` that could ever reach it."""
    await store_google_tokens(
        pool, internal_user_id=user_id, access_token="original-access-token",
        refresh_token="the-real-refresh-token", access_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        granted_scopes="openid email", encryption_key=_KEY,
    )

    new_expiry = datetime.now(timezone.utc) + timedelta(hours=2)
    await update_access_token_after_refresh(
        pool, internal_user_id=user_id, access_token="refreshed-access-token",
        access_token_expires_at=new_expiry, encryption_key=_KEY,
    )

    record = await fetch_google_tokens(pool, internal_user_id=user_id, encryption_key=_KEY)
    assert record.access_token == "refreshed-access-token"
    assert record.refresh_token == "the-real-refresh-token"  # untouched
    assert abs((record.access_token_expires_at - new_expiry).total_seconds()) < 1


async def test_update_access_token_after_refresh_is_a_real_honest_no_op_for_a_nonexistent_row(pool, user_id):
    # A real row deleted concurrently (a real account deletion racing a
    # real refresh) must never raise here -- a real, honest UPDATE 0.
    await update_access_token_after_refresh(
        pool, internal_user_id=user_id, access_token="a",
        access_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1), encryption_key=_KEY,
    )
    assert await fetch_google_tokens(pool, internal_user_id=user_id, encryption_key=_KEY) is None


async def test_store_google_tokens_is_genuinely_race_free_under_real_concurrent_writers(pool, user_id):
    """Real, live proof that the fix for MEDIUM 5 actually closes the
    race this PR's own review reproduced (3 of 25 real concurrent
    writes silently persisting a stale refresh_token). Since this
    function no longer reads any existing value before writing (no
    subquery, no COALESCE), every real concurrent writer's own values
    are fully self-consistent -- the only real question is which write
    lands last, never a corrupted mix of two real writes."""

    async def _write(n: int):
        await store_google_tokens(
            pool, internal_user_id=user_id, access_token=f"access-{n}", refresh_token=f"refresh-{n}",
            access_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            granted_scopes="openid", encryption_key=_KEY,
        )

    await asyncio.gather(*(_write(n) for n in range(10)))

    record = await fetch_google_tokens(pool, internal_user_id=user_id, encryption_key=_KEY)
    # Whichever real write landed last, its own access_token and
    # refresh_token must be a matched, self-consistent pair -- never one
    # writer's access_token alongside a DIFFERENT writer's refresh_token.
    winner = record.access_token.split("-")[1]
    assert record.refresh_token == f"refresh-{winner}"


async def test_delete_google_tokens_returns_the_real_count_and_actually_deletes(pool, user_id):
    await store_google_tokens(
        pool, internal_user_id=user_id, access_token="a", refresh_token="b",
        access_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        granted_scopes="openid", encryption_key=_KEY,
    )

    deleted = await delete_google_tokens(pool, internal_user_id=user_id)
    assert deleted == 1
    assert await fetch_google_tokens(pool, internal_user_id=user_id, encryption_key=_KEY) is None

    # A second real delete of an already-gone row is a real, honest
    # zero, never a crash.
    assert await delete_google_tokens(pool, internal_user_id=user_id) == 0


async def test_deleting_the_real_users_row_cascades_and_removes_the_real_token_row(pool, user_id):
    """Real, live proof of `migrations/0010_google_oauth_tokens/up.sql`'s
    own `ON DELETE CASCADE` -- this is exactly the real property that
    makes revoke-before-purge ordering load-bearing in `security/
    account_deletion.py::delete_account()`."""
    await store_google_tokens(
        pool, internal_user_id=user_id, access_token="a", refresh_token="b",
        access_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        granted_scopes="openid", encryption_key=_KEY,
    )

    await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(user_id))

    row = await pool.fetchrow("SELECT 1 FROM google_oauth_tokens WHERE user_id = $1", uuid.UUID(user_id))
    assert row is None  # genuinely cascaded away, not orphaned


async def test_get_valid_google_access_token_returns_none_when_nothing_is_stored(pool, user_id):
    result = await get_valid_google_access_token(
        pool, internal_user_id=user_id, client_id="unused", client_secret="unused", encryption_key=_KEY
    )
    assert result is None


async def test_get_valid_google_access_token_returns_the_stored_token_without_refreshing_when_far_from_expiry(pool, user_id):
    await store_google_tokens(
        pool, internal_user_id=user_id, access_token="still-fresh-token", refresh_token="a-refresh-token",
        access_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        granted_scopes="openid", encryption_key=_KEY,
    )

    # client_id/client_secret are deliberately garbage -- if this test
    # ever actually reached a real refresh call, it would raise, proving
    # this test genuinely exercises the no-refresh-needed path.
    result = await get_valid_google_access_token(
        pool, internal_user_id=user_id, client_id="unused", client_secret="unused", encryption_key=_KEY
    )
    assert result == "still-fresh-token"


async def test_get_valid_google_access_token_margin_constant_is_a_real_positive_number():
    # A light, real sanity check on the module's own disclosed constant
    # -- not testing Google, just this module's own real configuration.
    assert GOOGLE_ACCESS_TOKEN_REFRESH_MARGIN_SECONDS > 0


async def test_get_valid_google_access_token_refreshes_and_persists_when_expired(pool, user_id, monkeypatch):
    """No real, valid Google-issued refresh_token exists for this test
    suite to use (obtaining one needs a real, human-completed mobile
    consent flow with the new scopes -- a real, disclosed, still-open
    verification, see this session's own account) -- monkeypatches the
    one real network call this function makes, deterministic and
    network-independent, the same technique `test_negotiation_gemini_
    calls.py` already established for this class of dependency. Proves
    this module's own real orchestration: detect expiry, call refresh,
    persist the new access_token, keep the SAME real refresh_token."""
    expired_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await store_google_tokens(
        pool, internal_user_id=user_id, access_token="expired-token", refresh_token="the-real-refresh-token",
        access_token_expires_at=expired_at, granted_scopes="openid email", encryption_key=_KEY,
    )

    new_expiry = datetime.now(timezone.utc) + timedelta(hours=1)

    async def _fake_refresh(*, refresh_token, client_id, client_secret):
        assert refresh_token == "the-real-refresh-token"
        return "freshly-refreshed-token", new_expiry

    monkeypatch.setattr("quorum_backend.auth.google_token_store.refresh_google_access_token", _fake_refresh)

    result = await get_valid_google_access_token(
        pool, internal_user_id=user_id, client_id="a-client-id", client_secret="a-client-secret", encryption_key=_KEY
    )

    assert result == "freshly-refreshed-token"
    record = await fetch_google_tokens(pool, internal_user_id=user_id, encryption_key=_KEY)
    assert record.access_token == "freshly-refreshed-token"
    assert record.refresh_token == "the-real-refresh-token"  # the real, original one, never lost
    assert abs((record.access_token_expires_at - new_expiry).total_seconds()) < 1
