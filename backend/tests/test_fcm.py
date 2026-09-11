"""Real tests for features/fcm.py (`DEC-176`) -- QUORUM_FINAL_COMPLETION_
PLAN.md Session 9's real Firebase Cloud Messaging integration.

Every test here is deterministic and network-independent, using a
monkeypatched httpx client -- matching `test_gate_llm_calls.py`'s own
established pattern for exactly this class of test. No real, live test
section exists in this file (unlike `test_gate_llm_calls.py`'s Groq/
Gemini calls) because no real Firebase project exists anywhere in this
project's real history yet -- see `fcm.py`'s own top-of-file docstring
for the full, disclosed account. The real JWT-building logic IS tested
against a real, test-generated RSA key pair below, though -- that part
needs no real Firebase project at all, only a real, valid private key
shape, which a test can legitimately generate itself."""
import json
import time

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from quorum_backend.features.fcm import (
    FcmError,
    FcmNotConfiguredError,
    _build_service_account_jwt,
    _parse_service_account,
    get_fcm_access_token,
    send_briefing_notification,
    send_fcm_notification,
)


class _FakeResponse:
    def __init__(self, status_code: int, json_body: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json_body = json_body
        self.text = text

    def json(self):
        if self._json_body is None:
            raise ValueError("no real JSON body configured for this fake response")
        return self._json_body


def _real_test_rsa_keypair() -> tuple[str, str]:
    """A real, freshly-generated RSA key pair, PEM-encoded -- legitimate
    for testing this module's own real JWT-signing logic, since that
    logic only needs a real, valid private key SHAPE, never a real
    Firebase project's actual key."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private_pem, public_pem


def _real_service_account_json(private_key_pem: str) -> str:
    return json.dumps({
        "type": "service_account",
        "project_id": "quorum-test-project",
        "private_key": private_key_pem,
        "client_email": "quorum-test@quorum-test-project.iam.gserviceaccount.com",
    })


# --- _parse_service_account / _build_service_account_jwt ---


def test_parse_service_account_rejects_malformed_json():
    with pytest.raises(FcmError, match="not real, valid JSON"):
        _parse_service_account("not real json")


def test_parse_service_account_rejects_a_real_json_array_not_an_object():
    with pytest.raises(FcmError, match="real JSON object"):
        _parse_service_account("[1, 2, 3]")


def test_parse_service_account_rejects_missing_client_email():
    with pytest.raises(FcmError, match="client_email"):
        _parse_service_account(json.dumps({"private_key": "x"}))


def test_parse_service_account_rejects_missing_private_key():
    with pytest.raises(FcmError, match="private_key"):
        _parse_service_account(json.dumps({"client_email": "x@y.com"}))


def test_build_service_account_jwt_produces_a_real_verifiable_rs256_token():
    private_pem, public_pem = _real_test_rsa_keypair()
    service_account = {"client_email": "quorum-test@quorum-test-project.iam.gserviceaccount.com", "private_key": private_pem}
    now = int(time.time())

    token = _build_service_account_jwt(service_account, now=now)

    # Real, direct verification against the matching real public key --
    # not just "it produced a string."
    decoded = jwt.decode(token, public_pem, algorithms=["RS256"], audience="https://oauth2.googleapis.com/token")
    assert decoded["iss"] == service_account["client_email"]
    assert decoded["scope"] == "https://www.googleapis.com/auth/firebase.messaging"
    assert decoded["aud"] == "https://oauth2.googleapis.com/token"
    assert decoded["iat"] == now
    assert decoded["exp"] == now + 3600


# --- get_fcm_access_token ---


async def test_get_fcm_access_token_returns_the_real_token_on_a_real_200(monkeypatch):
    private_pem, _ = _real_test_rsa_keypair()
    service_account_json = _real_service_account_json(private_pem)

    async def fake_post(self, url, data=None, **kwargs):
        assert url == "https://oauth2.googleapis.com/token"
        assert data["grant_type"] == "urn:ietf:params:oauth:grant-type:jwt-bearer"
        return _FakeResponse(200, json_body={"access_token": "real-fake-access-token", "expires_in": 3600})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    token = await get_fcm_access_token(service_account_json=service_account_json)
    assert token == "real-fake-access-token"


async def test_get_fcm_access_token_raises_after_real_retries_exhausted_on_a_persistent_non_200(monkeypatch):
    private_pem, _ = _real_test_rsa_keypair()
    service_account_json = _real_service_account_json(private_pem)
    call_count = 0

    async def fake_post(self, url, data=None, **kwargs):
        nonlocal call_count
        call_count += 1
        return _FakeResponse(401, text="invalid_grant")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(FcmError):
        await get_fcm_access_token(service_account_json=service_account_json, retry_delay_seconds=0)
    assert call_count == 2  # max_retries default


async def test_get_fcm_access_token_raises_on_a_real_200_missing_access_token(monkeypatch):
    private_pem, _ = _real_test_rsa_keypair()
    service_account_json = _real_service_account_json(private_pem)

    async def fake_post(self, url, data=None, **kwargs):
        return _FakeResponse(200, json_body={"expires_in": 3600})  # no access_token

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(FcmError, match="access_token"):
        await get_fcm_access_token(service_account_json=service_account_json, retry_delay_seconds=0)


async def test_get_fcm_access_token_rejects_malformed_service_account_before_any_real_network_call(monkeypatch):
    call_count = 0

    async def fake_post(self, url, data=None, **kwargs):
        nonlocal call_count
        call_count += 1
        return _FakeResponse(200, json_body={"access_token": "should never be reached"})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(FcmError):
        await get_fcm_access_token(service_account_json="not real json")
    assert call_count == 0


# --- send_fcm_notification ---


async def test_send_fcm_notification_succeeds_cleanly_on_a_real_200(monkeypatch):
    captured_body = None

    async def fake_post(self, url, headers=None, json=None):
        nonlocal captured_body
        captured_body = json
        assert url == "https://fcm.googleapis.com/v1/projects/quorum-test-project/messages:send"
        assert headers["Authorization"] == "Bearer real-fake-token"
        return _FakeResponse(200, json_body={"name": "real-fake-message-id"})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    await send_fcm_notification(
        project_id="quorum-test-project",
        access_token="real-fake-token",
        device_token="real-fake-device-token",
        title="Today",
        body="You have 2 things needing you.",
    )

    assert captured_body["message"]["token"] == "real-fake-device-token"
    assert captured_body["message"]["notification"] == {"title": "Today", "body": "You have 2 things needing you."}
    assert "data" not in captured_body["message"]


async def test_send_fcm_notification_includes_the_real_data_payload_when_given(monkeypatch):
    captured_body = None

    async def fake_post(self, url, headers=None, json=None):
        nonlocal captured_body
        captured_body = json
        return _FakeResponse(200, json_body={"name": "real-fake-message-id"})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    await send_fcm_notification(
        project_id="quorum-test-project",
        access_token="real-fake-token",
        device_token="real-fake-device-token",
        title="Today",
        body="You have 2 things needing you.",
        data={"deep_link": "today"},
    )

    assert captured_body["message"]["data"] == {"deep_link": "today"}


async def test_send_fcm_notification_raises_after_real_retries_exhausted(monkeypatch):
    call_count = 0

    async def fake_post(self, url, headers=None, json=None):
        nonlocal call_count
        call_count += 1
        return _FakeResponse(404, text="registration-token-not-registered")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(FcmError):
        await send_fcm_notification(
            project_id="quorum-test-project",
            access_token="real-fake-token",
            device_token="a-real-but-unregistered-device-token",
            title="Today",
            body="x",
            retry_delay_seconds=0,
        )
    assert call_count == 2


# --- send_briefing_notification ---


async def test_send_briefing_notification_raises_fcm_not_configured_before_any_real_network_call_when_project_id_missing(monkeypatch):
    call_count = 0

    async def fake_post(self, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        return _FakeResponse(200, json_body={})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(FcmNotConfiguredError):
        await send_briefing_notification(
            project_id=None,
            service_account_json="{}",
            access_token="x",
            device_token="x",
            title="x",
            body="x",
        )
    assert call_count == 0


async def test_send_briefing_notification_raises_fcm_not_configured_when_service_account_json_missing(monkeypatch):
    call_count = 0

    async def fake_post(self, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        return _FakeResponse(200, json_body={})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(FcmNotConfiguredError):
        await send_briefing_notification(
            project_id="quorum-test-project",
            service_account_json=None,
            access_token="x",
            device_token="x",
            title="x",
            body="x",
        )
    assert call_count == 0


async def test_send_briefing_notification_sends_for_real_when_genuinely_configured(monkeypatch):
    captured_body = None

    async def fake_post(self, url, headers=None, json=None):
        nonlocal captured_body
        captured_body = json
        return _FakeResponse(200, json_body={"name": "real-fake-message-id"})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    await send_briefing_notification(
        project_id="quorum-test-project",
        service_account_json="{}",
        access_token="real-fake-token",
        device_token="real-fake-device-token",
        title="Today",
        body="You have 2 things needing you.",
        data={"deep_link": "today"},
    )

    assert captured_body["message"]["token"] == "real-fake-device-token"
    assert captured_body["message"]["data"] == {"deep_link": "today"}
