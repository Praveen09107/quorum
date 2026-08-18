"""Real, live tests for auth/google_oauth.py -- every test here makes a
genuine network call to Google's real, live infrastructure (Rule 5: real
APIs, never mocked). Uses the same real, deliberately-invalid-input
technique already proven earlier in this project's history for
distinguishing "the server's own client credentials are broken"
(`invalid_client`) from "this specific code/token is fake"
(`invalid_grant` / a verification failure) -- confirming the real
credentials are genuinely wired through correctly, not just that some
error was raised.
"""
import pytest

from quorum_backend.auth.google_oauth import (
    GoogleIdTokenInvalid,
    GoogleOAuthExchangeFailed,
    exchange_authorization_code,
    verify_google_id_token,
)
from quorum_backend.core.config import get_settings


async def test_exchange_with_a_fake_code_fails_with_invalid_grant_not_invalid_client():
    # invalid_grant means Google recognized OUR real client credentials
    # and rejected only the fake code -- the real, meaningful proof that
    # GOOGLE_OAUTH_CLIENT_ID/SECRET are genuinely wired through, not that
    # the whole exchange is broken.
    settings = get_settings()
    with pytest.raises(GoogleOAuthExchangeFailed) as exc_info:
        await exchange_authorization_code(
            code="deliberately-fake-code-for-a-real-test",
            code_verifier="deliberately-fake-verifier",
            redirect_uri="https://example.com/callback",
            client_id=settings.google_oauth_client_id,
            client_secret=settings.google_oauth_client_secret,
        )
    assert "invalid_grant" in str(exc_info.value)
    assert "invalid_client" not in str(exc_info.value)


async def test_verify_id_token_rejects_a_malformed_token():
    settings = get_settings()
    with pytest.raises(GoogleIdTokenInvalid):
        verify_google_id_token("not.a.real.jwt", settings.google_oauth_client_id)


async def test_verify_id_token_rejects_a_well_formed_but_unsigned_token():
    # A syntactically real JWT (three real base64url segments) but never
    # actually signed by Google -- must still fail verification, proving
    # this isn't a shape-only check.
    import base64
    import json

    header = base64.urlsafe_b64encode(json.dumps({"alg": "RS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps({"sub": "fake-user", "iss": "https://accounts.google.com"}).encode()).rstrip(b"=").decode()
    fake_token = f"{header}.{payload}.fake-signature"

    settings = get_settings()
    with pytest.raises(GoogleIdTokenInvalid):
        verify_google_id_token(fake_token, settings.google_oauth_client_id)
