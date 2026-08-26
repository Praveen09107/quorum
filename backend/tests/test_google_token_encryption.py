"""Real tests for security/google_token_encryption.py."""
import pytest
from cryptography.fernet import Fernet

from quorum_backend.security.google_token_encryption import (
    GoogleTokenDecryptionFailed,
    decrypt_token,
    encrypt_token,
)

_KEY = Fernet.generate_key().decode()


def test_encrypt_then_decrypt_round_trips_to_the_real_original_value():
    raw = "a-real-looking-google-refresh-token-value"
    encrypted = encrypt_token(raw, encryption_key=_KEY)
    assert encrypted != raw  # genuinely encrypted, not a no-op
    assert decrypt_token(encrypted, encryption_key=_KEY) == raw


def test_the_same_real_plaintext_encrypts_to_a_different_ciphertext_each_time():
    # Fernet includes a real, random IV per encryption -- a real,
    # deliberate property, not a bug: two encryptions of the identical
    # real token must never produce identical ciphertext (which would
    # leak that two stored rows share a value).
    raw = "same-real-token"
    first = encrypt_token(raw, encryption_key=_KEY)
    second = encrypt_token(raw, encryption_key=_KEY)
    assert first != second
    assert decrypt_token(first, encryption_key=_KEY) == raw
    assert decrypt_token(second, encryption_key=_KEY) == raw


def test_decrypting_with_the_wrong_real_key_fails_loud_not_silent_garbage():
    encrypted = encrypt_token("a-real-secret", encryption_key=_KEY)
    wrong_key = Fernet.generate_key().decode()
    with pytest.raises(GoogleTokenDecryptionFailed):
        decrypt_token(encrypted, encryption_key=wrong_key)


def test_decrypting_a_genuinely_tampered_ciphertext_fails_loud():
    encrypted = encrypt_token("a-real-secret", encryption_key=_KEY)
    tampered = encrypted[:-4] + ("A" if encrypted[-4] != "A" else "B") + encrypted[-3:]
    with pytest.raises(GoogleTokenDecryptionFailed):
        decrypt_token(tampered, encryption_key=_KEY)
