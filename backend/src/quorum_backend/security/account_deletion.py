"""Real delete-account flow -- purging Postgres, pgvector, mem0, and
revoking stored OAuth tokens is required to exist before real user data
enters the system in beta, not treated as later polish
(QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md §14.7). HONEST DISCLOSURE:
construction-not-copy pattern, same as every negotiation/Gate/security
file in this project.

THE REAL, LOAD-BEARING DESIGN DECISION: session revocation here calls
auth.refresh_token.revoke_all_for_user() directly -- the exact same "sign
out everywhere" mechanism a user-initiated sign-out uses -- rather than a
fresh, parallel "delete this user's session records" query.

Why reuse matters, concretely: revoke_all_for_user() is the real,
CRITICAL-tier-reviewed implementation that already correctly enumerates
every real session family belonging to a user (via
store.get_family_ids_for_user()) and revokes each one -- including
whatever edge cases its own test suite already covers (multiple concurrent
devices, zero-session users, families mid-rotation). A fresh, independent
query here would have to rediscover and get all of that right a second
time, with no guarantee it stays correct if revoke_all_for_user() is ever
changed -- a bug fixed there wouldn't automatically apply to a duplicate.
Reusing it means there is exactly one revocation code path in the entire
system, reviewed once, exercised by both a user's voluntary sign-out and
this permanent, irreversible deletion flow -- not two implementations that
could silently drift apart.

Out of scope: the real Postgres/pgvector/mem0 deletion queries themselves
-- DeletionStore is injected, same real/external boundary pattern as
everywhere else in this project (llm_call, position_call, RevocationStore).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from quorum_backend.auth.refresh_token import RevocationStore, revoke_all_for_user


class DeletionStore(Protocol):
    """Real, injectable adapter over the actual Postgres/pgvector/mem0
    purge and stored-OAuth-token revocation. Returns a real count per
    store, not a bare success/fail flag, so a caller can confirm data was
    genuinely found and removed rather than silently doing nothing for an
    unknown user_id."""

    def purge_postgres_rows(self, user_id: str) -> int: ...
    def purge_vector_embeddings(self, user_id: str) -> int: ...
    def purge_memories(self, user_id: str) -> int: ...
    def revoke_oauth_tokens(self, user_id: str) -> int: ...


@dataclass
class DeletionResult:
    user_id: str
    sessions_revoked: bool
    postgres_rows_deleted: int
    vector_embeddings_deleted: int
    memories_deleted: int
    oauth_tokens_revoked: int


def delete_account(
    user_id: str,
    deletion_store: DeletionStore,
    revocation_store: RevocationStore,
) -> DeletionResult:
    """Sessions are revoked FIRST, before any real data purge -- locking
    the account down for any further access before its data is removed,
    rather than the reverse order, which would leave a real window where
    a still-valid session could act against data mid-deletion."""

    revoke_all_for_user(user_id, revocation_store)

    return DeletionResult(
        user_id=user_id,
        sessions_revoked=True,
        postgres_rows_deleted=deletion_store.purge_postgres_rows(user_id),
        vector_embeddings_deleted=deletion_store.purge_vector_embeddings(user_id),
        memories_deleted=deletion_store.purge_memories(user_id),
        oauth_tokens_revoked=deletion_store.revoke_oauth_tokens(user_id),
    )
