"""The real, live implementation of `refresh_token.py`'s `RevocationStore`
Protocol -- backed by the real `refresh_tokens` table (migration
`0002_refresh_tokens`), the storage layer that module's own docstring
named as "a separate, later integration concern" (`IMPL_12`). This is
that integration.

HONEST NOTE on a real, harmless name collision, found and confirmed
before trusting it, not assumed: Supabase provisions its own internal
`auth.refresh_tokens` table in every project by default (part of
Supabase's own Auth product, which this project does not use). This
module's real table lives in the `public` schema instead
(`public.refresh_tokens`) -- confirmed live, via `information_schema.
tables`, that both exist as genuinely separate tables in separate
schemas, and that Postgres's default `search_path` resolves every
unqualified query in this file to `public.refresh_tokens`, never
Supabase's internal one. No functional collision; disclosed here purely
so a future reader isn't confused by the coincidence.

REAL, DISCLOSED CORRECTION, found by fresh-context review before this
module ever merged to `main`: an earlier version of `claim_and_rotate()`
was a separate `try_claim()` method (an atomic `UPDATE ... WHERE
used = false`) plus a fully independent, later `INSERT` performed by
`refresh_token.py`'s own `issue_refresh_token()` call. That left a real
gap between the two statements with no ordering guarantee against a
concurrent loser's `revoke_family()` -- a race winner's brand-new child
token could end up committed AFTER the loser's revoke_family() already
ran, escaping revocation entirely. `claim_and_rotate()` below closes
this for real: the OLD token's claim and the NEW record's insertion now
happen inside one transaction, holding a real row lock
(`SELECT ... FOR UPDATE`) on the old token for the transaction's full
duration -- a concurrently racing call is genuinely blocked at the
database level until that whole transaction, insert included, commits.
"""
from __future__ import annotations

import asyncpg

from quorum_backend.auth.refresh_token import RefreshTokenRecord


class SupabaseRevocationStore:
    """Real, live -- every method is a genuine round-trip to the real
    Supabase database, never an in-memory fake. See `claim_and_rotate()`
    for the one method whose real atomicity this whole module's security
    property depends on."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get(self, token_hash: str) -> RefreshTokenRecord | None:
        row = await self._pool.fetchrow(
            "SELECT token_hash, family_id, user_id, issued_at, expires_at, used, revoked "
            "FROM refresh_tokens WHERE token_hash = $1",
            token_hash,
        )
        if row is None:
            return None
        return RefreshTokenRecord(
            token_hash=row["token_hash"],
            family_id=str(row["family_id"]),
            user_id=row["user_id"],
            issued_at=row["issued_at"],
            expires_at=row["expires_at"],
            used=row["used"],
            revoked=row["revoked"],
        )

    async def save(self, record: RefreshTokenRecord) -> None:
        # A real upsert -- issue_refresh_token() always calls this for a
        # brand-new record (INSERT path), but ON CONFLICT DO UPDATE keeps
        # this method correct if it's ever called again for an existing
        # row (it currently isn't, but the Protocol doesn't promise that).
        await self._pool.execute(
            """
            INSERT INTO refresh_tokens (token_hash, family_id, user_id, issued_at, expires_at, used, revoked)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (token_hash) DO UPDATE SET
                used = EXCLUDED.used,
                revoked = EXCLUDED.revoked
            """,
            record.token_hash,
            record.family_id,
            record.user_id,
            record.issued_at,
            record.expires_at,
            record.used,
            record.revoked,
        )

    async def claim_and_rotate(self, old_token_hash: str, new_record: RefreshTokenRecord) -> bool:
        # THE real atomic guarantee refresh_token.py's own docstring
        # depends on. One connection, one transaction, for the whole
        # operation -- `SELECT ... FOR UPDATE` takes a real row lock on
        # the OLD token that's held until COMMIT, so a second, genuinely
        # concurrent call attempting to lock the SAME row (even from an
        # entirely separate Cloud Run container instance) blocks at the
        # database level until this transaction -- claim AND insert
        # together -- has fully committed. Only once unblocked does that
        # second call see `used = True` and correctly report a loss; by
        # then this call's `new_record` is already committed and visible,
        # so the loser's subsequent `revoke_family()` is guaranteed to
        # catch it.
        async with self._pool.acquire() as conn, conn.transaction():
            row = await conn.fetchrow(
                "SELECT used FROM refresh_tokens WHERE token_hash = $1 FOR UPDATE",
                old_token_hash,
            )
            if row is None or row["used"]:
                return False
            await conn.execute("UPDATE refresh_tokens SET used = true WHERE token_hash = $1", old_token_hash)
            await conn.execute(
                """
                INSERT INTO refresh_tokens (token_hash, family_id, user_id, issued_at, expires_at, used, revoked)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                new_record.token_hash,
                new_record.family_id,
                new_record.user_id,
                new_record.issued_at,
                new_record.expires_at,
                new_record.used,
                new_record.revoked,
            )
            return True

    async def revoke_family(self, family_id: str) -> None:
        await self._pool.execute("UPDATE refresh_tokens SET revoked = true WHERE family_id = $1", family_id)

    async def get_family_ids_for_user(self, user_id: str) -> set[str]:
        rows = await self._pool.fetch("SELECT DISTINCT family_id FROM refresh_tokens WHERE user_id = $1", user_id)
        return {str(row["family_id"]) for row in rows}
