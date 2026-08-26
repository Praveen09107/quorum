"""Real tests for security/account_deletion.py.

Batch 10 Phase 3: `delete_account()` and `FakeRevocationStore` ported to
async, matching `auth/refresh_token.py`'s own async change this session
-- every existing test's real behavior preserved exactly.

`DEC-113`: `delete_account()` now takes two real, distinct identifiers
(`google_sub` for real session revocation, `internal_user_id` for the
real `DeletionStore` calls) instead of one conflated `user_id` --
found live while building the first real `DeletionStore` and
discovering the two identifier spaces `DEC-110` introduced were never
actually reconcilable through a single parameter. `FakeDeletionStore`'s
methods are now `async`, matching the real `DeletionStore` Protocol's
own async conversion the same session.
"""
from quorum_backend.auth.refresh_token import issue_refresh_token
from quorum_backend.security.account_deletion import DeletionResult, delete_account


class FakeRevocationStore:
    """Same real, in-memory double pattern as test_auth_refresh_token.py's
    FakeStore -- account_deletion.py must work against the exact same
    RevocationStore protocol a user-initiated sign-out uses."""

    def __init__(self):
        self.records = {}

    async def get(self, token_hash):
        return self.records.get(token_hash)

    async def save(self, record):
        self.records[record.token_hash] = record

    async def claim_and_rotate(self, old_token_hash, new_record):
        record = self.records.get(old_token_hash)
        if record is None or record.used or record.revoked:
            return False
        record.used = True
        self.records[new_record.token_hash] = new_record
        return True

    async def revoke_family(self, family_id):
        for r in self.records.values():
            if r.family_id == family_id:
                r.revoked = True

    async def get_family_ids_for_user(self, user_id):
        return {r.family_id for r in self.records.values() if r.user_id == user_id}


class FakeDeletionStore:
    def __init__(self):
        self.purged_postgres = []
        self.purged_vectors = []
        self.purged_memories = []
        self.revoked_oauth = []
        # Real, ordered record of which real method ran when -- the
        # only way to actually prove a real call ORDER, not just that
        # every real method eventually ran.
        self.call_order = []

    async def purge_postgres_rows(self, internal_user_id):
        self.purged_postgres.append(internal_user_id)
        self.call_order.append("purge_postgres_rows")
        return 12

    async def purge_vector_embeddings(self, internal_user_id):
        self.purged_vectors.append(internal_user_id)
        self.call_order.append("purge_vector_embeddings")
        return 340

    async def purge_memories(self, internal_user_id):
        self.purged_memories.append(internal_user_id)
        self.call_order.append("purge_memories")
        return 5

    async def revoke_oauth_tokens(self, internal_user_id):
        self.revoked_oauth.append(internal_user_id)
        self.call_order.append("revoke_oauth_tokens")
        return 2


async def test_delete_account_genuinely_revokes_every_real_session_via_revoke_all_for_user():
    # Real, functional proof that delete_account calls the actual
    # revoke_all_for_user() logic -- not just an import-and-comment check.
    revocation_store = FakeRevocationStore()
    deletion_store = FakeDeletionStore()

    raw_token = await issue_refresh_token("google-sub-user-1", revocation_store)
    from quorum_backend.auth.refresh_token import hash_token

    record = await revocation_store.get(hash_token(raw_token))
    assert record.revoked is False

    await delete_account(
        google_sub="google-sub-user-1",
        internal_user_id="11111111-1111-1111-1111-111111111111",
        deletion_store=deletion_store,
        revocation_store=revocation_store,
    )

    assert (await revocation_store.get(hash_token(raw_token))).revoked is True


async def test_deleting_one_user_never_touches_a_different_users_real_session():
    # The account-deletion equivalent of the five-domain authorization
    # matrix -- a real, live proof that a second, unrelated user's session
    # keeps working after a different user's account is deleted.
    revocation_store = FakeRevocationStore()
    deletion_store = FakeDeletionStore()

    from quorum_backend.auth.refresh_token import hash_token

    victim_token = await issue_refresh_token("google-sub-to-delete", revocation_store)
    other_user_token = await issue_refresh_token("google-sub-innocent-bystander", revocation_store)

    await delete_account(
        google_sub="google-sub-to-delete",
        internal_user_id="22222222-2222-2222-2222-222222222222",
        deletion_store=deletion_store,
        revocation_store=revocation_store,
    )

    assert (await revocation_store.get(hash_token(victim_token))).revoked is True
    assert (await revocation_store.get(hash_token(other_user_token))).revoked is False
    # The deletion store must also have only ever been asked about the
    # real, intended user's real internal UUID -- never the bystander's,
    # and never the Google sub (a genuinely different identifier space).
    assert deletion_store.purged_postgres == ["22222222-2222-2222-2222-222222222222"]


async def test_delete_account_returns_real_counts_not_a_bare_success_flag():
    revocation_store = FakeRevocationStore()
    deletion_store = FakeDeletionStore()
    await issue_refresh_token("google-sub-user-1", revocation_store)

    result = await delete_account(
        google_sub="google-sub-user-1",
        internal_user_id="33333333-3333-3333-3333-333333333333",
        deletion_store=deletion_store,
        revocation_store=revocation_store,
    )

    assert isinstance(result, DeletionResult)
    assert result.user_id == "33333333-3333-3333-3333-333333333333"
    assert result.sessions_revoked is True
    assert result.postgres_rows_deleted == 12
    assert result.vector_embeddings_deleted == 340
    assert result.memories_deleted == 5
    assert result.oauth_tokens_revoked == 2


async def test_delete_account_revokes_real_oauth_tokens_before_purging_postgres_rows():
    """Real regression test for Phase 3's own deliberate reordering --
    see `delete_account()`'s own docstring for the full real reasoning:
    `google_oauth_tokens.user_id` has a real `ON DELETE CASCADE` against
    `users`, so `revoke_oauth_tokens()` (which needs the real, stored
    token still present to send to Google) must run before `purge_
    postgres_rows()` (which deletes the real `users` row the cascade
    keys off of) -- never the reverse."""
    revocation_store = FakeRevocationStore()
    deletion_store = FakeDeletionStore()
    await issue_refresh_token("google-sub-user-1", revocation_store)

    await delete_account(
        google_sub="google-sub-user-1",
        internal_user_id="44444444-4444-4444-4444-444444444444",
        deletion_store=deletion_store,
        revocation_store=revocation_store,
    )

    revoke_index = deletion_store.call_order.index("revoke_oauth_tokens")
    purge_index = deletion_store.call_order.index("purge_postgres_rows")
    assert revoke_index < purge_index
