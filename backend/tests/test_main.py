"""Real tests for main.py -- confirms core/config.py is genuinely
consumed at real app startup, not just an unreferenced file."""
import logging

from fastapi.testclient import TestClient

from quorum_backend.core.config import get_settings
from quorum_backend.main import app


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


def test_trust_digest_endpoint_is_real_and_live_not_mocked():
    """Real, end-to-end: the real lifespan creates a real DB pool
    against the real, live Supabase database (DEC-098), and this
    request genuinely round-trips through it. Asserts shape and types
    only, never specific counts -- real production data changes as this
    project actually gets used, so a value-based assertion here would be
    the exact kind of stale, restated number CLAUDE.md's own drift
    patterns warn against."""
    with TestClient(app) as client:
        response = client.get("/trust_digest")

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
            digest_response = client.get("/trust_digest")
            health_response = client.get("/health")
            assert digest_response.status_code == 503
            assert health_response.status_code == 200
        finally:
            app.state.db_pool = real_pool
