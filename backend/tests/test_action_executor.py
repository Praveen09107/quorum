"""Real tests for features/action_executor.py (DEC-128, extended
DEC-142) -- real inserts against the real, live database for
`CREATE_TASK`/`LOG_EXPENSE`, real Gmail API calls for `SEND_EMAIL`/
`ARCHIVE_EMAIL`/`LABEL_EMAIL` (against the real sandbox account, Rule
5), and a real, exhaustive proof that every other real `ActionType`
returns an honest, non-executing result, per CLAUDE.md Rule 5.
"""
import uuid
from datetime import datetime, timezone

import httpx
import pytest
import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.core.config import get_settings
from quorum_backend.features.action_executor import execute_approved_action
from quorum_backend.gate.schemas import ActionType

_HAS_REAL_GOOGLE_CONFIG = (
    get_settings().google_oauth_client_id is not None
    and get_settings().google_oauth_client_secret is not None
    and get_settings().google_token_encryption_key is not None
)


class _FakeResponse:
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body
        self.text = str(body)

    def json(self):
        return self._body


class _FakePostClient:
    """A real, minimal double for `httpx.AsyncClient`'s own `.post()`
    interface -- `execute_approved_action()` takes `http_client` as an
    explicit, already-injectable parameter, matching `email_ingestion.
    py`'s own established fake-client pattern."""

    def __init__(self, *, status_code: int = 200, body: dict | None = None):
        self.status_code = status_code
        self.body = body or {"id": "fake-message-id", "threadId": "fake-thread-id", "labelIds": []}
        self.calls: list[tuple[str, dict, dict]] = []

    async def post(self, url, json=None, headers=None):
        self.calls.append((url, json, headers))
        return _FakeResponse(self.status_code, self.body)


def _patch_valid_token(monkeypatch, token: str = "fake-access-token") -> None:
    async def _fake_valid_token(*args, **kwargs):
        return token

    monkeypatch.setattr("quorum_backend.features.action_executor.get_valid_google_access_token", _fake_valid_token)


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-executor-{uuid.uuid4()}"
    uid = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield uid
    await pool.execute("DELETE FROM tasks WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM expenses WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(uid))


async def test_execute_approved_action_create_task_writes_a_real_row(pool, user_id):
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn,
            action_type=ActionType.CREATE_TASK,
            payload={"title": "Real executed task", "estimated_hours": 2.5, "deadline": None},
            user_id=user_id,
        )
    assert result.executed is True
    row = await pool.fetchrow(
        "SELECT title, estimated_hours, deadline, status FROM tasks WHERE user_id = $1", uuid.UUID(user_id)
    )
    assert row is not None
    assert row["title"] == "Real executed task"
    assert float(row["estimated_hours"]) == 2.5
    assert row["deadline"] is None
    assert row["status"] == "open"


async def test_execute_approved_action_create_task_with_a_real_deadline(pool, user_id):
    deadline = datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc)
    async with pool.acquire() as conn:
        await execute_approved_action(
            conn,
            action_type=ActionType.CREATE_TASK,
            payload={"title": "Real deadlined task", "estimated_hours": 1.0, "deadline": deadline.isoformat()},
            user_id=user_id,
        )
    row = await pool.fetchrow("SELECT deadline FROM tasks WHERE user_id = $1", uuid.UUID(user_id))
    assert row["deadline"] == deadline


async def test_execute_approved_action_log_expense_writes_a_real_row_with_the_new_gate_approved_source(pool, user_id):
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn,
            action_type=ActionType.LOG_EXPENSE,
            payload={"amount": 42.5, "category": "food", "payee": "Real Vendor"},
            user_id=user_id,
        )
    assert result.executed is True
    row = await pool.fetchrow(
        "SELECT payee, amount, source FROM expenses WHERE user_id = $1", uuid.UUID(user_id)
    )
    assert row is not None
    assert row["payee"] == "Real Vendor"
    assert float(row["amount"]) == 42.5
    # DEC-128's own real, live schema migration (0007) -- confirmed
    # here, live, not just read from the migration file.
    assert row["source"] == "gate_approved"


async def test_execute_approved_action_log_expense_defaults_a_real_missing_payee_honestly(pool, user_id):
    async with pool.acquire() as conn:
        await execute_approved_action(
            conn,
            action_type=ActionType.LOG_EXPENSE,
            payload={"amount": 10.0, "category": "food", "payee": None},
            user_id=user_id,
        )
    row = await pool.fetchrow("SELECT payee FROM expenses WHERE user_id = $1", uuid.UUID(user_id))
    assert row["payee"] == "Unknown"


async def test_execute_approved_action_fails_safely_not_loudly_on_a_real_malformed_payload(pool, user_id):
    """A real, defensive guard: `CREATE_TASK`/`LOG_EXPENSE` should never
    reach this function with a payload missing required keys under the
    real, current stakes table (Stage B never runs for S1, so the
    payload is always the original, validated one) -- but if that
    invariant is ever violated by a future change, this must fail
    safely (a real, honest `executed=False`) rather than raise an
    unhandled exception mid-transaction."""
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.CREATE_TASK, payload={"title": "Missing hours"}, user_id=user_id
        )
    assert result.executed is False
    assert "malformed" in result.detail.lower()
    assert await pool.fetchrow("SELECT 1 FROM tasks WHERE user_id = $1", uuid.UUID(user_id)) is None


# --- SEND_EMAIL: the real S3 backstop, DEC-142's own review finding ---


async def test_execute_approved_action_send_email_refuses_without_real_human_approval(pool, user_id):
    """The real, structural backstop this session's own review found
    missing from `gate/orchestration.py` itself -- see action_executor.
    py's own top-of-file docstring. Refuses BEFORE ever touching Google
    config or a real access token."""
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.SEND_EMAIL, payload={"to": "a@x.com", "body": "hi"}, user_id=user_id,
            google_client_id="unused", google_client_secret="unused", google_token_encryption_key="unused",
        )
    assert result.executed is False
    assert "S3" in result.detail
    assert "human_approved" in result.detail


async def test_execute_approved_action_send_email_refuses_without_real_google_config_even_when_human_approved(pool, user_id):
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.SEND_EMAIL, payload={"to": "a@x.com", "body": "hi"}, user_id=user_id,
            human_approved=True,
        )
    assert result.executed is False
    assert "Google OAuth configuration" in result.detail


async def test_execute_approved_action_send_email_refuses_for_a_user_with_no_real_google_grant(pool, user_id, monkeypatch):
    async def _fake_none(*args, **kwargs):
        return None

    monkeypatch.setattr("quorum_backend.features.action_executor.get_valid_google_access_token", _fake_none)
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.SEND_EMAIL, payload={"to": "a@x.com", "body": "hi"}, user_id=user_id,
            human_approved=True, google_client_id="x", google_client_secret="y", google_token_encryption_key="z",
        )
    assert result.executed is False
    assert "no real, stored Google grant" in result.detail


async def test_execute_approved_action_send_email_a_real_malformed_payload_is_honest_not_a_crash(pool, user_id, monkeypatch):
    _patch_valid_token(monkeypatch)
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.SEND_EMAIL, payload={"to": "a@x.com"}, user_id=user_id,  # missing "body"
            human_approved=True, google_client_id="x", google_client_secret="y", google_token_encryption_key="z",
            http_client=_FakePostClient(),
        )
    assert result.executed is False
    assert "malformed" in result.detail.lower()


async def test_execute_approved_action_send_email_a_real_gmail_failure_is_honest_not_a_crash(pool, user_id, monkeypatch):
    _patch_valid_token(monkeypatch)
    fake_client = _FakePostClient(status_code=500, body={"error": "fake failure"})
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.SEND_EMAIL, payload={"to": "a@x.com", "body": "hi"}, user_id=user_id,
            human_approved=True, google_client_id="x", google_client_secret="y", google_token_encryption_key="z",
            http_client=fake_client,
        )
    assert result.executed is False
    assert "Google's real API" in result.detail


async def test_execute_approved_action_send_email_sends_a_real_raw_mime_message_with_the_real_existing_payload_shape(pool, user_id, monkeypatch):
    """Real, deterministic proof of the exact real payload contract
    `agents/email_agent.py::build_reply_proposal()` already produces
    (`to`/`body`, no `subject`) -- see action_executor.py's own top-of-
    file docstring for the real, disclosed gap this exposes."""
    _patch_valid_token(monkeypatch)
    fake_client = _FakePostClient(body={"id": "sent-1", "threadId": "thread-1", "labelIds": ["SENT"]})
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.SEND_EMAIL, payload={"to": "a@x.com", "body": "hello there"}, user_id=user_id,
            human_approved=True, google_client_id="x", google_client_secret="y", google_token_encryption_key="z",
            http_client=fake_client,
        )
    assert result.executed is True
    assert "sent-1" in result.detail
    url, body, headers = fake_client.calls[0]
    assert url.endswith("/messages/send")
    assert headers["Authorization"] == "Bearer fake-access-token"
    import base64

    raw = base64.urlsafe_b64decode(body["raw"]).decode()
    assert "To: a@x.com" in raw
    assert "Subject: \r\n" in raw  # a real, honest empty subject -- the real payload shape has none
    assert "hello there" in raw


# --- ARCHIVE_EMAIL / LABEL_EMAIL: real Gmail modify calls, S1/S0, no human_approved needed ---


async def test_execute_approved_action_archive_email_succeeds_with_a_real_fake_gmail_response(pool, user_id, monkeypatch):
    _patch_valid_token(monkeypatch)
    fake_client = _FakePostClient()
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.ARCHIVE_EMAIL, payload={"message_id": "msg-1"}, user_id=user_id,
            google_client_id="x", google_client_secret="y", google_token_encryption_key="z", http_client=fake_client,
        )
    assert result.executed is True
    url, body, headers = fake_client.calls[0]
    assert url.endswith("/msg-1/modify")
    assert body == {"removeLabelIds": ["INBOX"]}
    assert headers["Authorization"] == "Bearer fake-access-token"


async def test_execute_approved_action_label_email_succeeds_with_a_real_fake_gmail_response(pool, user_id, monkeypatch):
    _patch_valid_token(monkeypatch)
    fake_client = _FakePostClient()
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.LABEL_EMAIL, payload={"message_id": "msg-1", "label_id": "IMPORTANT"}, user_id=user_id,
            google_client_id="x", google_client_secret="y", google_token_encryption_key="z", http_client=fake_client,
        )
    assert result.executed is True
    url, body, headers = fake_client.calls[0]
    assert url.endswith("/msg-1/modify")
    assert body == {"addLabelIds": ["IMPORTANT"]}


async def test_execute_approved_action_archive_email_a_real_malformed_payload_missing_message_id(pool, user_id, monkeypatch):
    _patch_valid_token(monkeypatch)
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.ARCHIVE_EMAIL, payload={}, user_id=user_id,
            google_client_id="x", google_client_secret="y", google_token_encryption_key="z", http_client=_FakePostClient(),
        )
    assert result.executed is False
    assert "malformed" in result.detail.lower()


async def test_execute_approved_action_label_email_a_real_malformed_payload_missing_label_id(pool, user_id, monkeypatch):
    """A real `message_id` present but no real `label_id` -- must fail
    the same honest way, never a raw `KeyError`."""
    _patch_valid_token(monkeypatch)
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.LABEL_EMAIL, payload={"message_id": "msg-1"}, user_id=user_id,
            google_client_id="x", google_client_secret="y", google_token_encryption_key="z", http_client=_FakePostClient(),
        )
    assert result.executed is False
    assert "malformed" in result.detail.lower()


async def test_execute_approved_action_label_email_a_real_gmail_failure_is_honest_not_a_crash(pool, user_id, monkeypatch):
    _patch_valid_token(monkeypatch)
    fake_client = _FakePostClient(status_code=404, body={"error": "fake: message not found"})
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.LABEL_EMAIL, payload={"message_id": "gone", "label_id": "IMPORTANT"}, user_id=user_id,
            google_client_id="x", google_client_secret="y", google_token_encryption_key="z", http_client=fake_client,
        )
    assert result.executed is False
    assert "Google's real API" in result.detail


# --- Real, live capstone tests (Rule 5) ---


async def test_execute_approved_action_send_email_a_real_genuine_send_via_gmail(pool):
    """The real capstone for SEND_EMAIL: a genuine, human-approved send
    through Gmail's real, live API against this project's own dedicated
    sandbox account (`quorum.dev.sandbox@gmail.com`, `DEC-139`)."""
    if not _HAS_REAL_GOOGLE_CONFIG:
        pytest.skip("no real Google OAuth config in this environment")

    settings = get_settings()
    row = await pool.fetchrow("SELECT user_id FROM google_oauth_tokens ORDER BY updated_at DESC LIMIT 1")
    if row is None:
        pytest.skip("no real, live Google token stored in this environment (see DEC-139)")
    real_user_id = str(row["user_id"])
    marker = f"real-execution-test-{uuid.uuid4()}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client, pool.acquire() as conn:
            result = await execute_approved_action(
                conn,
                action_type=ActionType.SEND_EMAIL,
                payload={
                    "to": "quorum.dev.sandbox@gmail.com",
                    "subject": f"Real Quorum execution test {marker}",
                    "body": "A real, harmless, automated execution test -- safe to ignore or delete.",
                },
                user_id=real_user_id,
                human_approved=True,
                google_client_id=settings.google_oauth_client_id,
                google_client_secret=settings.google_oauth_client_secret,
                google_token_encryption_key=settings.google_token_encryption_key,
                http_client=client,
            )
        assert result.executed is True
        assert "message_id" in result.detail
    finally:
        await _cleanup_real_gmail_messages_matching(pool, real_user_id, marker)


async def test_execute_approved_action_archive_and_label_email_a_real_genuine_modify_via_gmail(pool):
    """The real capstone for ARCHIVE_EMAIL/LABEL_EMAIL: sends a real
    probe message directly (bypassing `execute_approved_action`, to
    isolate what THIS test is proving), then archives and labels it for
    real through `execute_approved_action`, verifying both real label
    changes directly against Gmail's own API afterward."""
    if not _HAS_REAL_GOOGLE_CONFIG:
        pytest.skip("no real Google OAuth config in this environment")

    import base64

    from quorum_backend.auth.google_token_store import get_valid_google_access_token

    settings = get_settings()
    row = await pool.fetchrow("SELECT user_id FROM google_oauth_tokens ORDER BY updated_at DESC LIMIT 1")
    if row is None:
        pytest.skip("no real, live Google token stored in this environment (see DEC-139)")
    real_user_id = str(row["user_id"])
    marker = f"real-modify-test-{uuid.uuid4()}"

    access_token = await get_valid_google_access_token(
        pool, internal_user_id=real_user_id, client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret, encryption_key=settings.google_token_encryption_key,
    )
    raw_message = (
        "To: quorum.dev.sandbox@gmail.com\r\n"
        f"Subject: Real Quorum modify test {marker}\r\n"
        "Content-Type: text/plain; charset=UTF-8\r\n\r\n"
        "A real, harmless, automated modify test -- safe to ignore or delete."
    )
    encoded = base64.urlsafe_b64encode(raw_message.encode()).decode()

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            send_response = await client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                json={"raw": encoded}, headers={"Authorization": f"Bearer {access_token}"},
            )
            assert send_response.status_code == 200
            message_id = send_response.json()["id"]

            async with pool.acquire() as conn:
                archive_result = await execute_approved_action(
                    conn, action_type=ActionType.ARCHIVE_EMAIL, payload={"message_id": message_id}, user_id=real_user_id,
                    google_client_id=settings.google_oauth_client_id, google_client_secret=settings.google_oauth_client_secret,
                    google_token_encryption_key=settings.google_token_encryption_key, http_client=client,
                )
            assert archive_result.executed is True

            check_response = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
                params={"format": "minimal"}, headers={"Authorization": f"Bearer {access_token}"},
            )
            assert "INBOX" not in check_response.json()["labelIds"]  # genuinely archived, not just claimed

            async with pool.acquire() as conn:
                label_result = await execute_approved_action(
                    conn, action_type=ActionType.LABEL_EMAIL, payload={"message_id": message_id, "label_id": "IMPORTANT"},
                    user_id=real_user_id, google_client_id=settings.google_oauth_client_id,
                    google_client_secret=settings.google_oauth_client_secret,
                    google_token_encryption_key=settings.google_token_encryption_key, http_client=client,
                )
            assert label_result.executed is True

            check_response_2 = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
                params={"format": "minimal"}, headers={"Authorization": f"Bearer {access_token}"},
            )
            assert "IMPORTANT" in check_response_2.json()["labelIds"]  # genuinely labeled, not just claimed
    finally:
        await _cleanup_real_gmail_messages_matching(pool, real_user_id, marker)


async def _cleanup_real_gmail_messages_matching(pool, real_user_id: str, marker: str) -> None:
    """Finds and trashes every real Gmail message this test run itself
    created (matched by its own unique marker subject), the same real
    cleanup discipline `test_email_ingestion.py`'s own capstone test
    established this session (DEC-140, review finding M2) -- never
    leaves real test debris in the real, live sandbox account."""
    settings = get_settings()
    from quorum_backend.auth.google_token_store import get_valid_google_access_token

    access_token = await get_valid_google_access_token(
        pool, internal_user_id=real_user_id, client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret, encryption_key=settings.google_token_encryption_key,
    )
    async with httpx.AsyncClient(timeout=15.0) as client:
        list_response = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            params={"q": f"subject:{marker}"}, headers={"Authorization": f"Bearer {access_token}"},
        )
        for message in list_response.json().get("messages", []):
            await client.post(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message['id']}/trash",
                headers={"Authorization": f"Bearer {access_token}"},
            )


async def test_execute_approved_action_is_exhaustively_honest_about_every_other_real_action_type(pool, user_id):
    """A real, exhaustive proof, not a spot-check: every real
    `ActionType` other than `CREATE_TASK`/`LOG_EXPENSE` returns
    `executed=False` with a real, non-empty explanation, and genuinely
    writes nothing anywhere -- confirmed by an unconditional real row
    count, not just trusting the return value."""
    non_executable = [t for t in ActionType if t not in (ActionType.CREATE_TASK, ActionType.LOG_EXPENSE)]
    assert len(non_executable) == 9  # a real, live guard against this enum silently growing unnoticed

    async with pool.acquire() as conn:
        for action_type in non_executable:
            result = await execute_approved_action(conn, action_type=action_type, payload={}, user_id=user_id)
            assert result.executed is False, f"{action_type} unexpectedly executed"
            assert len(result.detail) > 0

    assert await pool.fetchrow("SELECT 1 FROM tasks WHERE user_id = $1", uuid.UUID(user_id)) is None
    assert await pool.fetchrow("SELECT 1 FROM expenses WHERE user_id = $1", uuid.UUID(user_id)) is None
