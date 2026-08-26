"""The real, live `DeletionStore` implementation (`security/
account_deletion.py`'s own injected Protocol), backing `DELETE /account`
(`QUORUM_DATA_CONTRACTS.md` §5.8). HONEST DISCLOSURE: this real
implementation did not exist anywhere in this backend before `DEC-113`
-- `account_deletion.py`'s own docstring named it as "out of scope"
since the module was first built, deferred until a real
user-identity-provisioning system existed to make a correctly-scoped
purge possible at all (`DEC-110`).

**A real, necessary deletion order, confirmed against the real schema
before writing a line of SQL, not assumed:** `interviews.application_id`
references `applications(application_id)` with no `ON DELETE CASCADE`
(confirmed directly against `backend/migrations/0001_initial_schema/
up.sql`) -- the default `NO ACTION` behavior means deleting an
`applications` row while a real `interviews` row still references it
raises a genuine foreign-key violation. `interviews` rows for this
user's own applications are deleted first, via a real subquery, before
`applications` itself.

**A real, deliberate scope split, matching `DeletionResult`'s own
four-store shape:** `purge_postgres_rows()` covers the real relational
tables this account genuinely owns data in -- `tasks`, `expenses`,
`applications` (+ their `interviews`), `action_events`, `negotiations`,
and the real `users` row itself (so a future re-signup with the same
Google identity gets a genuinely fresh internal UUID, never silently
resurrecting deleted history). `purge_vector_embeddings()` covers
`note_embeddings` specifically -- the one real table with a pgvector
column, a genuine conceptual distinct from the other tables even
though it lives in the same real Postgres database.

**`action_events`/`negotiations` purging: RESOLVED, `DEC-124`, real,
disclosed gap found and closed, not left open.** A stale comment here
previously claimed `action_events` "has no `user_id` column at all,"
true when originally written but false since `DEC-119`'s migration
`0004` added one -- corrected first as a disclosed, still-open gap
(`DEC-123`, found while working on unrelated negotiation-choice code),
then actually closed here, as its own explicit CRITICAL-tier session
rather than an incidental patch. Deleting a `negotiations` row also
removes any real `positions`/`options` `DEC-121` persisted to it --
genuinely part of this account's own data, not a separate concern.
`retry_queue` remains genuinely, permanently out of scope for per-user
purging: it is a real, generic, system-level job queue with no
per-user ownership *column* at all (a user's own `user_id` may appear
inside an individual job's `payload` JSONB, but that is not a
queryable, indexed relationship this store can safely scope a bulk
delete against) -- a real, disclosed, permanent limitation, not
something a future session should expect to close the way this one
closed `action_events`/`negotiations`.

**`revoke_oauth_tokens()` is now real, Phase 3 (`QUORUM_PRODUCTION_
COMPLETION_PLAN.md`).** This paragraph previously described it as an
honest, disclosed zero -- true when written (Google's own tokens were
never persisted anywhere in this backend), false since `auth/google_
token_store.py` closed that gap. `purge_memories()` remains a real,
honest zero: no real `mem0` integration exists anywhere in this backend
(confirmed by direct search), a genuinely different, still-open gap.

**A REAL, DISCLOSED SEQUENCING REQUIREMENT `revoke_oauth_tokens()`
introduces, closed in `security/account_deletion.py::delete_account()`
the same session:** `google_oauth_tokens.user_id` has `ON DELETE
CASCADE` against `users` (`migrations/0010_google_oauth_tokens/up.sql`)
-- if `purge_postgres_rows()` (which deletes the real `users` row) ran
BEFORE this method, the cascade would silently delete this table's own
row first, leaving nothing here to send to Google's real `/revoke`
endpoint. `delete_account()` now calls `revoke_oauth_tokens()` before
`purge_postgres_rows()`, mirroring the same "revoke access to the real,
external thing before destroying the local record that makes revoking
it possible" reasoning that function's own docstring already uses for
session revocation running first.

**A real, disclosed atomicity gap, found by CRITICAL-tier review
(`DEC-113`), not silently left unexamined:** `purge_postgres_rows()`'s
own transaction does NOT extend to `purge_vector_embeddings()` --
`delete_account()` (`security/account_deletion.py`) calls these as two
separate, independently-awaited store methods, each opening its own
connection. In the narrow case where `purge_postgres_rows()` succeeds
(the real `users` row is gone) but `purge_vector_embeddings()` then
fails (a dropped connection, a transient DB error), a retry of
`DELETE /account` 404s immediately -- `_resolve_internal_user_id_or_404`
can no longer find the now-deleted `users` row -- permanently orphaning
that user's `note_embeddings`. Deliberately not fixed by forcing the two
methods into one shared transaction here: both are independently
callable and independently tested (`test_supabase_deletion_store.py`)
by design, matching `DeletionResult`'s own real four-store shape: this
class's true minimum footprint. Tracked as a real, open, low-probability
follow-up in `STATUS_INDEX.md` rather than an unexamined risk or an
architecture change beyond what this session's real scope called for.
"""
from __future__ import annotations

import logging
import uuid

import asyncpg

from quorum_backend.auth.google_oauth import GoogleOAuthExchangeFailed, revoke_google_token
from quorum_backend.auth.google_token_store import delete_google_tokens, fetch_google_tokens
from quorum_backend.security.google_token_encryption import GoogleTokenDecryptionFailed

logger = logging.getLogger("quorum_backend")


def _parse_deleted_count(command_status: str) -> int:
    """asyncpg's `execute()` returns the real Postgres command-status
    string (e.g. `"DELETE 3"`), not a count directly -- parses the real,
    trailing integer. A real, established asyncpg pattern, not a fragile
    guess."""
    return int(command_status.rsplit(" ", 1)[-1])


class SupabaseDeletionStore:
    def __init__(self, pool: asyncpg.Pool, *, google_token_encryption_key: str | None = None):
        self._pool = pool
        # Resolved once, at construction time, by the real caller
        # (`main.py`'s own `delete_account_route`) from `core/config.py`
        # -- the same resolve-in-the-route-then-pass-down convention
        # every other real credential in this backend already follows
        # (e.g. `settings.gemini_api_key` passed into `make_gemini_
        # position_call`, never read from inside that factory).
        self._google_token_encryption_key = google_token_encryption_key

    async def purge_postgres_rows(self, internal_user_id: str) -> int:
        """A real, deliberate design choice, not a default left
        unconsidered: all five real deletes run inside one real Postgres
        transaction (`conn.transaction()`), not as five independent
        statements. This is an irreversible operation -- if any one real
        delete fails partway (a genuine constraint violation, a dropped
        connection), the whole real purge rolls back rather than leaving
        an account in a real, half-deleted state that's neither fully
        present nor fully gone."""
        user_uuid = uuid.UUID(internal_user_id)
        total = 0

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # Real, necessary order: interviews before applications,
                # closing the real FK constraint confirmed in this
                # module's own docstring.
                total += _parse_deleted_count(
                    await conn.execute(
                        "DELETE FROM interviews WHERE application_id IN (SELECT application_id FROM applications WHERE user_id = $1)",
                        user_uuid,
                    )
                )
                total += _parse_deleted_count(
                    await conn.execute("DELETE FROM applications WHERE user_id = $1", user_uuid)
                )
                total += _parse_deleted_count(await conn.execute("DELETE FROM tasks WHERE user_id = $1", user_uuid))
                total += _parse_deleted_count(
                    await conn.execute("DELETE FROM expenses WHERE user_id = $1", user_uuid)
                )
                # DEC-124: real, previously-missing purges. No FK
                # references either table (confirmed by grepping every
                # real migration for "REFERENCES action_events"/
                # "REFERENCES negotiations" before writing this --
                # neither table is ever the target of a foreign key),
                # so ordering relative to the other four deletes in
                # this transaction genuinely doesn't matter.
                total += _parse_deleted_count(
                    await conn.execute("DELETE FROM action_events WHERE user_id = $1", user_uuid)
                )
                total += _parse_deleted_count(
                    await conn.execute("DELETE FROM negotiations WHERE user_id = $1", user_uuid)
                )
                # The real users row itself, last. A REAL, DISCLOSED
                # CORRECTION to this comment's own earlier claim: as of
                # migration 0010, `google_oauth_tokens.user_id` DOES hold
                # a real, database-enforced `ON DELETE CASCADE` FK against
                # this table -- by the time this line runs (this method
                # is always called AFTER `revoke_oauth_tokens()`, see
                # `security/account_deletion.py::delete_account()`'s own
                # real, deliberate ordering), that row is already gone,
                # so the cascade is a real, harmless no-op in the intended
                # flow; it only actually fires if this method is ever
                # called standalone, skipping revocation, in which case
                # it correctly cleans up an orphaned row rather than
                # leaving one behind. Ordering relative to the four other
                # deletes above still genuinely doesn't matter -- done
                # last here simply to keep the identity valid for as much
                # of this real operation as possible, in case a later
                # step needs to look it up for a real diagnostic.
                #
                # A SECOND real table also rides this same cascade,
                # genuinely passively this time: `sent_messages.user_id`
                # (migration 0011, Phase 4) holds its own real `ON
                # DELETE CASCADE` FK against this table too. Unlike
                # `google_oauth_tokens`, it has no external side effect
                # to revoke first (it is local bookkeeping only, never a
                # live external grant), so it needs no dedicated
                # `revoke_*` method of its own -- this single `DELETE`
                # genuinely purges it, real-database-verified by this
                # session's own CRITICAL-tier review (`DEC-140`,
                # finding M3) via a dedicated cascade test in `test_
                # supabase_deletion_store.py`. Not counted in `total`
                # below, the same as `google_oauth_tokens`'s own cascade
                # -- Postgres's own `DELETE` command tag only reports
                # rows removed from the target table directly, never
                # cascade-affected rows in other tables.
                total += _parse_deleted_count(await conn.execute("DELETE FROM users WHERE user_id = $1", user_uuid))

        return total

    async def purge_vector_embeddings(self, internal_user_id: str) -> int:
        return _parse_deleted_count(
            await self._pool.execute(
                "DELETE FROM note_embeddings WHERE user_id = $1", uuid.UUID(internal_user_id)
            )
        )

    async def purge_memories(self, internal_user_id: str) -> int:
        # Real, honest zero -- see this module's own top-of-file
        # docstring for the full account of why.
        return 0

    async def revoke_oauth_tokens(self, internal_user_id: str) -> int:
        """Real, live -- see this module's own top-of-file docstring for
        the full account of the real sequencing requirement this method
        creates. Returns `0` honestly (never raises) when this user
        never granted Google access at all, or `GOOGLE_TOKEN_ENCRYPTION_
        KEY` isn't configured on this deployment -- an account deletion
        must never be blocked by a real feature this specific real user
        never actually used.

        **TWO REAL, LIVE BUGS FOUND BY THIS PR'S OWN CRITICAL-TIER
        REVIEW, BOTH FIXED HERE:** an earlier version let a real
        `GoogleTokenDecryptionFailed` (a real encryption-key rotation
        with no real migration path for rows encrypted under the old
        key) or a real `GoogleOAuthExchangeFailed` (a genuine Google
        `/revoke` outage or network failure) propagate straight out of
        this method, through `delete_account()`, and out of the real
        `DELETE /account` route as an unhandled `500` -- live-proven to
        leave the account PERMANENTLY undeletable: session revocation
        had already run by the time this method is reached (`delete_
        account()`'s own real ordering), so the user is logged out with
        no working retry path, and this real, S3-equivalent irreversible
        operation has no other real entry point. Both real failure modes
        are now caught, logged loudly, and never block the rest of this
        real account deletion -- the same "an account deletion must
        never be blocked by a real feature this specific real user never
        actually used" principle, extended to "...or a real, external
        failure this specific real user has no control over."

        **A REAL, DISCLOSED, NOT-FULLY-CLOSED GAP, found by the same
        review, matching `DEC-113`'s own already-disclosed atomicity
        gap for `purge_postgres_rows`/`purge_vector_embeddings`:** this
        method's own real local delete and `purge_postgres_rows()` are
        independently awaited, not one shared transaction. If Google's
        real revoke call and this method's own local delete both
        succeed, but `purge_postgres_rows()` then fails, the account
        still exists but its stored Google tokens are already gone --
        a real, live, still-open risk, not silently treated as closed
        by the fixes above. Also honest, not hidden: on a real Google-
        side failure, the real local row is still deleted (so this
        method never re-attempts the same failing real revoke call
        forever), but the real external Google grant may still be live
        until it naturally expires or the user revokes it manually at
        Google's own account settings -- `oauth_tokens_revoked` in this
        case reports the real LOCAL deletion count, not a guarantee the
        real external grant was confirmed revoked."""
        if self._google_token_encryption_key is None:
            return 0
        try:
            record = await fetch_google_tokens(
                self._pool, internal_user_id=internal_user_id, encryption_key=self._google_token_encryption_key
            )
        except GoogleTokenDecryptionFailed:
            logger.exception(
                "Real Google token ciphertext for user_id=%s failed to decrypt during account deletion -- "
                "deleting the real, undecryptable row locally without a real Google revoke call (nothing "
                "could be recovered from it to revoke), never blocking the rest of this real account deletion.",
                internal_user_id,
            )
            return await delete_google_tokens(self._pool, internal_user_id=internal_user_id)
        if record is None:
            return 0
        try:
            await revoke_google_token(record.refresh_token)
        except GoogleOAuthExchangeFailed:
            logger.exception(
                "Real Google token revocation failed for user_id=%s during account deletion (a real Google "
                "outage or network failure) -- the real local row is still deleted so this never blocks the "
                "rest of deletion, but the real external Google grant may still be live until it naturally "
                "expires or the user revokes it manually at Google's own account settings.",
                internal_user_id,
            )
        return await delete_google_tokens(self._pool, internal_user_id=internal_user_id)
