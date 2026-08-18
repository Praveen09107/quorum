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

Batch 10 Phase 3, real, disclosed changes to this already-reviewed
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

2. `claim_and_rotate()` -- a real fix for a real, CONFIRMED-EXPLOITABLE
   race, found by fresh-context review of an earlier version of this
   same session's own work, not assumed safe from a partial fix. That
   earlier version added a `try_claim()` step that correctly made
   marking the OLD token used atomic -- but the race winner's brand-new
   child token was still issued as a fully separate, later `INSERT`,
   with no ordering guarantee against the race LOSER's `revoke_family()`
   `UPDATE`. If the loser's revoke ran before the winner's insert
   landed, the winner walked away with a live, unrevoked session inside
   a family the system believed it had just fully burned -- the exact
   failure mode this whole module exists to prevent, empirically
   reproduced by the reviewing agent, not theoretical.

   The real fix: `claim_and_rotate()` performs the ENTIRE
   read-lock-check-mark-and-insert sequence as one atomic database
   transaction, using `SELECT ... FOR UPDATE` on the OLD token's row to
   serialize any concurrent attempt to rotate that SAME token -- not
   just the used-flag write, the new row's insertion too. A second,
   concurrently racing call attempting the same lock genuinely BLOCKS at
   the database level until the first transaction (including its
   `INSERT` of the new child) has fully committed. Only once unblocked
   does the loser observe `used=True` and call `revoke_family()` -- by
   which point the winner's new child row is already committed and
   visible, so `revoke_family()` correctly catches and revokes it too.
   Proven by `test_the_race_winners_new_child_token_is_genuinely_left_
   unusable_after_the_loser_detects_reuse` -- the exact postcondition
   the earlier, incomplete fix's own test never actually checked.
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
    async def claim_and_rotate(self, old_token_hash: str, new_record: RefreshTokenRecord) -> bool:
        """THE real, atomic heart of rotation -- everything from
        confirming the old token is still unused through inserting its
        replacement happens as ONE database transaction, so a
        concurrently racing caller trying to rotate the SAME old token
        genuinely blocks at the database level until this entire
        operation -- old-token claim AND new-record insertion together
        -- has fully committed. Returns whether THIS call was the one to
        claim it: `False` means a concurrent caller (or an earlier real
        presentation) already claimed and rotated it first, and by the
        time that's observable, that caller's new child record is
        already committed and visible -- safe for the caller here to
        find and revoke via `revoke_family()`."""
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
    """Real, distinguishable failure branches. `get()` below is a cheap,
    non-locking PRE-check only -- it catches the common, unambiguous
    cases (unknown token, already-revoked family, expired token) without
    taking a real database lock for a request that's going to fail
    regardless of any race. It deliberately does NOT make the reuse
    decision -- a `record.used` check here would itself be racy and
    meaningless, which is exactly the bug an earlier version of this
    same function had. The real, load-bearing, race-safe decision is
    `claim_and_rotate()` alone -- see this module's own top-of-file
    docstring for why the old-token claim and the new-token insertion
    must happen inside the SAME atomic operation, not two separate ones.
    """
    token_hash = hash_token(raw_token)
    record = await store.get(token_hash)

    if record is None:
        raise TokenInvalid("Refresh token not recognized")
    if record.revoked:
        raise TokenRevoked("This token's family has been revoked")
    if datetime.now(timezone.utc) > record.expires_at:
        raise TokenExpired("Refresh token has expired")

    # Prepared BEFORE the atomic claim, but only ever persisted (and only
    # ever returned to the caller) if claim_and_rotate() reports a real
    # win below -- a prepared-but-never-claimed new_record simply never
    # touches the database at all, no cleanup needed.
    raw_new_token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    new_record = RefreshTokenRecord(
        token_hash=hash_token(raw_new_token),
        family_id=record.family_id,
        user_id=record.user_id,
        issued_at=now,
        expires_at=now + timedelta(days=REFRESH_TOKEN_TTL_DAYS),
    )

    claimed = await store.claim_and_rotate(token_hash, new_record)
    if not claimed:
        # THE real theft signature -- reached either because this was an
        # ordinary (non-racing) reuse, or because this call lost a
        # genuine concurrent race. Either way, by the time claim_and_
        # rotate() returns False, any real winner's new child record is
        # already committed and visible, so revoke_family() here is
        # guaranteed to catch it too -- the exact property the earlier,
        # incomplete fix was missing.
        await store.revoke_family(record.family_id)
        raise TokenReuseDetected(
            f"Refresh token reuse detected for family {record.family_id} — entire family revoked"
        )

    return raw_new_token


async def revoke_all_for_user(user_id: str, store: RevocationStore) -> None:
    """The real 'sign out everywhere' control. Revokes every family
    belonging to this user -- proven, not assumed, to never touch a
    different user's active sessions (see test_sign_out_everywhere_...)."""
    for family_id in await store.get_family_ids_for_user(user_id):
        await store.revoke_family(family_id)
