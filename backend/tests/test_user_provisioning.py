"""Real tests for auth/user_provisioning.py -- against the real, live
Supabase database (`DEC-098`), mirroring `test_trust_digest.py`'s
established pattern. Every inserted row uses a real, deliberately
obscure, UUID-namespaced `google_sub` value and is deleted by that
same value in a `finally` block -- these tests can never collide with
a real person's account and never leave anything behind.
"""
import asyncio
import uuid

import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user, resolve_internal_user_id
from quorum_backend.core import db


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


def _real_test_sub() -> str:
    return f"real-test-google-sub-{uuid.uuid4()}"


async def test_a_new_google_sub_gets_a_real_new_uuid(pool):
    google_sub = _real_test_sub()
    try:
        user_id = await get_or_create_user(pool, google_sub=google_sub, email="test@example.com")
        assert user_id  # a real, non-empty UUID string
        uuid.UUID(user_id)  # a real, valid UUID -- raises ValueError otherwise
    finally:
        await pool.execute("DELETE FROM users WHERE google_sub = $1", google_sub)


async def test_the_same_google_sub_always_resolves_to_the_same_real_uuid(pool):
    google_sub = _real_test_sub()
    try:
        first = await get_or_create_user(pool, google_sub=google_sub, email="a@example.com")
        second = await get_or_create_user(pool, google_sub=google_sub, email="a@example.com")
        assert first == second
    finally:
        await pool.execute("DELETE FROM users WHERE google_sub = $1", google_sub)


async def test_a_second_real_call_refreshes_the_stored_email_not_a_stale_one(pool):
    google_sub = _real_test_sub()
    try:
        await get_or_create_user(pool, google_sub=google_sub, email="old@example.com")
        await get_or_create_user(pool, google_sub=google_sub, email="new@example.com")

        row = await pool.fetchrow("SELECT email FROM users WHERE google_sub = $1", google_sub)
        assert row["email"] == "new@example.com"
    finally:
        await pool.execute("DELETE FROM users WHERE google_sub = $1", google_sub)


async def test_a_real_null_email_is_honestly_stored_as_null_not_a_placeholder(pool):
    google_sub = _real_test_sub()
    try:
        user_id = await get_or_create_user(pool, google_sub=google_sub, email=None)
        row = await pool.fetchrow("SELECT email FROM users WHERE user_id = $1", uuid.UUID(user_id))
        assert row["email"] is None
    finally:
        await pool.execute("DELETE FROM users WHERE google_sub = $1", google_sub)


async def test_two_distinct_google_subs_get_two_distinct_real_uuids(pool):
    sub_a, sub_b = _real_test_sub(), _real_test_sub()
    try:
        user_id_a = await get_or_create_user(pool, google_sub=sub_a, email=None)
        user_id_b = await get_or_create_user(pool, google_sub=sub_b, email=None)
        assert user_id_a != user_id_b
    finally:
        await pool.execute("DELETE FROM users WHERE google_sub = ANY($1::text[])", [sub_a, sub_b])


async def test_resolve_internal_user_id_finds_a_real_already_provisioned_identity(pool):
    google_sub = _real_test_sub()
    try:
        created = await get_or_create_user(pool, google_sub=google_sub, email=None)
        resolved = await resolve_internal_user_id(pool, google_sub=google_sub)
        assert resolved == created
    finally:
        await pool.execute("DELETE FROM users WHERE google_sub = $1", google_sub)


async def test_resolve_internal_user_id_returns_a_real_honest_none_for_an_unprovisioned_identity(pool):
    # A real, deliberately never-inserted google_sub -- never provisioned,
    # so the real, honest answer is None, never a fabricated UUID.
    resolved = await resolve_internal_user_id(pool, google_sub=_real_test_sub())
    assert resolved is None


async def test_concurrent_first_sign_ins_for_the_same_real_identity_never_create_two_uuids(pool):
    # The real, load-bearing race the ON CONFLICT upsert exists to
    # close -- two near-simultaneous first sign-ins for the same real
    # person (e.g. two devices, or a real double-tap) must resolve to
    # exactly one real internal UUID, never two.
    google_sub = _real_test_sub()
    try:
        results = await asyncio.gather(
            *[get_or_create_user(pool, google_sub=google_sub, email=None) for _ in range(10)]
        )
        assert len(set(results)) == 1

        rows = await pool.fetch("SELECT user_id FROM users WHERE google_sub = $1", google_sub)
        assert len(rows) == 1
    finally:
        await pool.execute("DELETE FROM users WHERE google_sub = $1", google_sub)
