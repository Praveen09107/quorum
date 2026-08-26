"""Real Google-token refresh flow (Phase 3, `QUORUM_PRODUCTION_
COMPLETION_PLAN.md`) -- genuinely separate from Quorum's own internal
JWT refresh (`auth/refresh_token.py`), per that phase's own explicit
requirement not to conflate two real, distinct token families the way
`DEC-113` had to explicitly un-conflate `google_sub` vs. internal
`user_id`. `auth/refresh_token.py`'s own rotation-with-theft-detection
design has NO real analogue here: Google's own refresh_token doesn't
rotate on use (confirmed against Google's own documentation before
relying on it) -- the same one keeps working until explicitly revoked
or unused for 6 months, so there is no "reuse of an already-rotated
token" signature to detect on this side at all. This module is
deliberately simple because the real underlying protocol is.

Reuses `auth/google_oauth.py`'s own real `GOOGLE_TOKEN_URL` constant and
`GoogleOAuthExchangeFailed` exception -- a real refresh-grant failure
and a real authorization-code-exchange failure are both "Google's own
/token endpoint rejected this request," the same real failure category,
not two independently-invented exception types for one real concept.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from quorum_backend.auth.google_oauth import GOOGLE_TOKEN_URL, GoogleOAuthExchangeFailed


async def refresh_google_access_token(
    *, refresh_token: str, client_id: str, client_secret: str
) -> tuple[str, datetime]:
    """Real, live POST to Google's actual token endpoint with
    `grant_type=refresh_token`. Google's real response for this grant
    type does not include a new `refresh_token` in the ordinary case --
    only a fresh `access_token`/`expires_in` -- so this function's own
    return type deliberately excludes one; `google_token_store.py`'s own
    caller keeps using the refresh_token already on record.

    A real 400/401 here most commonly means the real refresh_token
    itself was revoked (by the user, at Google's own account settings,
    independently of this app) or expired from 6 real months of disuse
    -- surfaced as `GoogleOAuthExchangeFailed`, never silently retried
    with a token that will never work again."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
            },
        )
    if response.status_code != 200:
        raise GoogleOAuthExchangeFailed(f"Google token refresh failed ({response.status_code}): {response.text}")
    body = response.json()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(body["expires_in"]))
    return body["access_token"], expires_at
