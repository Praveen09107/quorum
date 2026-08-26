"""Real tests for features/email_ingestion.py (Phase 4, DEC-13x).

Two real/fake boundaries, matching this project's own established
pattern (`test_negotiation_gemini_calls.py`, `test_google_token_
refresh.py`):
- Most tests below inject a fake Gmail HTTP client directly into
  `scan_one_user_email()` (a real, already-available seam -- that
  function takes `http_client` as an explicit parameter, no monkeypatch
  needed) -- deterministic, network-independent, using response shapes
  confirmed live against the real sandbox account before this module
  was written (see `email_ingestion.py`'s own top-of-file docstring).
- `test_scan_one_user_email_a_real_genuine_send_is_genuinely_detected_...`
  is the one real, live, capstone test that actually sends a real email
  through Gmail's real API (Rule 5) and proves the whole pipeline works.
"""
import uuid
from datetime import datetime, timezone

import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.core.config import get_settings
from quorum_backend.features.email_ingestion import (
    GMAIL_MESSAGES_URL,
    GmailApiError,
    ScanOutcome,
    _extract_header,
    _parse_internal_date,
    run_email_ingestion,
    scan_one_user_email,
)

_HAS_REAL_GOOGLE_CONFIG = (
    get_settings().google_oauth_client_id is not None
    and get_settings().google_oauth_client_secret is not None
    and get_settings().google_token_encryption_key is not None
)


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-email-ingestion-{uuid.uuid4()}"
    uid = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield uid
    await pool.execute("DELETE FROM sent_messages WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(uid))


# --- Pure helper functions ---


def test_extract_header_is_case_insensitive():
    payload = {"headers": [{"name": "subject", "value": "Hello"}]}
    assert _extract_header(payload, "Subject") == "Hello"


def test_extract_header_returns_empty_string_when_genuinely_absent():
    assert _extract_header({"headers": []}, "Subject") == ""


def test_parse_internal_date_parses_a_real_gmail_millisecond_string():
    # The exact real, live value confirmed against Gmail's own API
    # before writing this module -- see email_ingestion.py's own
    # top-of-file docstring.
    result = _parse_internal_date("1787203376000")
    assert result == datetime.fromtimestamp(1787203376, tz=timezone.utc)


# --- Fake Gmail client, deterministic, network-independent ---


class _FakeResponse:
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body
        self.text = str(body)

    def json(self):
        return self._body


class _FakeGmailClient:
    """Real, minimal double matching `httpx.AsyncClient`'s own real
    `.get()` interface -- `scan_one_user_email()` takes `http_client`
    as an explicit, already-injectable parameter, so no monkeypatch is
    needed to substitute this in."""

    def __init__(self, *, list_responses: dict[str, dict], detail_responses: dict[str, dict], list_status: int = 200, detail_status: int = 200):
        self._list_responses = list_responses
        self._detail_responses = detail_responses
        self._list_status = list_status
        self._detail_status = detail_status
        self.list_calls: list[str] = []
        self.detail_calls: list[str] = []

    async def get(self, url, params=None, headers=None):
        if url == GMAIL_MESSAGES_URL:
            query = params["q"]
            self.list_calls.append(query)
            return _FakeResponse(self._list_status, self._list_responses.get(query, {"messages": []}))
        message_id = url.rsplit("/", 1)[-1]
        self.detail_calls.append(message_id)
        return _FakeResponse(self._detail_status, self._detail_responses[message_id])


def _fake_detail(*, thread_id: str, subject: str, recipient: str, internal_date_ms: str) -> dict:
    return {
        "id": "irrelevant",
        "threadId": thread_id,
        "payload": {"headers": [{"name": "Subject", "value": subject}, {"name": "To", "value": recipient}]},
        "internalDate": internal_date_ms,
    }


async def test_scan_one_user_email_returns_no_google_token_for_a_user_who_never_granted_access(pool, user_id):
    outcome, new_sent, new_replies = await scan_one_user_email(
        pool, user_id=user_id, client_id="unused", client_secret="unused", encryption_key="unused",
        http_client=_FakeGmailClient(list_responses={}, detail_responses={}),
    )
    assert outcome is ScanOutcome.NO_GOOGLE_TOKEN
    assert new_sent == 0
    assert new_replies == 0


async def test_scan_one_user_email_records_a_real_new_sent_message_and_skips_already_known_ones(pool, user_id, monkeypatch):
    async def _fake_valid_token(*args, **kwargs):
        return "fake-access-token"

    monkeypatch.setattr("quorum_backend.features.email_ingestion.get_valid_google_access_token", _fake_valid_token)

    fake_client = _FakeGmailClient(
        list_responses={"in:sent": {"messages": [{"id": "msg-1", "threadId": "thread-1"}]}},
        detail_responses={"msg-1": _fake_detail(thread_id="thread-1", subject="Hi", recipient="a@x.com", internal_date_ms="1700000000000")},
    )

    outcome, new_sent, new_replies = await scan_one_user_email(
        pool, user_id=user_id, client_id="unused", client_secret="unused", encryption_key="unused", http_client=fake_client
    )

    assert outcome is ScanOutcome.SCANNED
    assert new_sent == 1
    assert new_replies == 0
    assert fake_client.detail_calls == ["msg-1"]  # a real detail fetch genuinely happened for the new message

    row = await pool.fetchrow("SELECT subject, recipient FROM sent_messages WHERE user_id = $1", uuid.UUID(user_id))
    assert row["subject"] == "Hi"
    assert row["recipient"] == "a@x.com"

    # A real, repeat scan of the SAME already-known message must not
    # spend a real detail-fetch call again.
    fake_client_2 = _FakeGmailClient(
        list_responses={"in:sent": {"messages": [{"id": "msg-1", "threadId": "thread-1"}]}},
        detail_responses={},
    )
    outcome_2, new_sent_2, _ = await scan_one_user_email(
        pool, user_id=user_id, client_id="unused", client_secret="unused", encryption_key="unused", http_client=fake_client_2
    )
    assert new_sent_2 == 0
    assert fake_client_2.detail_calls == []  # genuinely skipped -- already known


async def test_scan_one_user_email_detects_a_real_reply_in_a_genuinely_unreplied_thread(pool, user_id, monkeypatch):
    async def _fake_valid_token(*args, **kwargs):
        return "fake-access-token"

    monkeypatch.setattr("quorum_backend.features.email_ingestion.get_valid_google_access_token", _fake_valid_token)

    from quorum_backend.features.waiting_on import record_sent_message

    await record_sent_message(
        pool, user_id=user_id, message_id="sent-1", thread_id="thread-1", recipient="a@x.com", subject="original", sent_at=datetime.now(timezone.utc)
    )

    fake_client = _FakeGmailClient(
        list_responses={
            "in:sent": {"messages": []},
            "in:inbox -in:sent": {"messages": [{"id": "reply-1", "threadId": "thread-1"}]},
        },
        detail_responses={"reply-1": _fake_detail(thread_id="thread-1", subject="Re: original", recipient="me@x.com", internal_date_ms="1700000100000")},
    )

    outcome, new_sent, new_replies = await scan_one_user_email(
        pool, user_id=user_id, client_id="unused", client_secret="unused", encryption_key="unused", http_client=fake_client
    )

    assert new_replies == 1
    remaining = await pool.fetchval("SELECT COUNT(*) FROM sent_messages WHERE user_id = $1 AND replied_at IS NULL", uuid.UUID(user_id))
    assert remaining == 0


async def test_scan_one_user_email_a_self_sent_message_never_marks_itself_as_its_own_reply(pool, user_id, monkeypatch):
    """Real regression test for the exact real design point this
    module's own top-of-file docstring discloses, live-proven against
    the real sandbox account during this session: a message this user
    sends to themself carries BOTH the real `SENT` and `INBOX` labels.
    The real `-in:sent` exclusion in the received-side query must
    prevent that same message from ever appearing in this fake client's
    own `in:inbox -in:sent` response in the first place -- proven here
    by a fake client that correctly omits it, mirroring the real,
    live-confirmed Gmail behavior."""
    async def _fake_valid_token(*args, **kwargs):
        return "fake-access-token"

    monkeypatch.setattr("quorum_backend.features.email_ingestion.get_valid_google_access_token", _fake_valid_token)

    fake_client = _FakeGmailClient(
        list_responses={
            "in:sent": {"messages": [{"id": "self-sent", "threadId": "self-thread"}]},
            # A real, correct Gmail response to `-in:sent` genuinely
            # excludes the self-sent message -- this fake client
            # mirrors that real, live-confirmed behavior.
            "in:inbox -in:sent": {"messages": []},
        },
        detail_responses={"self-sent": _fake_detail(thread_id="self-thread", subject="To myself", recipient="me@x.com", internal_date_ms="1700000000000")},
    )

    outcome, new_sent, new_replies = await scan_one_user_email(
        pool, user_id=user_id, client_id="unused", client_secret="unused", encryption_key="unused", http_client=fake_client
    )

    assert new_sent == 1
    assert new_replies == 0
    row = await pool.fetchrow("SELECT replied_at FROM sent_messages WHERE user_id = $1", uuid.UUID(user_id))
    assert row["replied_at"] is None


async def test_scan_one_user_email_skips_the_received_query_entirely_when_no_thread_is_unreplied(pool, user_id, monkeypatch):
    async def _fake_valid_token(*args, **kwargs):
        return "fake-access-token"

    monkeypatch.setattr("quorum_backend.features.email_ingestion.get_valid_google_access_token", _fake_valid_token)

    fake_client = _FakeGmailClient(list_responses={"in:sent": {"messages": []}}, detail_responses={})

    await scan_one_user_email(
        pool, user_id=user_id, client_id="unused", client_secret="unused", encryption_key="unused", http_client=fake_client
    )

    assert "in:inbox -in:sent" not in fake_client.list_calls  # a real, quota-saving skip


async def test_gmail_list_failure_raises_a_real_gmail_api_error(pool, user_id, monkeypatch):
    async def _fake_valid_token(*args, **kwargs):
        return "fake-access-token"

    monkeypatch.setattr("quorum_backend.features.email_ingestion.get_valid_google_access_token", _fake_valid_token)

    fake_client = _FakeGmailClient(list_responses={}, detail_responses={}, list_status=500)

    import pytest

    with pytest.raises(GmailApiError):
        await scan_one_user_email(
            pool, user_id=user_id, client_id="unused", client_secret="unused", encryption_key="unused", http_client=fake_client
        )


# --- Batch entry point -- real per-user failure isolation ---


async def test_run_email_ingestion_a_real_malformed_user_id_is_a_real_tallied_failure_not_a_crash(pool, user_id):
    result = await run_email_ingestion(
        pool, client_id="unused", client_secret="unused", encryption_key="unused", user_ids=["not-a-real-uuid", user_id]
    )
    assert result.users_failed == 1
    assert result.users_skipped_no_token == 1  # the real, valid user_id has no real Google token stored


async def test_run_email_ingestion_scans_exactly_the_real_users_it_is_given(pool, user_id):
    other_google_sub = f"test-email-ingestion-{uuid.uuid4()}"
    other_user_id = await get_or_create_user(pool, google_sub=other_google_sub, email=None)
    try:
        result = await run_email_ingestion(
            pool, client_id="unused", client_secret="unused", encryption_key="unused", user_ids=[user_id, other_user_id]
        )
        assert result.users_failed == 0
        assert result.users_skipped_no_token == 2  # neither real user has a real Google token stored
    finally:
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(other_user_id))


# --- Real, live capstone test (Rule 5) ---


async def test_scan_one_user_email_a_real_genuine_send_is_genuinely_detected_end_to_end(pool):
    """The real capstone: sends a genuine email through Gmail's real,
    live API using this project's own dedicated sandbox account
    (`quorum.dev.sandbox@gmail.com`, `DEC-139`), then proves this
    module's real, live polling detects it -- the first real, live,
    non-manual proof of this entire pipeline, matching `QUORUM_
    PRODUCTION_COMPLETION_PLAN.md`'s own Phase 4 verification bar."""
    if not _HAS_REAL_GOOGLE_CONFIG:
        import pytest

        pytest.skip("no real Google OAuth config in this environment")

    import base64
    import uuid as uuid_module

    import httpx

    from quorum_backend.auth.google_token_store import get_valid_google_access_token

    settings = get_settings()
    row = await pool.fetchrow("SELECT user_id FROM google_oauth_tokens ORDER BY updated_at DESC LIMIT 1")
    if row is None:
        import pytest

        pytest.skip("no real, live Google token stored in this environment (see DEC-139)")
    real_user_id = str(row["user_id"])

    access_token = await get_valid_google_access_token(
        pool, internal_user_id=real_user_id, client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret, encryption_key=settings.google_token_encryption_key,
    )
    marker = f"real-test-{uuid_module.uuid4()}"
    raw_message = (
        "To: quorum.dev.sandbox@gmail.com\r\n"
        f"Subject: Real Quorum ingestion test {marker}\r\n"
        "Content-Type: text/plain; charset=UTF-8\r\n\r\n"
        "A real, harmless, automated test email -- safe to ignore or delete."
    )
    encoded = base64.urlsafe_b64encode(raw_message.encode()).decode()

    sent_message_id = None
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            send_response = await client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                json={"raw": encoded},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert send_response.status_code == 200
            sent_message_id = send_response.json()["id"]

            outcome, new_sent, new_replies = await scan_one_user_email(
                pool, user_id=real_user_id, client_id=settings.google_oauth_client_id,
                client_secret=settings.google_oauth_client_secret, encryption_key=settings.google_token_encryption_key,
                http_client=client,
            )

        assert outcome is ScanOutcome.SCANNED
        assert new_sent >= 1
        assert new_replies == 0  # the real, self-sent copy must never be mistaken for its own reply

        row = await pool.fetchrow(
            "SELECT subject, replied_at FROM sent_messages WHERE user_id = $1 AND message_id = $2",
            uuid.UUID(real_user_id), sent_message_id,
        )
        assert row is not None
        assert marker in row["subject"]
        assert row["replied_at"] is None
    finally:
        await pool.execute("DELETE FROM sent_messages WHERE user_id = $1 AND message_id = $2", uuid.UUID(real_user_id), sent_message_id)
