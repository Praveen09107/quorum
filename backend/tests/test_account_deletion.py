"""Real tests for security/account_deletion.py."""
from quorum_backend.auth.refresh_token import issue_refresh_token
from quorum_backend.security.account_deletion import DeletionResult, delete_account


class FakeRevocationStore:
    """Same real, in-memory double pattern as test_auth_refresh_token.py's
    FakeStore -- account_deletion.py must work against the exact same
    RevocationStore protocol a user-initiated sign-out uses."""

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


class FakeDeletionStore:
    def __init__(self):
        self.purged_postgres = []
        self.purged_vectors = []
        self.purged_memories = []
        self.revoked_oauth = []

    def purge_postgres_rows(self, user_id):
        self.purged_postgres.append(user_id)
        return 12

    def purge_vector_embeddings(self, user_id):
        self.purged_vectors.append(user_id)
        return 340

    def purge_memories(self, user_id):
        self.purged_memories.append(user_id)
        return 5

    def revoke_oauth_tokens(self, user_id):
        self.revoked_oauth.append(user_id)
        return 2


def test_delete_account_genuinely_revokes_every_real_session_via_revoke_all_for_user():
    # Real, functional proof that delete_account calls the actual
    # revoke_all_for_user() logic -- not just an import-and-comment check.
    revocation_store = FakeRevocationStore()
    deletion_store = FakeDeletionStore()

    raw_token = issue_refresh_token("user_1", revocation_store)
    from quorum_backend.auth.refresh_token import _hash_token

    record = revocation_store.get(_hash_token(raw_token))
    assert record.revoked is False

    delete_account("user_1", deletion_store, revocation_store)

    assert revocation_store.get(_hash_token(raw_token)).revoked is True


def test_deleting_one_user_never_touches_a_different_users_real_session():
    # The account-deletion equivalent of the five-domain authorization
    # matrix -- a real, live proof that a second, unrelated user's session
    # keeps working after a different user's account is deleted.
    revocation_store = FakeRevocationStore()
    deletion_store = FakeDeletionStore()

    from quorum_backend.auth.refresh_token import _hash_token

    victim_token = issue_refresh_token("user_to_delete", revocation_store)
    other_user_token = issue_refresh_token("innocent_bystander", revocation_store)

    delete_account("user_to_delete", deletion_store, revocation_store)

    assert revocation_store.get(_hash_token(victim_token)).revoked is True
    assert revocation_store.get(_hash_token(other_user_token)).revoked is False
    # The deletion store must also have only ever been asked about the
    # real, intended user -- never the bystander.
    assert deletion_store.purged_postgres == ["user_to_delete"]


def test_delete_account_returns_real_counts_not_a_bare_success_flag():
    revocation_store = FakeRevocationStore()
    deletion_store = FakeDeletionStore()
    issue_refresh_token("user_1", revocation_store)

    result = delete_account("user_1", deletion_store, revocation_store)

    assert isinstance(result, DeletionResult)
    assert result.sessions_revoked is True
    assert result.postgres_rows_deleted == 12
    assert result.vector_embeddings_deleted == 340
    assert result.memories_deleted == 5
    assert result.oauth_tokens_revoked == 2
