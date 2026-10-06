"""Real, live-database tests for features/connection_health.py
(`DEC-198`, product rebuild) -- backs `GET /connections`."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest_asyncio
from cryptography.fernet import Fernet

from quorum_backend.auth.google_oauth import GoogleOAuthExchangeFailed
from quorum_backend.auth.google_token_store import store_google_tokens
from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.features.connection_health import get_connection_health

_KEY = Fernet.generate_key().decode()


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-connection-health-{uuid.uuid4()}"
    uid = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield uid
    await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(uid))


async def test_no_grant_at_all_is_honestly_not_connected(pool, user_id):
    health = await get_connection_health(
        pool, internal_user_id=user_id, client_id="unused", client_secret="unused", encryption_key=_KEY
    )
    assert health.connected is False
    assert health.granted_scopes == []
    assert health.last_updated_at is None
    # Genuinely nothing to test a live refresh against -- `None`, not a
    # fabricated `False`, see this module's own top-of-file docstring.
    assert health.token_refreshable is None


async def test_a_real_far_from_expiry_grant_is_connected_and_refreshable_without_a_real_network_call(pool, user_id):
    await store_google_tokens(
        pool, internal_user_id=user_id, access_token="still-fresh", refresh_token="a-refresh-token",
        access_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        granted_scopes="openid email https://www.googleapis.com/auth/gmail.readonly", encryption_key=_KEY,
    )

    # client_id/client_secret are deliberately garbage -- if this test
    # ever actually reached a real refresh call, it would raise, proving
    # this exercises the no-refresh-needed path, same technique
    # `test_google_token_store.py` already established.
    health = await get_connection_health(
        pool, internal_user_id=user_id, client_id="unused", client_secret="unused", encryption_key=_KEY
    )
    assert health.connected is True
    assert health.granted_scopes == ["openid", "email", "https://www.googleapis.com/auth/gmail.readonly"]
    assert health.last_updated_at is not None
    assert health.token_refreshable is True


async def test_a_real_expired_grant_that_genuinely_refreshes_is_reported_refreshable(pool, user_id, monkeypatch):
    await store_google_tokens(
        pool, internal_user_id=user_id, access_token="expired-token", refresh_token="the-real-refresh-token",
        access_token_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        granted_scopes="openid", encryption_key=_KEY,
    )

    async def _fake_refresh(*, refresh_token, client_id, client_secret):
        return "freshly-refreshed-token", datetime.now(timezone.utc) + timedelta(hours=1)

    monkeypatch.setattr("quorum_backend.auth.google_token_store.refresh_google_access_token", _fake_refresh)

    health = await get_connection_health(
        pool, internal_user_id=user_id, client_id="a-client-id", client_secret="a-client-secret", encryption_key=_KEY
    )
    assert health.connected is True
    assert health.token_refreshable is True


async def test_a_real_revoked_grant_is_reported_connected_but_not_refreshable_never_crashing(pool, user_id, monkeypatch):
    """The real, direct answer to this rebuild's own sharpest named root
    cause: a real, revoked grant must surface as an honest, distinct
    signal a client can act on (`token_refreshable=False`), never as an
    unhandled exception and never collapsed into "not connected at all"
    -- the grant genuinely exists, it just can't be used right now."""
    await store_google_tokens(
        pool, internal_user_id=user_id, access_token="expired-token", refresh_token="a-revoked-refresh-token",
        access_token_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        granted_scopes="openid email", encryption_key=_KEY,
    )

    async def _fake_refresh_fails(*, refresh_token, client_id, client_secret):
        raise GoogleOAuthExchangeFailed("Google token refresh failed (400): invalid_grant")

    monkeypatch.setattr("quorum_backend.auth.google_token_store.refresh_google_access_token", _fake_refresh_fails)

    health = await get_connection_health(
        pool, internal_user_id=user_id, client_id="a-client-id", client_secret="a-client-secret", encryption_key=_KEY
    )
    assert health.connected is True
    assert health.granted_scopes == ["openid", "email"]
    assert health.token_refreshable is False
