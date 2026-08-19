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

**RESOLVED, `DEC-113`, CRITICAL tier:** found live while finally building
a real `DeletionStore` -- this module previously took one single `user_id`
string and passed it, unchanged, to both `revoke_all_for_user()` (which
needs the real Google `sub`, confirmed against `refresh_tokens.user_id`'s
real `TEXT` column type) and `deletion_store`'s own methods (which need
the real, internal `UUID` every per-user domain table actually uses,
since `DEC-110`'s real `users` table exists). Passing the same value to
both was silently correct only because no real `DeletionStore`
implementation existed yet to expose the mismatch -- a real Postgres
purge scoped by a Google `sub` string would have failed outright (not a
valid UUID) or, worse, silently matched nothing while claiming success.
Split into two explicit, named parameters below; never conflated again.

**RESOLVED, `DEC-113`:** `DeletionStore`'s own methods are now `async`,
exactly as this module's own prior docstring already anticipated ("when
it is built against the real database, the same async reasoning will
apply to it too") -- `delete_account()` now `await`s each real call, the
same real, disclosed conversion `refresh_token.py`'s own `async` change
already established as this project's precedent for exactly this
situation.

Out of scope: the real Postgres/pgvector/mem0 deletion queries
themselves used to be -- `DeletionStore` is injected, same real/external
boundary pattern as everywhere else in this project (llm_call,
position_call, RevocationStore). As of `DEC-113`, a real, live
implementation exists: `security/supabase_deletion_store.py`.
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
    unknown user_id. Every method takes the real, internal UUID
    (`DEC-110`'s `users` table), never the Google `sub` -- that identity
    stays entirely on the session-revocation side of `delete_account()`
    below."""

    async def purge_postgres_rows(self, internal_user_id: str) -> int: ...
    async def purge_vector_embeddings(self, internal_user_id: str) -> int: ...
    async def purge_memories(self, internal_user_id: str) -> int: ...
    async def revoke_oauth_tokens(self, internal_user_id: str) -> int: ...


@dataclass
class DeletionResult:
    user_id: str
    sessions_revoked: bool
    postgres_rows_deleted: int
    vector_embeddings_deleted: int
    memories_deleted: int
    oauth_tokens_revoked: int


async def delete_account(
    *,
    google_sub: str,
    internal_user_id: str,
    deletion_store: DeletionStore,
    revocation_store: RevocationStore,
) -> DeletionResult:
    """Sessions are revoked FIRST, before any real data purge -- locking
    the account down for any further access before its data is removed,
    rather than the reverse order, which would leave a real window where
    a still-valid session could act against data mid-deletion.

    Two real, distinct identifiers, never conflated (`DEC-113`):
    `google_sub` is the real identity `revoke_all_for_user()` and the
    whole JWT/refresh-token session-management system use; `internal_
    user_id` is the real, resolved UUID every per-user domain table
    (and `deletion_store`'s own methods) actually expects. The real
    `DeletionResult.user_id` reports the internal UUID -- the identity
    that will actually mean something once this session's tokens are
    gone.
    """
    await revoke_all_for_user(google_sub, revocation_store)

    return DeletionResult(
        user_id=internal_user_id,
        sessions_revoked=True,
        postgres_rows_deleted=await deletion_store.purge_postgres_rows(internal_user_id),
        vector_embeddings_deleted=await deletion_store.purge_vector_embeddings(internal_user_id),
        memories_deleted=await deletion_store.purge_memories(internal_user_id),
        oauth_tokens_revoked=await deletion_store.revoke_oauth_tokens(internal_user_id),
    )
