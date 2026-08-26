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
    revoke_google_token,
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


async def test_revoking_a_real_deliberately_invalid_but_well_formed_token_is_a_real_benign_no_op():
    """Phase 3. Google's real `/revoke` endpoint answers a real,
    well-formed-but-unrecognized token with a real `400` and
    `{"error": "invalid_token"}` -- `revoke_google_token()`'s own
    documented design treats specifically THAT real error as benign
    (the real end state, no live grant for this token, is identical to
    a successful real revocation), so this call must complete without
    raising."""
    await revoke_google_token("deliberately-fake-token-for-a-real-test")


async def test_revoking_an_empty_token_is_a_real_invalid_request_and_must_raise():
    """A REAL, DISCLOSED CORRECTION to this test's own former name and
    assertion, found by this PR's own CRITICAL-tier review: an earlier
    version of this test asserted an empty token must NOT raise,
    enshrining the wrong real behavior. Google's real `/revoke` endpoint
    answers a genuinely empty token with `400` and `{"error":
    "invalid_request", "error_description": "Bad Request"}` -- a
    GENUINELY DIFFERENT real error than `invalid_token`: Google never
    evaluated a real token at all, so this can never be treated as "the
    grant is already gone." `revoke_google_token()` must raise here,
    not silently report a real revocation that never happened."""
    with pytest.raises(GoogleOAuthExchangeFailed, match="invalid_request"):
        await revoke_google_token("")
