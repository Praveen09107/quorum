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

Batch 10 Phase 3, TWO real, disclosed changes to this already-reviewed
CRITICAL-tier module, made when this module's own storage layer finally
became real (IMPL_12's docstring named this "a separate, later
integration concern" -- this is that moment):

1. `RevocationStore` and every function here are now `async`. The real
   storage backend (`auth/revocation_store.py`, new) is `asyncpg`-backed,
   and a synchronous DB call from inside this codebase's async FastAPI
   app would block the whole event loop -- a real problem, not a style
   preference, given Cloud Run's own `--concurrency=1` means one blocked
   request stalls everything else that container instance would otherwise
   serve. Every internal check/branch/exception is unchanged; only the
   calling convention changed.

2. A NEW `try_claim()` method closes a real race this module's original
   two-call `get()` then `save()` pattern left open: `--max-instances=2`
   means two real, separate container instances can genuinely process two
   requests concurrently. Two concurrent presentations of the same stolen
   token could both call `get()`, both see `used=False` (the race window
   between the read and the write), and both "successfully" rotate --
   silently defeating the exact theft detection this module exists to
   provide. `try_claim()` performs the read-and-mark-used step as a single
   atomic database operation; only the first of two racing callers can
   ever succeed. `rotate_refresh_token`'s exception behavior is completely
   unchanged from the caller's perspective -- `try_claim()` returning
   `False` is treated exactly like the pre-existing `record.used` branch,
   just now genuinely race-safe rather than only correct in the common,
   non-concurrent case.
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
    """Real, injectable adapter -- `auth/revocation_store.py` is the real
    Supabase-backed implementation; `FakeStore` in this module's own tests
    is the in-memory one. Nothing in `rotate_refresh_token`/
    `issue_refresh_token`/`revoke_all_for_user` assumes a specific storage
    backend, the same discipline every Gate validator adapter follows."""

    async def get(self, token_hash: str) -> RefreshTokenRecord | None: ...
    async def save(self, record: RefreshTokenRecord) -> None: ...
    async def try_claim(self, token_hash: str) -> bool:
        """Atomically marks the record `used=True` IF AND ONLY IF it is
        currently `used=False`. Returns whether THIS call was the one to
        claim it -- `False` means a concurrent caller (or an earlier real
        presentation) already claimed it first. The real race-safety
        guarantee this module depends on lives entirely in this one
        method being genuinely atomic in the concrete implementation."""
        ...
    async def revoke_family(self, family_id: str) -> None: ...
    async def get_family_ids_for_user(self, user_id: str) -> set[str]: ...


def hash_token(raw_token: str) -> str:
    """Only a HASH of the token is ever stored -- never the raw value.
    A real database compromise then leaks nothing an attacker could
    present as a valid token."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


async def issue_refresh_token(
    user_id: str,
    store: RevocationStore,
    family_id: str | None = None,
) -> str:
    """A new family is started unless family_id is provided (real
    rotation continuity — see rotate_refresh_token)."""
    raw_token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    record = RefreshTokenRecord(
        token_hash=hash_token(raw_token),
        family_id=family_id or str(uuid4()),
        user_id=user_id,
        issued_at=now,
        expires_at=now + timedelta(days=REFRESH_TOKEN_TTL_DAYS),
    )
    await store.save(record)
    return raw_token


async def rotate_refresh_token(raw_token: str, store: RevocationStore) -> str:
    """Real, distinguishable failure branches, checked in an order that
    cannot be bypassed by a race: the initial `record.used` check below
    catches the common, non-concurrent reuse case cheaply (no atomic
    operation needed when the answer is already obviously "yes, reused"),
    but the real, load-bearing guarantee against a genuine concurrent
    race is `try_claim()` -- see this module's own top-of-file docstring
    for why a second atomic step is necessary at all.
    """
    token_hash = hash_token(raw_token)
    record = await store.get(token_hash)

    if record is None:
        raise TokenInvalid("Refresh token not recognized")
    if record.revoked:
        raise TokenRevoked("This token's family has been revoked")
    if record.used:
        # THE real theft signature, the common (non-racing) case. Revoke
        # the whole family FIRST, so a subsequent legitimate presentation
        # of the current token also fails, then disclose what happened.
        await store.revoke_family(record.family_id)
        raise TokenReuseDetected(
            f"Refresh token reuse detected for family {record.family_id} — entire family revoked"
        )
    if datetime.now(timezone.utc) > record.expires_at:
        raise TokenExpired("Refresh token has expired")

    # The real, race-safe guard: only the first of any concurrently racing
    # callers can win this atomic claim. A loser here is the exact same
    # real theft signature as the record.used branch above, just caught
    # under genuine concurrency rather than only in the common case.
    claimed = await store.try_claim(token_hash)
    if not claimed:
        await store.revoke_family(record.family_id)
        raise TokenReuseDetected(
            f"Refresh token reuse detected for family {record.family_id} (concurrent claim) — entire family revoked"
        )

    return await issue_refresh_token(record.user_id, store, family_id=record.family_id)


async def revoke_all_for_user(user_id: str, store: RevocationStore) -> None:
    """The real 'sign out everywhere' control. Revokes every family
    belonging to this user -- proven, not assumed, to never touch a
    different user's active sessions (see test_sign_out_everywhere_...)."""
    for family_id in await store.get_family_ids_for_user(user_id):
        await store.revoke_family(family_id)
