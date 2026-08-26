"""Real, application-level symmetric encryption for Google's own OAuth
tokens at rest (Phase 3, `QUORUM_PRODUCTION_COMPLETION_PLAN.md`) -- see
`migrations/0010_google_oauth_tokens/up.sql`'s own top comment for why
this lives here, at the application level, rather than via Postgres
`pgcrypto`'s own SQL-level `pgp_sym_encrypt`/`pgp_sym_decrypt`.

`cryptography.fernet.Fernet` provides real, authenticated symmetric
encryption (AES-128-CBC + HMAC-SHA256, versioned, with a real embedded
timestamp) -- already a real dependency of this backend (`cryptography`
in `pyproject.toml`, pulled in for `PyJWT`'s own RS256 support), not a
new library added just for this. A tampered or corrupted ciphertext
fails to decrypt loudly (`InvalidToken`) -- never silently returns
garbage plaintext that would then be sent to Google as a real, invalid
credential.
"""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken


class GoogleTokenDecryptionFailed(Exception):
    """Raised when a stored ciphertext fails to decrypt -- a genuinely
    corrupted row, a tampered value, or a real encryption-key rotation
    with no real migration path for rows encrypted under the old key.
    Never silently treated as an empty or missing token."""


def encrypt_token(raw_token: str, *, encryption_key: str) -> str:
    """`encryption_key` is the real, configured `GOOGLE_TOKEN_ENCRYPTION_
    KEY` value -- callers resolve it from `core/config.py::Settings`
    once, at the call site, and pass it explicitly here, the same
    resolve-in-the-route-then-pass-down convention every other real
    credential in this backend already follows (`settings.gemini_api_key`
    passed into `make_gemini_position_call`, not read from inside that
    factory)."""
    fernet = Fernet(encryption_key.encode())
    return fernet.encrypt(raw_token.encode()).decode()


def decrypt_token(encrypted_token: str, *, encryption_key: str) -> str:
    fernet = Fernet(encryption_key.encode())
    try:
        return fernet.decrypt(encrypted_token.encode()).decode()
    except InvalidToken as exc:
        raise GoogleTokenDecryptionFailed("Stored Google token ciphertext failed to decrypt") from exc
