"""Real tests for auth/refresh_token.py -- CRITICAL TIER.

Batch 10 Phase 3: ported to async (the module itself is now async -- see
its own top-of-file docstring for why), every existing test's real
behavior preserved exactly, plus one genuinely new test proving the
real, atomic `try_claim()` race-safety guarantee this session added.
"""
import asyncio

import pytest

from quorum_backend.auth.refresh_token import (
    TokenExpired,
    TokenInvalid,
    TokenRevoked,
    TokenReuseDetected,
    issue_refresh_token,
    revoke_all_for_user,
    rotate_refresh_token,
)


class FakeStore:
    """In-memory, real `try_claim()` semantics preserved exactly: an
    atomic check-and-set within a single Python statement -- no `await`
    between the check and the set, so no other task can interleave
    inside this method. The concrete, real Supabase-backed store
    (`auth/revocation_store.py`) must guarantee the same atomicity at
    the database level, since two separate real Cloud Run instances
    share no Python-level state at all.

    `_race_barrier`, when set, forces every `get()` call to block until
    exactly two callers have reached it -- used by the one test below
    that needs a genuine, deterministic race (not an accidental one that
    depends on asyncio's internal scheduling order)."""

    def __init__(self):
        self.records = {}
        self._race_barrier: asyncio.Barrier | None = None

    async def get(self, token_hash):
        if self._race_barrier is not None:
            await self._race_barrier.wait()
        return self.records.get(token_hash)

    async def save(self, record):
        self.records[record.token_hash] = record

    async def try_claim(self, token_hash):
        record = self.records.get(token_hash)
        if record is None or record.used:
            return False
        record.used = True
        return True

    async def revoke_family(self, family_id):
        for r in self.records.values():
            if r.family_id == family_id:
                r.revoked = True

    async def get_family_ids_for_user(self, user_id):
        return {r.family_id for r in self.records.values() if r.user_id == user_id}


async def test_issue_and_rotate_succeeds_for_legitimate_use():
    store = FakeStore()
    raw1 = await issue_refresh_token("user_123", store)
    raw2 = await rotate_refresh_token(raw1, store)
    assert raw2 != raw1


async def test_rotation_preserves_the_same_family_id():
    store = FakeStore()
    raw1 = await issue_refresh_token("user_123", store)
    from quorum_backend.auth.refresh_token import hash_token

    original_family = (await store.get(hash_token(raw1))).family_id
    raw2 = await rotate_refresh_token(raw1, store)
    new_family = (await store.get(hash_token(raw2))).family_id
    assert new_family == original_family


async def test_reuse_detection_revokes_the_whole_family_not_just_one_token():
    # THE real, most important check in this batch -- a genuine token-
    # theft scenario, end to end, both halves proven.
    store = FakeStore()
    raw1 = await issue_refresh_token("user_123", store)
    raw2 = await rotate_refresh_token(raw1, store)  # legitimate client rotates

    with pytest.raises(TokenReuseDetected):
        await rotate_refresh_token(raw1, store)  # attacker replays the stolen, now-stale token

    # The legitimate client's own CURRENT token must also stop working --
    # proof the whole family was revoked, not just the reused one.
    with pytest.raises(TokenRevoked):
        await rotate_refresh_token(raw2, store)


async def test_unknown_token_raises_token_invalid():
    store = FakeStore()
    with pytest.raises(TokenInvalid):
        await rotate_refresh_token("a-token-that-was-never-issued", store)


async def test_expired_token_raises_token_expired():
    from datetime import datetime, timedelta, timezone

    from quorum_backend.auth.refresh_token import RefreshTokenRecord, hash_token

    store = FakeStore()
    raw = "a-real-raw-token-value"
    now = datetime.now(timezone.utc)
    await store.save(
        RefreshTokenRecord(
            token_hash=hash_token(raw),
            family_id="fam1",
            user_id="user_123",
            issued_at=now - timedelta(days=10),
            expires_at=now - timedelta(days=3),  # already expired
        )
    )
    with pytest.raises(TokenExpired):
        await rotate_refresh_token(raw, store)


async def test_revoked_family_raises_token_revoked_on_any_member():
    store = FakeStore()
    raw1 = await issue_refresh_token("user_123", store)
    from quorum_backend.auth.refresh_token import hash_token

    family_id = (await store.get(hash_token(raw1))).family_id
    await store.revoke_family(family_id)
    with pytest.raises(TokenRevoked):
        await rotate_refresh_token(raw1, store)


async def test_sign_out_everywhere_revokes_every_family_for_the_user_only():
    store = FakeStore()
    user_a_raw = await issue_refresh_token("user_a", store)
    user_b_raw = await issue_refresh_token("user_b", store)

    await revoke_all_for_user("user_a", store)

    with pytest.raises(TokenRevoked):
        await rotate_refresh_token(user_a_raw, store)

    # A different user's real session must be completely unaffected.
    new_raw = await rotate_refresh_token(user_b_raw, store)
    assert new_raw is not None


async def test_concurrent_reuse_of_the_same_token_is_caught_by_try_claim_not_lost_to_the_race():
    # THE real, new property this session's try_claim() exists to
    # guarantee: two callers racing to rotate the SAME token concurrently
    # must not both succeed -- exactly one wins, the other gets a real
    # TokenReuseDetected, and the whole family ends up revoked either way.
    #
    # store._race_barrier forces BOTH calls' get() to complete (both see
    # used=False) before EITHER can proceed to try_claim() -- a genuine,
    # deterministic race at exactly the point try_claim() exists to
    # guard, not an accident of asyncio's internal scheduling order. This
    # is the one scenario the OLD (pre-try_claim) design would have
    # failed: both callers would have seen used=False and both would
    # have "succeeded," silently defeating theft detection.
    store = FakeStore()
    raw1 = await issue_refresh_token("user_123", store)
    store._race_barrier = asyncio.Barrier(2)

    results = await asyncio.gather(
        rotate_refresh_token(raw1, store),
        rotate_refresh_token(raw1, store),
        return_exceptions=True,
    )

    successes = [r for r in results if isinstance(r, str)]
    failures = [r for r in results if isinstance(r, BaseException)]

    assert len(successes) == 1, "exactly one of two genuinely concurrent racers must win the atomic claim"
    assert len(failures) == 1
    assert isinstance(failures[0], TokenReuseDetected)
