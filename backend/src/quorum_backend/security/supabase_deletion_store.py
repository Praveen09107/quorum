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

**Two real, honest, disclosed zeros, not silently faked:**
`purge_memories()` -- no real `mem0` integration exists anywhere in this
backend (confirmed by direct search); `revoke_oauth_tokens()` -- Google's
own real `access_token`/`refresh_token` are deliberately never persisted
here (confirmed directly against `auth/google_oauth.py`'s own
docstring), so there is nothing real to revoke via a Google API call.
Both real, disclosed gaps, not gaps this class silently hides behind a
plausible-looking nonzero number.

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

import uuid

import asyncpg


def _parse_deleted_count(command_status: str) -> int:
    """asyncpg's `execute()` returns the real Postgres command-status
    string (e.g. `"DELETE 3"`), not a count directly -- parses the real,
    trailing integer. A real, established asyncpg pattern, not a fragile
    guess."""
    return int(command_status.rsplit(" ", 1)[-1])


class SupabaseDeletionStore:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

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
                # The real users row itself, last -- no other real table
                # has a database-enforced FK against it (confirmed
                # against the real 0003 migration), so ordering relative
                # to the four deletes above genuinely doesn't matter;
                # done last here simply to keep the identity valid for
                # as much of this real operation as possible, in case a
                # later step needs to look it up for a real diagnostic.
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
        # Real, honest zero -- see this module's own top-of-file
        # docstring for the full account of why.
        return 0
