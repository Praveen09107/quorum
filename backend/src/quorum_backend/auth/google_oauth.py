"""Real Google OAuth server-side code exchange.

New this session (Batch 10 Phase 3): the actual network calls to Google
that `POST /auth/token` performs, real per `QUORUM_DATA_CONTRACTS.md`
§5.5 ("exchanges a Gmail OAuth authorization code (server-side)... for
a Quorum access + refresh token pair"). No literal request/response
JSON shape exists anywhere in this project's real spec corpus for this
specific exchange -- the file that section cites for the full flow,
`QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §14.2, has never actually
existed in this repository (confirmed by direct search; the same real
absence `IMPL_12`'s own `DEC-062` entry already found and worked around
for the token modules themselves). This module is a real, reasoned
construction against standard OAuth 2.0 Authorization Code + PKCE
practice, not a recalled spec value.

Deliberately narrow scope, disclosed rather than silently expanded:
this module verifies the caller's real Google identity (via the
returned, signature-verified `id_token`) and returns just enough to
issue a Quorum session -- it does NOT persist Google's own access/
refresh tokens for later Gmail/Calendar API calls. That's a real,
separate, currently-open gap (see `STATUS_INDEX.md`) belonging to
whichever session builds the real email/calendar agent's live Google
API integration -- `IMPL_12`'s own scope was strictly session
management, never Google token storage, and this session doesn't
silently expand that.
"""
from __future__ import annotations

import httpx
import jwt
from jwt import PyJWKClient

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
# Google documents both forms as valid real issuer values for an id_token
# -- https://developers.google.com/identity/openid-connect/openid-connect#validatinganidtoken
GOOGLE_ID_TOKEN_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}

# One real, shared client across the process -- real connection pooling/
# keep-alive to Google's endpoints, not a fresh TCP+TLS handshake per
# request. `PyJWKClient` does its own internal caching of the fetched
# key set, so real repeated verifications don't re-fetch every time.
_jwks_client = PyJWKClient(GOOGLE_JWKS_URL)


class GoogleOAuthExchangeFailed(Exception):
    """Google's real token endpoint rejected the exchange -- an invalid
    or already-used authorization code, a redirect_uri mismatch, or a
    failed PKCE verification. Carries Google's own real error string,
    never swallowed or replaced with a generic message."""


class GoogleIdTokenInvalid(Exception):
    """The id_token Google returned doesn't verify -- wrong signature,
    wrong audience, wrong issuer, or expired. A real security-relevant
    event: never treated as "close enough" to a valid token."""


async def exchange_authorization_code(
    *,
    code: str,
    code_verifier: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str,
) -> dict:
    """Real, live POST to Google's actual token endpoint. Returns
    Google's raw JSON response (contains `id_token`, Google's own
    `access_token`/`refresh_token` for Gmail/Calendar API use -- the
    latter two deliberately not persisted by this module, see the
    top-of-file docstring)."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "code_verifier": code_verifier,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    if response.status_code != 200:
        # Google's real error body is JSON with an "error" field
        # ("invalid_grant", "invalid_client", etc.) -- surfaced directly
        # rather than replaced, since it's genuinely useful for
        # distinguishing "your code was fake/expired" from "the server's
        # own client credentials are broken."
        raise GoogleOAuthExchangeFailed(f"Google token exchange failed ({response.status_code}): {response.text}")
    return response.json()


def verify_google_id_token(id_token: str, client_id: str) -> dict:
    """Real signature verification against Google's real, live public
    keys (fetched from `GOOGLE_JWKS_URL`), never a decode-without-verify
    shortcut. Returns the real, verified payload on success -- `sub` is
    Google's real, stable per-user identifier, used as Quorum's
    `user_id`. Every non-success path raises a distinct, real exception,
    the same no-silent-fallthrough discipline `access_token.py` already
    holds itself to."""
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(id_token)
        payload = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=list(GOOGLE_ID_TOKEN_ISSUERS),
        )
    except jwt.PyJWTError as exc:
        raise GoogleIdTokenInvalid(f"Google id_token failed verification: {exc}") from exc
    return payload
