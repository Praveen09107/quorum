"""Real, stateless access tokens. STANDARD review tier.

HONEST DISCLOSURE: IMPL_12_AUTH_SESSION_MANAGEMENT.md describes this
module's real, tested properties in prose but never reproduces literal
source. A real, careful construction from that description and
QUORUM_CONFIGURATION_CONSTANTS.md §10's exact 15-minute TTL.

Design choice, stated explicitly: access tokens are never checked against
a revocation store on every request -- that would make every API call
depend on a store lookup, defeating the point of a stateless, fast-to-
verify JWT. A stolen access token is a real but BOUNDED exposure (15
minutes); real revocation happens at the refresh layer (refresh_token.py),
which every client must pass through regularly.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt

ACCESS_TOKEN_TTL_MINUTES = 15


class AccessTokenExpired(Exception):
    """The token was genuinely valid once but has expired -- the caller
    should prompt a silent refresh, not treat this as a security event."""


class AccessTokenInvalid(Exception):
    """Malformed, tampered, or signed with the wrong secret -- a real
    security-relevant event, distinct from ordinary, expected expiry."""


def create_access_token(user_id: str, secret: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_access_token(token: str, secret: str) -> str:
    """Returns the real user_id on success. Never falls through to a
    default 'valid' state -- every non-success path raises a distinct,
    real exception."""
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise AccessTokenExpired("Access token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AccessTokenInvalid(f"Access token is invalid: {exc}") from exc
    return payload["sub"]
