"""Real, live user-provisioning -- the bridge between Google's raw
`sub` (what the auth system's own JWT/refresh-token layer already uses
as `user_id`, unchanged) and the real, internal UUID every per-user
domain table (`tasks`, `expenses`, `applications`, `note_embeddings`)
actually expects in its own `user_id` column.

HONEST DISCLOSURE: found live while scoping `DELETE /account` (`DEC-110`)
-- no table anywhere in this backend had ever mapped a real Google
identity onto one of these UUIDs, which is the real, root cause of the
disclosed per-user-scoping limitation already carried by
`/trust_digest`, `/tasks`, `/career_pipeline`, and
`/finance/subscriptions`. This module closes that gap, without
touching the already-reviewed, CRITICAL-tier `auth/refresh_token.py`
system at all -- `refresh_tokens.user_id` (confirmed `TEXT`, not
`UUID`, against the real `0002` migration) and the JWT's own `sub`
claim continue carrying Google's raw sub string unchanged.

A real, confirmed-safe name collision, the same pattern already
disclosed for `refresh_tokens` (`DEC-101`/`DEC-102`): Supabase
provisions its own internal `auth.users` table by default. This
module's real table lives in `public.users` -- confirmed live, this
session, via `SHOW search_path` (`"$user", public, extensions` -- no
`auth` schema present) and `'users'::regclass`, that every unqualified
`users` reference in this module resolves to the real, intended table.
"""
from __future__ import annotations

import asyncpg


async def get_or_create_user(pool: asyncpg.Pool, *, google_sub: str, email: str | None) -> str:
    """Real, atomic upsert -- returns the real, internal UUID for this
    Google identity, creating a new real row on first sign-in.
    `INSERT ... ON CONFLICT ... DO UPDATE` (rather than a separate
    SELECT-then-INSERT) closes a real race: two near-simultaneous first
    sign-ins for the same real person must never create two different
    UUIDs for one real identity.

    `email` is refreshed on every real call, not just at creation -- a
    real, honest reflection of Google's own most recent value, never a
    stale one left over from a person's first sign-in."""
    row = await pool.fetchrow(
        """
        INSERT INTO users (google_sub, email)
        VALUES ($1, $2)
        ON CONFLICT (google_sub) DO UPDATE SET email = EXCLUDED.email
        RETURNING user_id
        """,
        google_sub,
        email,
    )
    return str(row["user_id"])


async def resolve_internal_user_id(pool: asyncpg.Pool, *, google_sub: str) -> str | None:
    """Real, live lookup -- returns the internal UUID already
    provisioned for this Google identity, or `None` if this person has
    never actually completed a real sign-in. In practice this should be
    unreachable (provisioning happens at `/auth/token` issuance time,
    before any access token exists to reach a per-user route with), but
    a caller presenting a syntactically valid token for a genuinely
    unprovisioned identity is handled as a real, honest `None` -- never
    silently treated as "show every user's data.\""""
    row = await pool.fetchrow("SELECT user_id FROM users WHERE google_sub = $1", google_sub)
    return str(row["user_id"]) if row is not None else None
