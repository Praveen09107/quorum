"""Real Google connection health (`DEC-198`, product rebuild). Backs
`GET /connections`.

WHY THIS EXISTS: this rebuild's own root-cause research named the
single biggest reason the app feels dead -- one expired OAuth token
dams the entire Gmail + Calendar + Career surface, silently, with
nothing anywhere in the app telling the user this is happening. A real
re-auth already fixes it every time it's tried; the actual, disclosed
gap is that there was never a real screen that could tell a signed-in
user their own grant had gone stale, or that Quorum even requested
Calendar/email access at all.

REAL, DELIBERATE SCOPE DECISION: this module does NOT invent a "last
successful ingestion" timestamp. No such fact is persisted per-user
anywhere in this backend's history (`email_ingestion.py`'s own
`GOOGLE_TOKEN_REFRESH_FAILED` outcome is aggregated into one real,
whole-batch count, never written back per-user) -- adding that would be
a genuinely separate schema change this session's own scope doesn't
need. What this module surfaces instead is honest and already real:
whether a grant exists at all, its real granted scopes, when it was
last written (`google_oauth_tokens.updated_at` -- a real consent or
refresh, not a mailbox scan), and whether it can be refreshed RIGHT
NOW -- checked live, by making the exact same real call `email_
ingestion.py`'s own per-user poll already depends on, never a guess
from the stored expiry alone (a token can look unexpired in storage
and still fail a live refresh if the underlying grant was revoked).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import asyncpg

from quorum_backend.auth.google_oauth import GoogleOAuthExchangeFailed
from quorum_backend.auth.google_token_store import fetch_google_tokens, get_valid_google_access_token


@dataclass(frozen=True)
class ConnectionHealth:
    connected: bool
    granted_scopes: list[str]
    last_updated_at: datetime | None
    # `None` only when `connected` is `False` -- there is genuinely
    # nothing to test a live refresh against. `True`/`False` otherwise,
    # from a real, live attempt, never inferred from the stored expiry
    # alone -- see this module's own top-of-file docstring.
    token_refreshable: bool | None


async def get_connection_health(
    pool: asyncpg.Pool,
    *,
    internal_user_id: str,
    client_id: str,
    client_secret: str,
    encryption_key: str,
) -> ConnectionHealth:
    """Real, live per-user check. `granted_scopes` is Google's own
    real, space-separated scope string split into a list -- an honest
    empty list for a genuinely absent grant, never `None` (the real
    caller on the mobile side renders this as a real list of rows, no
    `null`-checking needed for the common case)."""
    record = await fetch_google_tokens(pool, internal_user_id=internal_user_id, encryption_key=encryption_key)
    if record is None:
        return ConnectionHealth(connected=False, granted_scopes=[], last_updated_at=None, token_refreshable=None)

    try:
        await get_valid_google_access_token(
            pool,
            internal_user_id=internal_user_id,
            client_id=client_id,
            client_secret=client_secret,
            encryption_key=encryption_key,
        )
        refreshable = True
    except GoogleOAuthExchangeFailed:
        # A real, revoked (or currently un-refreshable) grant -- the
        # same real, distinct outcome `email_ingestion.py`'s own
        # `GOOGLE_TOKEN_REFRESH_FAILED` already names, surfaced here
        # per-user instead of folded into a whole-batch count.
        refreshable = False

    return ConnectionHealth(
        connected=True,
        granted_scopes=record.granted_scopes.split() if record.granted_scopes else [],
        last_updated_at=record.updated_at,
        token_refreshable=refreshable,
    )
