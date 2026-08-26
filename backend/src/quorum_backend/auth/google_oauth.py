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

**RESOLVED, Phase 3 (`QUORUM_PRODUCTION_COMPLETION_PLAN.md`):** this
module's own docstring previously described a deliberately narrow scope
-- verifying identity only, never persisting Google's own access/
refresh tokens. That gap is now closed: `main.py`'s own `/auth/token`
route persists them (encrypted, `auth/google_token_store.py`) right
after this module's real exchange succeeds. This module's own real
job is unchanged -- the real network call to Google and the real
`id_token` verification -- storage is a genuinely separate concern,
layered on top here, not folded into this file. `revoke_google_token`
below is the one real addition: Google's own token-family lifecycle
(exchange, revoke) belongs together in one file even though storage
does not.
"""
from __future__ import annotations

import httpx
import jwt
from jwt import PyJWKClient

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
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


async def revoke_google_token(token: str) -> None:
    """Real, live POST to Google's actual revoke endpoint (Phase 3) --
    backs `security/supabase_deletion_store.py::revoke_oauth_tokens()`.
    Revoking either a real `access_token` or `refresh_token` works per
    Google's own documentation; callers here pass the `refresh_token`
    specifically, since revoking it also invalidates every real
    `access_token` issued under it -- one real call closes the entire
    real grant, not just its current, possibly-already-expired half.

    A REAL, DISCLOSED FIX (this PR's own CRITICAL-tier review): an
    earlier version treated EVERY real `400` as the benign "already
    invalid or previously revoked" case. Live probing of Google's real
    `/revoke` endpoint found `400` genuinely covers TWO different real
    errors, distinguishable only by the response body's own `error`
    field -- `"invalid_token"` (Google looked at the token and it's
    genuinely already dead -- the real, intended benign case) versus
    `"invalid_request"` (Google never evaluated a token at all -- an
    empty/missing/malformed real request, which a real, undetected bug
    in how this function builds its own POST body could produce just as
    easily as a caller passing bad real input). Live-proven the
    difference is consequential, not academic: treating a real
    `invalid_request` as benign would let `revoke_oauth_tokens()` delete
    the real local token row while the real external Google grant (live
    `gmail.send`/`gmail.modify`/`calendar.events` access) was NEVER
    actually revoked -- exactly the plausible-looking-but-false success
    this project's own "honest count, never a fabricated one" discipline
    exists to prevent, on a real, S3-equivalent irreversible path. Only
    a real, confirmed `invalid_token` is now treated as benign."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(GOOGLE_REVOKE_URL, data={"token": token})
    if response.status_code == 200:
        return
    if response.status_code == 400:
        try:
            error = response.json().get("error")
        except ValueError:
            error = None
        if error == "invalid_token":
            return
    raise GoogleOAuthExchangeFailed(f"Google token revocation failed ({response.status_code}): {response.text}")


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
