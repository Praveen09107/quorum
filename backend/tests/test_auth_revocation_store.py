"""Real, live tests for auth/revocation_store.py -- CRITICAL TIER, same
as the module it implements. Every test here runs against the real,
live Supabase database (Rule 5: real Postgres, never mocked), using
random UUIDs so nothing can ever collide with real data, with a
`finally` block guaranteeing cleanup even on failure.

The concurrency test is the real point of this file's existence: the
in-memory `FakeStore` in `test_auth_refresh_token.py` proves
`try_claim()`'s CONTRACT is correct; this file proves the real,
concrete Supabase implementation actually delivers the atomicity that
contract promises, under real concurrent access to the real database
-- not just Python-level cooperative scheduling.
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest_asyncio

from quorum_backend.auth.refresh_token import RefreshTokenRecord
from quorum_backend.auth.revocation_store import SupabaseRevocationStore
from quorum_backend.core import db


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
def store(pool):
    return SupabaseRevocationStore(pool)


def _record(token_hash, family_id=None, user_id="test-user", used=False, revoked=False):
    now = datetime.now(timezone.utc)
    return RefreshTokenRecord(
        token_hash=token_hash,
        family_id=family_id or str(uuid.uuid4()),
        user_id=user_id,
        issued_at=now,
        expires_at=now + timedelta(days=7),
        used=used,
        revoked=revoked,
    )


async def test_save_and_get_round_trip_a_real_record(pool, store):
    token_hash = f"test-{uuid.uuid4()}"
    record = _record(token_hash, user_id="round-trip-user")
    try:
        await store.save(record)
        fetched = await store.get(token_hash)

        assert fetched is not None
        assert fetched.token_hash == token_hash
        assert fetched.family_id == record.family_id
        assert fetched.user_id == "round-trip-user"
        assert fetched.used is False
        assert fetched.revoked is False
    finally:
        await pool.execute("DELETE FROM refresh_tokens WHERE token_hash = $1", token_hash)


async def test_get_for_an_unknown_token_returns_none_not_an_error(store):
    result = await store.get(f"never-issued-{uuid.uuid4()}")
    assert result is None


async def test_try_claim_succeeds_once_and_fails_on_the_real_second_attempt(pool, store):
    token_hash = f"test-{uuid.uuid4()}"
    try:
        await store.save(_record(token_hash))

        first = await store.try_claim(token_hash)
        second = await store.try_claim(token_hash)

        assert first is True
        assert second is False
    finally:
        await pool.execute("DELETE FROM refresh_tokens WHERE token_hash = $1", token_hash)


async def test_try_claim_is_atomic_under_real_concurrent_requests_against_the_live_database(pool, store):
    # THE real point of this file. Two genuinely separate coroutines,
    # both racing to claim the SAME real database row via two separate
    # connections drawn from the same real pool -- proving the atomicity
    # try_claim()'s contract promises is real at the database level, not
    # just simulated in-memory (test_auth_refresh_token.py's FakeStore
    # test proves the CONTRACT; this proves the CONCRETE implementation
    # actually honors it against the real, live Supabase database).
    token_hash = f"test-{uuid.uuid4()}"
    try:
        await store.save(_record(token_hash))

        results = await asyncio.gather(
            store.try_claim(token_hash),
            store.try_claim(token_hash),
        )

        assert sorted(results) == [False, True], "exactly one of two real concurrent claims must succeed"
    finally:
        await pool.execute("DELETE FROM refresh_tokens WHERE token_hash = $1", token_hash)


async def test_revoke_family_marks_every_real_member_of_the_family_revoked(pool, store):
    family_id = str(uuid.uuid4())
    token_a = f"test-{uuid.uuid4()}"
    token_b = f"test-{uuid.uuid4()}"
    try:
        await store.save(_record(token_a, family_id=family_id))
        await store.save(_record(token_b, family_id=family_id))

        await store.revoke_family(family_id)

        assert (await store.get(token_a)).revoked is True
        assert (await store.get(token_b)).revoked is True
    finally:
        await pool.execute("DELETE FROM refresh_tokens WHERE token_hash = ANY($1::text[])", [token_a, token_b])


async def test_get_family_ids_for_user_returns_only_that_real_users_families(pool, store):
    user_a = f"test-user-a-{uuid.uuid4()}"
    user_b = f"test-user-b-{uuid.uuid4()}"
    token_a = f"test-{uuid.uuid4()}"
    token_b = f"test-{uuid.uuid4()}"
    record_a = _record(token_a, user_id=user_a)
    record_b = _record(token_b, user_id=user_b)
    try:
        await store.save(record_a)
        await store.save(record_b)

        families = await store.get_family_ids_for_user(user_a)

        assert families == {record_a.family_id}
    finally:
        await pool.execute("DELETE FROM refresh_tokens WHERE token_hash = ANY($1::text[])", [token_a, token_b])
