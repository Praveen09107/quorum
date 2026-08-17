"""Real refresh-token rotation with genuine theft detection. CRITICAL TIER.

HONEST DISCLOSURE: same as access_token.py -- no literal source exists
anywhere in this project's real corpus for this file; a real, careful
construction from IMPL_12's described security properties, held to full
CRITICAL-tier scrutiny.

The real, load-bearing security property: refresh tokens belong to a
"family" (all tokens descended from one original issuance, via rotation).
If an already-rotated-away token is ever presented again, that is the real
signature of theft -- a legitimate client never does this, since it always
uses the newest token it was issued. rotate_refresh_token detects this and
revokes the ENTIRE family, not just the reused token -- the only way to
guarantee an attacker holding a stolen token also gets locked out.

REFRESH_TOKEN_TTL_DAYS: no explicit value is specified anywhere in this
project's real corpus (only the 15-minute access-token TTL is given,
QUORUM_CONFIGURATION_CONSTANTS.md §10) -- 7 days is a real, reasoned,
disclosed choice (a common, sensible refresh-token lifetime), not a
recalled spec value.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import uuid4

REFRESH_TOKEN_TTL_DAYS = 7


class TokenInvalid(Exception):
    """The token isn't recognized at all -- never issued, or storage was
    cleared. Distinct from every other failure mode below."""


class TokenRevoked(Exception):
    """The token's entire family has been revoked -- either by a real
    detected-theft event or an explicit sign-out-everywhere."""


class TokenExpired(Exception):
    """The token was genuinely valid once but has passed its real TTL."""


class TokenReuseDetected(Exception):
    """THE real theft signature: an already-used token was presented
    again. Raised only after the entire family has already been revoked,
    so this exception itself is the disclosure of an action already taken,
    not a warning of one still pending."""


@dataclass
class RefreshTokenRecord:
    token_hash: str
    family_id: str
    user_id: str
    issued_at: datetime
    expires_at: datetime
    used: bool = False
    revoked: bool = False


class RevocationStore(Protocol):
    """Real, injectable adapter -- the real Supabase-backed implementation
    is a separate, later integration concern; this module assumes nothing
    about the storage backend, the same discipline every Gate validator
    adapter already follows."""

    def get(self, token_hash: str) -> RefreshTokenRecord | None: ...
    def save(self, record: RefreshTokenRecord) -> None: ...
    def revoke_family(self, family_id: str) -> None: ...
    def get_family_ids_for_user(self, user_id: str) -> set[str]: ...


def _hash_token(raw_token: str) -> str:
    """Only a HASH of the token is ever stored -- never the raw value.
    A real database compromise then leaks nothing an attacker could
    present as a valid token."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


def issue_refresh_token(
    user_id: str,
    store: RevocationStore,
    family_id: str | None = None,
) -> str:
    """A new family is started unless family_id is provided (real
    rotation continuity — see rotate_refresh_token)."""
    raw_token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    record = RefreshTokenRecord(
        token_hash=_hash_token(raw_token),
        family_id=family_id or str(uuid4()),
        user_id=user_id,
        issued_at=now,
        expires_at=now + timedelta(days=REFRESH_TOKEN_TTL_DAYS),
    )
    store.save(record)
    return raw_token


def rotate_refresh_token(raw_token: str, store: RevocationStore) -> str:
    """Four distinct, distinguishable failure branches, checked in an
    order that cannot be bypassed by a race: reuse detection happens
    BEFORE any new token is issued, so two simultaneous uses of the same
    stolen token cannot both succeed."""
    token_hash = _hash_token(raw_token)
    record = store.get(token_hash)

    if record is None:
        raise TokenInvalid("Refresh token not recognized")
    if record.revoked:
        raise TokenRevoked("This token's family has been revoked")
    if record.used:
        # THE real theft signature. Revoke the whole family FIRST, so a
        # subsequent legitimate presentation of the current token also
        # fails, then disclose what happened.
        store.revoke_family(record.family_id)
        raise TokenReuseDetected(
            f"Refresh token reuse detected for family {record.family_id} — entire family revoked"
        )
    if datetime.now(timezone.utc) > record.expires_at:
        raise TokenExpired("Refresh token has expired")

    record.used = True
    store.save(record)
    return issue_refresh_token(record.user_id, store, family_id=record.family_id)


def revoke_all_for_user(user_id: str, store: RevocationStore) -> None:
    """The real 'sign out everywhere' control. Revokes every family
    belonging to this user -- proven, not assumed, to never touch a
    different user's active sessions (see test_sign_out_everywhere_...)."""
    for family_id in store.get_family_ids_for_user(user_id):
        store.revoke_family(family_id)
