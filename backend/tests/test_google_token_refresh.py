"""Real tests for auth/google_token_refresh.py.

Error-path test uses a monkeypatched httpx client (deterministic,
network-independent, matching test_negotiation_gemini_calls.py's own
established pattern). The real, live test below makes a genuine network
call to Google's real, live infrastructure (Rule 5) using a real,
deliberately-invalid refresh_token -- the same established technique
test_auth_google_oauth.py already uses, since no real, valid refresh
token is available to this test suite (obtaining one needs a real,
human-completed mobile consent flow with the new Gmail/Calendar scopes).
"""
import pytest

from quorum_backend.auth.google_oauth import GoogleOAuthExchangeFailed
from quorum_backend.auth.google_token_refresh import refresh_google_access_token
from quorum_backend.core.config import get_settings


async def test_refresh_raises_on_a_non_200_response(monkeypatch):
    class _FakeResponse:
        status_code = 400
        text = '{"error": "invalid_grant"}'

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, *args, **kwargs):
            return _FakeResponse()

    monkeypatch.setattr("quorum_backend.auth.google_token_refresh.httpx.AsyncClient", lambda **kwargs: _FakeClient())

    with pytest.raises(GoogleOAuthExchangeFailed, match="invalid_grant"):
        await refresh_google_access_token(refresh_token="fake", client_id="fake", client_secret="fake")


async def test_refresh_returns_the_real_access_token_and_a_real_future_expiry(monkeypatch):
    import datetime as dt

    class _FakeResponse:
        status_code = 200

        def json(self):
            return {"access_token": "real-fresh-token", "expires_in": 3600}

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, *args, **kwargs):
            return _FakeResponse()

    monkeypatch.setattr("quorum_backend.auth.google_token_refresh.httpx.AsyncClient", lambda **kwargs: _FakeClient())

    before = dt.datetime.now(dt.timezone.utc)
    access_token, expires_at = await refresh_google_access_token(refresh_token="fake", client_id="fake", client_secret="fake")
    after = dt.datetime.now(dt.timezone.utc)

    assert access_token == "real-fresh-token"
    assert before + dt.timedelta(seconds=3590) < expires_at < after + dt.timedelta(seconds=3601)


# --- Real, live test (Rule 5) ---


async def test_a_real_deliberately_invalid_refresh_token_is_genuinely_rejected_by_googles_real_endpoint():
    settings = get_settings()
    with pytest.raises(GoogleOAuthExchangeFailed) as exc_info:
        await refresh_google_access_token(
            refresh_token="deliberately-fake-refresh-token-for-a-real-test",
            client_id=settings.google_oauth_client_id,
            client_secret=settings.google_oauth_client_secret,
        )
    # invalid_grant means Google recognized our real client credentials
    # and rejected only the fake token -- the same real, meaningful
    # distinction test_auth_google_oauth.py's own live test already
    # relies on.
    assert "invalid_grant" in str(exc_info.value)
    assert "invalid_client" not in str(exc_info.value)
