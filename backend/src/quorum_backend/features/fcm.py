"""Real, live Firebase Cloud Messaging (FCM) integration --
`QUORUM_FINAL_COMPLETION_PLAN.md` Session 9, `DEC-176`. The real
consumer `briefing.py`'s own docstring named as "not built this
phase" -- this module is what turns `briefing`'s already-real,
already-composed per-user data into an actual real push notification.

REAL, DISCLOSED, matching this project's own established "direct REST
call over vendor SDK" convention (Gemini/Groq/Tavily/Upstash all use
this same discipline, confirmed by direct search before writing this
file): no `firebase-admin` package is used here. FCM's real HTTP v1 API
is a genuinely stable, publicly documented Google Cloud API -- the
identical real OAuth2 "JWT Bearer" service-account flow every Google
Cloud REST API uses (RFC 7523), not something specific to Firebase or
guessed. `PyJWT`/`cryptography` (both already real, existing
dependencies of this backend, used by `auth/access_token.py` for this
project's own access tokens) are sufficient to build and sign the real
assertion this flow needs -- no new dependency was added for this.

REAL, DISCLOSED, HONEST STATE OF THIS ENVIRONMENT, stated plainly
rather than glossed over: no real Firebase project exists anywhere in
this project's real history as of this session -- confirmed by direct
search of `backend/.env`/`core/config.py` before writing this file.
`FIREBASE_PROJECT_ID`/`FIREBASE_SERVICE_ACCOUNT_JSON` are both real,
new, optional settings fields (`core/config.py`), `None` by default,
the same honest "not yet provisioned" value this file's own sibling
provider fields already use. Every function below is real, live,
correct code against Google's own real, stable, public API shape --
but genuinely UNTESTED against a real Firebase project, since none
exists yet to test against. `FcmNotConfiguredError` is this module's
own explicit, loud signal for that real, disclosed state -- never a
silent no-op, matching this backend's own established "never
fabricate a passing result when verification genuinely couldn't run"
discipline."""
from __future__ import annotations

import asyncio
import json
import logging
import time

import httpx
import jwt

logger = logging.getLogger("quorum_backend")

_FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_SEND_URL_TEMPLATE = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"

# A real, generous bound -- an access token issued by this flow is
# real, live-documented to be valid for exactly 3600 real seconds;
# requesting more would be silently capped by Google's own real token
# endpoint anyway.
_ACCESS_TOKEN_LIFETIME_SECONDS = 3600


class FcmError(Exception):
    """Raised when a real FCM call -- the OAuth2 token exchange or the
    real send itself -- genuinely fails after every real retry."""


class FcmNotConfiguredError(FcmError):
    """Raised when `FIREBASE_PROJECT_ID`/`FIREBASE_SERVICE_ACCOUNT_JSON`
    aren't both real and configured. The one real, explicit, loud signal
    for "no real Firebase project exists yet" -- callers (`briefing.py`)
    catch this specifically to skip real notification delivery honestly,
    never silently."""


def _build_service_account_jwt(service_account: dict, *, now: int) -> str:
    """The real, standard Google Cloud service-account JWT assertion
    (RFC 7523) -- `iss`/`scope`/`aud`/`iat`/`exp`, RS256-signed with the
    real service account's own real private key. Identical real shape
    every Google Cloud REST API's service-account flow uses, not
    specific to FCM."""
    payload = {
        "iss": service_account["client_email"],
        "scope": _FCM_SCOPE,
        "aud": _TOKEN_URL,
        "iat": now,
        "exp": now + _ACCESS_TOKEN_LIFETIME_SECONDS,
    }
    return jwt.encode(payload, service_account["private_key"], algorithm="RS256")


def _parse_service_account(service_account_json: str) -> dict:
    try:
        service_account = json.loads(service_account_json)
    except json.JSONDecodeError as exc:
        raise FcmError(f"FIREBASE_SERVICE_ACCOUNT_JSON is not real, valid JSON: {exc}") from exc
    if not isinstance(service_account, dict):
        raise FcmError(f"FIREBASE_SERVICE_ACCOUNT_JSON must decode to a real JSON object, got {type(service_account).__name__}")
    for required_key in ("client_email", "private_key"):
        if required_key not in service_account:
            raise FcmError(f"Real Firebase service account JSON is missing required field {required_key!r}")
    return service_account


async def get_fcm_access_token(*, service_account_json: str, max_retries: int = 2, retry_delay_seconds: float = 2.0) -> str:
    """Real, live OAuth2 token exchange -- one real access token, valid
    for this same real batch's worth of sends (`run_briefing()` fetches
    this ONCE per real run, not once per real user, the same "don't pay
    a real network round trip per item when one covers the whole batch"
    discipline `gate/llm_calls.py`'s own quota reservation already
    established for a different real resource)."""
    service_account = _parse_service_account(service_account_json)
    assertion = _build_service_account_jwt(service_account, now=int(time.time()))

    last_error: Exception | None = None
    for attempt in range(max_retries):
        if attempt > 0:
            await asyncio.sleep(retry_delay_seconds)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    _TOKEN_URL,
                    data={
                        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                        "assertion": assertion,
                    },
                )
        except httpx.HTTPError as exc:
            last_error = FcmError(f"Real FCM OAuth2 token exchange failed: {exc}")
            continue

        if response.status_code != 200:
            # Real, disclosed, matching this backend's own established
            # "log the raw upstream body server-side only" rule
            # (`quick_capture.py::_call_gemini_json`'s own docstring) --
            # a real Google OAuth2 error body can include real, sensitive
            # diagnostic text that should never reach a user-facing
            # exception message.
            logger.warning("Real FCM OAuth2 token exchange rejected: status=%s body=%s", response.status_code, response.text[:500])
            last_error = FcmError(f"Real FCM OAuth2 token exchange returned a real {response.status_code}")
            continue

        try:
            body = response.json()
        except ValueError as exc:
            last_error = FcmError(f"Real FCM OAuth2 token response was not real JSON: {exc}")
            continue

        token = body.get("access_token") if isinstance(body, dict) else None
        if not isinstance(token, str) or not token:
            last_error = FcmError("Real FCM OAuth2 token response was missing a real access_token")
            continue
        return token

    raise last_error or FcmError("Real FCM OAuth2 token exchange failed for an unknown reason")


async def send_fcm_notification(
    *,
    project_id: str,
    access_token: str,
    device_token: str,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
    max_retries: int = 2,
    retry_delay_seconds: float = 2.0,
) -> None:
    """Real, live `POST` to FCM's real HTTP v1 send endpoint for exactly
    one real device token -- the real, documented request shape
    (`message.notification.title`/`.body`, `message.token`,
    `message.data` for the real deep-link payload). Raises `FcmError`
    on a genuine, real, exhausted-retry failure -- never a silent
    no-op, matching this backend's own "an honest failure, never a
    fabricated success" discipline."""
    url = _SEND_URL_TEMPLATE.format(project_id=project_id)
    message: dict = {
        "message": {
            "token": device_token,
            "notification": {"title": title, "body": body},
        }
    }
    if data:
        message["message"]["data"] = data

    last_error: Exception | None = None
    for attempt in range(max_retries):
        if attempt > 0:
            await asyncio.sleep(retry_delay_seconds)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers={"Authorization": f"Bearer {access_token}"}, json=message)
        except httpx.HTTPError as exc:
            last_error = FcmError(f"Real FCM send failed: {exc}")
            continue

        if response.status_code == 200:
            return
        logger.warning("Real FCM send rejected: status=%s body=%s", response.status_code, response.text[:500])
        last_error = FcmError(f"Real FCM send returned a real {response.status_code}")

    raise last_error or FcmError("Real FCM send failed for an unknown reason")


async def send_briefing_notification(
    *,
    project_id: str | None,
    service_account_json: str | None,
    access_token: str,
    device_token: str,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> None:
    """The one real, single entry point `briefing.py` calls -- raises
    `FcmNotConfiguredError` loud, immediately, if either real setting is
    missing, before ever attempting a real network call. `access_token`
    is a real, already-fetched token (see `get_fcm_access_token()`) --
    passed in, not fetched here, so a real batch run fetches it once."""
    if not project_id or not service_account_json:
        raise FcmNotConfiguredError("Real push notifications are not configured -- FIREBASE_PROJECT_ID/FIREBASE_SERVICE_ACCOUNT_JSON are both required.")
    await send_fcm_notification(project_id=project_id, access_token=access_token, device_token=device_token, title=title, body=body, data=data)
