"""Real tests for auth/refresh_token.py -- CRITICAL TIER."""
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
    def __init__(self):
        self.records = {}

    def get(self, token_hash):
        return self.records.get(token_hash)

    def save(self, record):
        self.records[record.token_hash] = record

    def revoke_family(self, family_id):
        for r in self.records.values():
            if r.family_id == family_id:
                r.revoked = True

    def get_family_ids_for_user(self, user_id):
        return {r.family_id for r in self.records.values() if r.user_id == user_id}


def test_issue_and_rotate_succeeds_for_legitimate_use():
    store = FakeStore()
    raw1 = issue_refresh_token("user_123", store)
    raw2 = rotate_refresh_token(raw1, store)
    assert raw2 != raw1


def test_rotation_preserves_the_same_family_id():
    store = FakeStore()
    raw1 = issue_refresh_token("user_123", store)
    from quorum_backend.auth.refresh_token import _hash_token

    original_family = store.get(_hash_token(raw1)).family_id
    raw2 = rotate_refresh_token(raw1, store)
    new_family = store.get(_hash_token(raw2)).family_id
    assert new_family == original_family


def test_reuse_detection_revokes_the_whole_family_not_just_one_token():
    # THE real, most important check in this batch -- a genuine token-
    # theft scenario, end to end, both halves proven.
    store = FakeStore()
    raw1 = issue_refresh_token("user_123", store)
    raw2 = rotate_refresh_token(raw1, store)  # legitimate client rotates

    with pytest.raises(TokenReuseDetected):
        rotate_refresh_token(raw1, store)  # attacker replays the stolen, now-stale token

    # The legitimate client's own CURRENT token must also stop working --
    # proof the whole family was revoked, not just the reused one.
    with pytest.raises(TokenRevoked):
        rotate_refresh_token(raw2, store)


def test_unknown_token_raises_token_invalid():
    store = FakeStore()
    with pytest.raises(TokenInvalid):
        rotate_refresh_token("a-token-that-was-never-issued", store)


def test_expired_token_raises_token_expired():
    from datetime import datetime, timedelta, timezone

    from quorum_backend.auth.refresh_token import RefreshTokenRecord, _hash_token

    store = FakeStore()
    raw = "a-real-raw-token-value"
    now = datetime.now(timezone.utc)
    store.save(
        RefreshTokenRecord(
            token_hash=_hash_token(raw),
            family_id="fam1",
            user_id="user_123",
            issued_at=now - timedelta(days=10),
            expires_at=now - timedelta(days=3),  # already expired
        )
    )
    with pytest.raises(TokenExpired):
        rotate_refresh_token(raw, store)


def test_revoked_family_raises_token_revoked_on_any_member():
    store = FakeStore()
    raw1 = issue_refresh_token("user_123", store)
    from quorum_backend.auth.refresh_token import _hash_token

    family_id = store.get(_hash_token(raw1)).family_id
    store.revoke_family(family_id)
    with pytest.raises(TokenRevoked):
        rotate_refresh_token(raw1, store)


def test_sign_out_everywhere_revokes_every_family_for_the_user_only():
    store = FakeStore()
    user_a_raw = issue_refresh_token("user_a", store)
    user_b_raw = issue_refresh_token("user_b", store)

    revoke_all_for_user("user_a", store)

    with pytest.raises(TokenRevoked):
        rotate_refresh_token(user_a_raw, store)

    # A different user's real session must be completely unaffected.
    new_raw = rotate_refresh_token(user_b_raw, store)
    assert new_raw is not None
