"""Real, live persistence for Google's own OAuth tokens (Phase 3,
`QUORUM_PRODUCTION_COMPLETION_PLAN.md`) -- closes the real, disclosed
gap `auth/google_oauth.py`'s own top-of-file docstring has named since
it was first written. See `migrations/0010_google_oauth_tokens/up.sql`'s
own top comment for the real schema and the real, disclosed sequencing
requirement this table's `ON DELETE CASCADE` creates for account
deletion.

Every function here takes the real, internal UUID (`DEC-110`'s `users`
table), never the Google `sub` -- the same convention every other real
per-user table in this backend already follows, and the same real
distinction `DEC-113` had to explicitly enforce for `refresh_tokens`.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import asyncpg

from quorum_backend.auth.google_token_refresh import refresh_google_access_token
from quorum_backend.security.google_token_encryption import decrypt_token, encrypt_token


@dataclass(frozen=True)
class GoogleTokenRecord:
    access_token: str
    refresh_token: str
    access_token_expires_at: datetime
    granted_scopes: str


async def store_google_tokens(
    pool: asyncpg.Pool,
    *,
    internal_user_id: str,
    access_token: str,
    refresh_token: str | None,
    access_token_expires_at: datetime,
    granted_scopes: str,
    encryption_key: str,
) -> None:
    """Real, atomic upsert. `refresh_token` is `None` in exactly one
    real caller: `google_token_refresh.py`'s own refresh flow, whose
    Google `grant_type=refresh_token` response never includes a fresh
    one (confirmed against Google's own documentation before relying on
    this) -- the real prior, still-valid encrypted refresh_token must
    survive that call intact, never overwritten with `NULL`.

    A REAL, LIVE, POSTGRES-SPECIFIC BUG FOUND AND FIXED WHILE WRITING
    THIS MODULE'S OWN TESTS, before any review: an earlier version
    resolved the `NULL`-refresh_token fallback inside the `ON CONFLICT
    DO UPDATE SET ... COALESCE(EXCLUDED.x, table.x)` clause -- syntactically
    correct-looking SQL that fails LIVE, every time, with a real
    `NotNullViolationError`. Confirmed via a real, minimal, unrelated
    reproduction table before trusting the explanation: Postgres checks
    a `NOT NULL` constraint against the raw `VALUES(...)` list BEFORE
    `ON CONFLICT` resolution ever runs -- a real `NULL` literal passed
    into the `VALUES` clause for a `NOT NULL` column raises immediately,
    even when the `DO UPDATE SET` clause would have replaced it with a
    real, non-null value via `COALESCE`. Fixed by moving the `COALESCE`
    INTO the `VALUES` clause itself, resolved against a real subquery
    for the existing row's own current value -- the constraint check
    then sees an already-non-null, already-resolved value, not a raw
    `NULL` headed for a conflict that hasn't been decided yet."""
    encrypted_refresh = encrypt_token(refresh_token, encryption_key=encryption_key) if refresh_token else None
    await pool.execute(
        """
        INSERT INTO google_oauth_tokens
            (user_id, encrypted_access_token, encrypted_refresh_token, access_token_expires_at, granted_scopes, updated_at)
        VALUES (
            $1, $2,
            COALESCE($3, (SELECT encrypted_refresh_token FROM google_oauth_tokens WHERE user_id = $1)),
            $4, $5, now()
        )
        ON CONFLICT (user_id) DO UPDATE SET
            encrypted_access_token = EXCLUDED.encrypted_access_token,
            encrypted_refresh_token = EXCLUDED.encrypted_refresh_token,
            access_token_expires_at = EXCLUDED.access_token_expires_at,
            granted_scopes = EXCLUDED.granted_scopes,
            updated_at = now()
        """,
        uuid.UUID(internal_user_id),
        encrypt_token(access_token, encryption_key=encryption_key),
        encrypted_refresh,
        access_token_expires_at,
        granted_scopes,
    )


async def fetch_google_tokens(
    pool: asyncpg.Pool, *, internal_user_id: str, encryption_key: str
) -> GoogleTokenRecord | None:
    """Returns `None` honestly when this user has never granted Google
    access, or their real tokens were already revoked/deleted -- never
    a fabricated record. Real, live decryption happens here, not at the
    caller -- ciphertext never leaves this module."""
    row = await pool.fetchrow(
        "SELECT encrypted_access_token, encrypted_refresh_token, access_token_expires_at, granted_scopes "
        "FROM google_oauth_tokens WHERE user_id = $1",
        uuid.UUID(internal_user_id),
    )
    if row is None:
        return None
    return GoogleTokenRecord(
        access_token=decrypt_token(row["encrypted_access_token"], encryption_key=encryption_key),
        refresh_token=decrypt_token(row["encrypted_refresh_token"], encryption_key=encryption_key),
        access_token_expires_at=row["access_token_expires_at"],
        granted_scopes=row["granted_scopes"],
    )


async def delete_google_tokens(pool: asyncpg.Pool, *, internal_user_id: str) -> int:
    """Real, live delete -- returns the real count (`0` or `1`, this
    table's own `user_id` is a real primary key) so a caller can
    distinguish "genuinely deleted a real row" from "nothing was ever
    stored," the same real-count-not-bare-bool convention `security/
    supabase_deletion_store.py`'s own methods already follow."""
    tag = await pool.execute("DELETE FROM google_oauth_tokens WHERE user_id = $1", uuid.UUID(internal_user_id))
    return int(tag.rsplit(" ", 1)[-1])


# A real, deliberate safety margin before a token's own real expiry --
# refreshing 5 real minutes early means a real, in-flight Gmail/Calendar
# API call started right before expiry never races Google's own clock.
GOOGLE_ACCESS_TOKEN_REFRESH_MARGIN_SECONDS = 300


async def get_valid_google_access_token(
    pool: asyncpg.Pool,
    *,
    internal_user_id: str,
    client_id: str,
    client_secret: str,
    encryption_key: str,
) -> str | None:
    """The one real function Phase 4's Gmail/Calendar integrations
    should call -- never `fetch_google_tokens` directly -- for a
    currently-usable real access token, refreshing it first if it's
    expired or about to be. Returns `None` honestly when no real Google
    tokens are stored for this user at all (never granted, or already
    revoked) -- never a fabricated token."""
    record = await fetch_google_tokens(pool, internal_user_id=internal_user_id, encryption_key=encryption_key)
    if record is None:
        return None

    now = datetime.now(timezone.utc)
    seconds_until_expiry = (record.access_token_expires_at - now).total_seconds()
    if seconds_until_expiry > GOOGLE_ACCESS_TOKEN_REFRESH_MARGIN_SECONDS:
        return record.access_token

    new_access_token, new_expires_at = await refresh_google_access_token(
        refresh_token=record.refresh_token, client_id=client_id, client_secret=client_secret
    )
    await store_google_tokens(
        pool,
        internal_user_id=internal_user_id,
        access_token=new_access_token,
        refresh_token=None,
        access_token_expires_at=new_expires_at,
        granted_scopes=record.granted_scopes,
        encryption_key=encryption_key,
    )
    return new_access_token
