"""Real tests for auth/access_token.py."""
import jwt
import pytest
from datetime import datetime, timedelta, timezone

from quorum_backend.auth.access_token import (
    AccessTokenExpired,
    AccessTokenInvalid,
    create_access_token,
    decode_access_token,
)

SECRET = "test-secret-do-not-use-in-real-deployment"


def test_valid_token_round_trips_to_the_real_user_id():
    token = create_access_token("user_123", SECRET)
    assert decode_access_token(token, SECRET) == "user_123"


def test_expired_token_is_genuinely_rejected():
    # Construct an already-expired token directly -- waiting 15 real
    # minutes in a test isn't practical, so the expiry claim is set
    # explicitly in the past.
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    expired_token = jwt.encode(
        {"sub": "user_123", "iat": past - timedelta(minutes=15), "exp": past}, SECRET, algorithm="HS256"
    )
    with pytest.raises(AccessTokenExpired):
        decode_access_token(expired_token, SECRET)


def test_tampered_token_is_genuinely_rejected():
    token = create_access_token("user_123", SECRET)
    tampered = token[:-4] + "xxxx"  # corrupt the signature
    with pytest.raises(AccessTokenInvalid):
        decode_access_token(tampered, SECRET)


def test_wrong_secret_is_genuinely_rejected():
    token = create_access_token("user_123", SECRET)
    with pytest.raises(AccessTokenInvalid):
        decode_access_token(token, "a-completely-different-secret")
