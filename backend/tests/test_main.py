"""Real tests for main.py -- confirms core/config.py is genuinely
consumed at real app startup, not just an unreferenced file, and (Batch
10 Phase 3) that the real auth routes and the real Bearer-auth gate on
/trust_digest genuinely work end to end against the real, live database.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest_asyncio
from fastapi.testclient import TestClient

from quorum_backend.auth.access_token import create_access_token
from quorum_backend.auth.refresh_token import TokenRevoked, issue_refresh_token, rotate_refresh_token
from quorum_backend.auth.revocation_store import SupabaseRevocationStore
from quorum_backend.core import db
from quorum_backend.core.config import get_settings
from quorum_backend.main import app

import pytest


def _auth_header() -> dict[str, str]:
    """A real, valid access token, created directly via the real
    create_access_token() -- bypasses the real Google login flow
    (which needs a live browser this environment doesn't have), while
    still exercising the real signing key and the real decode path on
    the receiving end."""
    settings = get_settings()
    token = create_access_token("test-user-" + str(uuid.uuid4()), settings.jwt_signing_key)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


def test_health_endpoint_still_works():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_real_startup_warns_when_the_insecure_default_jwt_key_is_still_active(monkeypatch, caplog):
    monkeypatch.delenv("JWT_SIGNING_KEY", raising=False)
    get_settings.cache_clear()

    with caplog.at_level(logging.WARNING, logger="quorum_backend"):
        with TestClient(app):
            pass  # entering the context manager runs the real lifespan startup

    assert any("insecure default" in record.message.lower() for record in caplog.records)
    get_settings.cache_clear()


def test_real_startup_does_not_warn_once_a_real_secret_is_configured(monkeypatch, caplog):
    monkeypatch.setenv("JWT_SIGNING_KEY", "a-real-generated-production-secret")
    get_settings.cache_clear()

    with caplog.at_level(logging.WARNING, logger="quorum_backend"):
        with TestClient(app):
            pass

    assert not any("insecure default" in record.message.lower() for record in caplog.records)
    get_settings.cache_clear()


def test_trust_digest_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.get("/trust_digest")
    assert response.status_code == 401


def test_trust_digest_rejects_a_malformed_authorization_header():
    with TestClient(app) as client:
        response = client.get("/trust_digest", headers={"Authorization": "not-a-bearer-token"})
    assert response.status_code == 401


def test_trust_digest_rejects_a_real_but_expired_access_token():
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expired_token = jwt.encode(
        {"sub": "test-user", "iat": now - timedelta(minutes=30), "exp": now - timedelta(minutes=15)},
        settings.jwt_signing_key,
        algorithm="HS256",
    )
    with TestClient(app) as client:
        response = client.get("/trust_digest", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


def test_trust_digest_endpoint_is_real_and_live_not_mocked_with_a_real_valid_token():
    """Real, end-to-end: the real lifespan creates a real DB pool
    against the real, live Supabase database (DEC-098), and this
    request genuinely round-trips through it once a real, valid access
    token is presented. Asserts shape and types only, never specific
    counts -- real production data changes as this project actually
    gets used, and a value-based assertion here would be exactly the
    stale-restated-number drift pattern CLAUDE.md warns against."""
    with TestClient(app) as client:
        response = client.get("/trust_digest", headers=_auth_header())

    assert response.status_code == 200
    body = response.json()

    assert set(body.keys()) == {"current_week", "previous_week", "trend", "delta"}
    assert body["trend"] in {"improving", "declining", "stable", "insufficient_data"}

    current = body["current_week"]
    assert set(current.keys()) == {"week_start", "total_actions", "success_rate"}
    assert isinstance(current["total_actions"], int)
    assert isinstance(current["success_rate"], float)

    if body["previous_week"] is not None:
        assert set(body["previous_week"].keys()) == {"week_start", "total_actions", "success_rate"}


def test_trust_digest_returns_503_not_a_crash_when_the_real_pool_is_unavailable():
    """Proves /health's own independence from database reachability
    (the real reasoning documented in main.py's lifespan): simulates a
    real startup-failure state by clearing the real pool reference
    after a genuine successful startup, confirms the endpoint that
    needs it fails loud with a real 503 rather than a raw exception,
    and that /health is entirely unaffected.

    A plain try/finally, not `monkeypatch`, restores the real pool
    reference deliberately: it must happen BEFORE the `with TestClient`
    block exits, since exiting runs the real lifespan shutdown, which
    closes whatever `app.state.db_pool` currently is -- `monkeypatch`'s
    own teardown only runs after that point, which would leave the
    real pool this fixture created never actually closed.
    """
    with TestClient(app) as client:
        real_pool = app.state.db_pool
        app.state.db_pool = None
        try:
            digest_response = client.get("/trust_digest", headers=_auth_header())
            health_response = client.get("/health")
            assert digest_response.status_code == 503
            assert health_response.status_code == 200
        finally:
            app.state.db_pool = real_pool


def test_auth_token_with_a_fake_code_fails_loud_with_a_real_400():
    # A full real round-trip needs a live browser completing Google's
    # real consent screen -- not available in this environment. This
    # proves the route's real, live path to Google (client credentials
    # genuinely wired through, per the invalid_grant-not-invalid_client
    # distinction already proven directly against google_oauth.py) and
    # its real error handling, the furthest this environment can verify
    # /auth/token without a human in a browser.
    with TestClient(app) as client:
        response = client.post(
            "/auth/token",
            json={
                "code": "deliberately-fake-code-for-a-real-test",
                "code_verifier": "deliberately-fake-verifier",
                "redirect_uri": "https://example.com/callback",
            },
        )
    assert response.status_code == 400
    assert "invalid_grant" in response.json()["detail"]


async def test_auth_refresh_genuinely_rotates_a_real_token_against_the_real_database(pool):
    store = SupabaseRevocationStore(pool)
    user_id = f"test-user-{uuid.uuid4()}"
    raw_refresh = await issue_refresh_token(user_id, store)

    try:
        with TestClient(app) as client:
            response = client.post("/auth/refresh", json={"refresh_token": raw_refresh})

        assert response.status_code == 200
        body = response.json()
        assert body["refresh_token"] != raw_refresh
        assert body["token_type"] == "bearer"
        assert isinstance(body["access_token"], str)
        assert len(body["access_token"]) > 0

        # The real theft-detection property, exercised through the real
        # HTTP route: presenting the OLD, now-rotated-away token again
        # must fail as real reuse, not silently succeed a second time.
        with TestClient(app) as client:
            reuse_response = client.post("/auth/refresh", json={"refresh_token": raw_refresh})
        assert reuse_response.status_code == 401
    finally:
        await pool.execute("DELETE FROM refresh_tokens WHERE user_id = $1", user_id)


async def test_auth_refresh_with_an_unknown_token_is_a_real_401():
    with TestClient(app) as client:
        response = client.post("/auth/refresh", json={"refresh_token": "a-token-that-was-never-issued"})
    assert response.status_code == 401


async def test_auth_revoke_requires_real_auth():
    with TestClient(app) as client:
        response = client.post("/auth/revoke")
    assert response.status_code == 401


async def test_auth_revoke_genuinely_signs_out_every_real_session_for_that_user(pool):
    store = SupabaseRevocationStore(pool)
    user_id = f"test-user-{uuid.uuid4()}"
    raw_refresh = await issue_refresh_token(user_id, store)
    settings = get_settings()
    access_token = create_access_token(user_id, settings.jwt_signing_key)

    try:
        with TestClient(app) as client:
            response = client.post("/auth/revoke", headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 204

        # The real, live proof: the session issued before revocation no
        # longer rotates -- genuinely revoked in the real database, not
        # just a 204 returned without real effect.
        with pytest.raises(TokenRevoked):
            await rotate_refresh_token(raw_refresh, store)
    finally:
        await pool.execute("DELETE FROM refresh_tokens WHERE user_id = $1", user_id)
