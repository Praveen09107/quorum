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
