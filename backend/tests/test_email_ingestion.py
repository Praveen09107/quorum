"""Real tests for features/email_ingestion.py (Phase 4, DEC-140).

Two real/fake boundaries, matching this project's own established
pattern (`test_negotiation_gemini_calls.py`, `test_google_token_
refresh.py`):
- Most tests below inject a fake, LABEL-AWARE Gmail HTTP client
  directly into `scan_one_user_email()` (a real, already-available
  seam -- that function takes `http_client` as an explicit parameter,
  no monkeypatch needed) -- deterministic, network-independent, using
  response shapes confirmed live against the real sandbox account
  before this module was written (see `email_ingestion.py`'s own
  top-of-file docstring). The fake genuinely evaluates `in:sent` /
  `in:inbox -in:sent` against each fake message's own `labelIds`, the
  same way real Gmail does -- a real, disclosed CRITICAL-tier review
  finding (`DEC-140`, M1): an earlier version of this fake hardcoded
  the right answer per query string, which meant a real regression
  (reverting `-in:sent` back to bare `in:inbox`) would have silently
  kept passing every test.
- `test_scan_one_user_email_a_real_genuine_send_is_genuinely_detected_...`
  is the one real, live, capstone test that actually sends a real email
  through Gmail's real API (Rule 5) and proves the whole pipeline works.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from quorum_backend.auth.google_oauth import GoogleOAuthExchangeFailed
from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.core.config import get_settings
from quorum_backend.features.email_ingestion import (
    GMAIL_MESSAGES_URL,
    GmailApiError,
    ScanOutcome,
    _extract_header,
    _parse_internal_date,
    _release_job_lock,
    _try_claim_job_lock,
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


@pytest_asyncio.fixture(autouse=True)
async def _clean_real_job_lock(pool):
    """The `email_ingestion_job_lock` row (migration `0012`) is a real,
    live SINGLETON shared by every test in this module (and, in a real
    deployment, every real `pg_cron` fire) -- a test that fails between
    claiming it and releasing it must never leave it stuck for every
    test that runs after it. Guarantees a clean, free lock both before
    and after every real test in this module."""
    await _release_job_lock(pool)
    yield
    await _release_job_lock(pool)


def _patch_valid_token(monkeypatch, token: str = "fake-access-token") -> None:
    async def _fake_valid_token(*args, **kwargs):
        return token

    monkeypatch.setattr("quorum_backend.features.email_ingestion.get_valid_google_access_token", _fake_valid_token)


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


# --- Fake, label-aware Gmail client (see this module's own top-of-file docstring) ---


@dataclass
class _FakeGmailMessage:
    id: str
    thread_id: str
    label_ids: list[str]
    subject: str
    recipient: str
    internal_date_ms: str


class _FakeResponse:
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body
        self.text = str(body)

    def json(self):
        return self._body


def _fake_detail_body(message: _FakeGmailMessage) -> dict:
    return {
        "id": message.id,
        "threadId": message.thread_id,
        "payload": {
            "headers": [
                {"name": "Subject", "value": message.subject},
                {"name": "To", "value": message.recipient},
            ]
        },
        "internalDate": message.internal_date_ms,
    }


class _FakeGmailClient:
    """Real, minimal double matching `httpx.AsyncClient`'s own real
    `.get()` interface. Evaluates `in:sent` / `in:inbox -in:sent`
    against each fake message's own `label_ids`, exactly the way real
    Gmail does -- an unrecognized query string raises `AssertionError`
    outright, a real, deliberate signal that a test (not this fake)
    needs updating, rather than a silent, vacuous pass."""

    def __init__(self, messages: list[_FakeGmailMessage], *, list_status: int = 200, detail_status: int = 200):
        self._messages = messages
        self._list_status = list_status
        self._detail_status = detail_status
        self.list_calls: list[str] = []
        self.detail_calls: list[str] = []

    async def get(self, url, params=None, headers=None):
        if url == GMAIL_MESSAGES_URL:
            query = params["q"]
            self.list_calls.append(query)
            if self._list_status != 200:
                return _FakeResponse(self._list_status, {"error": "fake list failure"})
            matched = self._evaluate_query(query)
            return _FakeResponse(200, {"messages": [{"id": m.id, "threadId": m.thread_id} for m in matched]})
        message_id = url.rsplit("/", 1)[-1]
        self.detail_calls.append(message_id)
        if self._detail_status != 200:
            return _FakeResponse(self._detail_status, {"error": "fake detail failure"})
        message = next(m for m in self._messages if m.id == message_id)
        return _FakeResponse(200, _fake_detail_body(message))

    def _evaluate_query(self, query: str) -> list[_FakeGmailMessage]:
        if query == "in:sent":
            return [m for m in self._messages if "SENT" in m.label_ids]
        if query == "in:inbox -in:sent":
            return [m for m in self._messages if "INBOX" in m.label_ids and "SENT" not in m.label_ids]
        raise AssertionError(f"_FakeGmailClient does not model the real Gmail query {query!r} -- update the fake, don't silently pass")


# --- scan_one_user_email ---


async def test_scan_one_user_email_returns_no_google_token_for_a_user_who_never_granted_access(pool, user_id):
    outcome, new_sent, new_replies, messages_failed = await scan_one_user_email(
        pool, user_id=user_id, client_id="unused", client_secret="unused", encryption_key="unused",
        http_client=_FakeGmailClient([]),
    )
    assert outcome is ScanOutcome.NO_GOOGLE_TOKEN
    assert (new_sent, new_replies, messages_failed) == (0, 0, 0)


async def test_scan_one_user_email_a_real_refresh_failure_is_a_distinct_honest_outcome_not_a_failure(pool, user_id, monkeypatch):
    """DEC-140 review finding H3: a real, stored grant that currently
    can't be refreshed (revoked, or Google's own endpoint degraded --
    genuinely unknown which) must be reported as its own DISTINCT
    outcome, never collapsed into `NO_GOOGLE_TOKEN` (which means "never
    granted at all") or silently propagated as an unhandled code
    failure."""
    async def _fake_valid_token_raises(*args, **kwargs):
        raise GoogleOAuthExchangeFailed("fake: invalid_grant")

    monkeypatch.setattr("quorum_backend.features.email_ingestion.get_valid_google_access_token", _fake_valid_token_raises)

    outcome, new_sent, new_replies, messages_failed = await scan_one_user_email(
        pool, user_id=user_id, client_id="unused", client_secret="unused", encryption_key="unused",
        http_client=_FakeGmailClient([]),
    )
    assert outcome is ScanOutcome.GOOGLE_TOKEN_REFRESH_FAILED
    assert (new_sent, new_replies, messages_failed) == (0, 0, 0)


async def test_scan_one_user_email_records_a_real_new_sent_message_and_skips_already_known_ones(pool, user_id, monkeypatch):
    _patch_valid_token(monkeypatch)

    fake_client = _FakeGmailClient([
        _FakeGmailMessage(id="msg-1", thread_id="thread-1", label_ids=["SENT"], subject="Hi", recipient="a@x.com", internal_date_ms="1700000000000"),
    ])

    outcome, new_sent, new_replies, messages_failed = await scan_one_user_email(
        pool, user_id=user_id, client_id="unused", client_secret="unused", encryption_key="unused", http_client=fake_client
    )

    assert outcome is ScanOutcome.SCANNED
    assert new_sent == 1
    assert new_replies == 0
    assert messages_failed == 0
    assert fake_client.detail_calls == ["msg-1"]  # a real detail fetch genuinely happened for the new message

    row = await pool.fetchrow("SELECT subject, recipient FROM sent_messages WHERE user_id = $1", uuid.UUID(user_id))
    assert row["subject"] == "Hi"
    assert row["recipient"] == "a@x.com"

    # A real, repeat scan of the SAME already-known message must not
    # spend a real detail-fetch call again.
    fake_client_2 = _FakeGmailClient([
        _FakeGmailMessage(id="msg-1", thread_id="thread-1", label_ids=["SENT"], subject="Hi", recipient="a@x.com", internal_date_ms="1700000000000"),
    ])
    outcome_2, new_sent_2, _, _ = await scan_one_user_email(
        pool, user_id=user_id, client_id="unused", client_secret="unused", encryption_key="unused", http_client=fake_client_2
    )
    assert new_sent_2 == 0
    assert fake_client_2.detail_calls == []  # genuinely skipped -- already known


async def test_scan_one_user_email_a_real_message_detail_failure_is_tallied_not_fatal(pool, user_id, monkeypatch):
    """DEC-140 review finding H1: a single unparseable/deleted real
    Gmail message must never permanently poison this user's whole
    scan. A real 404 on ONE message's detail fetch (a message deleted
    between `messages.list` and `messages.get`, or any other real,
    per-message failure) is tallied into `messages_failed` and the
    scan continues -- proven here alongside a second, healthy message
    in the same poll that is still correctly recorded."""
    _patch_valid_token(monkeypatch)

    fake_client = _FakeGmailClient([
        _FakeGmailMessage(id="bad-msg", thread_id="thread-bad", label_ids=["SENT"], subject="never reached", recipient="a@x.com", internal_date_ms="1700000000000"),
        _FakeGmailMessage(id="good-msg", thread_id="thread-good", label_ids=["SENT"], subject="Hi", recipient="b@x.com", internal_date_ms="1700000000000"),
    ])
    original_get = fake_client.get

    async def _flaky_get(url, params=None, headers=None):
        if url.endswith("/bad-msg"):
            return _FakeResponse(404, {"error": "fake: message not found"})
        return await original_get(url, params=params, headers=headers)

    fake_client.get = _flaky_get

    outcome, new_sent, new_replies, messages_failed = await scan_one_user_email(
        pool, user_id=user_id, client_id="unused", client_secret="unused", encryption_key="unused", http_client=fake_client
    )

    assert outcome is ScanOutcome.SCANNED
    assert new_sent == 1  # only the healthy message
    assert messages_failed == 1

    good_row = await pool.fetchrow("SELECT subject FROM sent_messages WHERE user_id = $1 AND message_id = 'good-msg'", uuid.UUID(user_id))
    assert good_row is not None
    bad_row = await pool.fetchrow("SELECT 1 FROM sent_messages WHERE user_id = $1 AND message_id = 'bad-msg'", uuid.UUID(user_id))
    assert bad_row is None


async def test_scan_one_user_email_detects_a_real_reply_in_a_genuinely_unreplied_thread(pool, user_id, monkeypatch):
    _patch_valid_token(monkeypatch)

    from quorum_backend.features.waiting_on import record_sent_message

    await record_sent_message(
        pool, user_id=user_id, message_id="sent-1", thread_id="thread-1", recipient="a@x.com", subject="original",
        sent_at=datetime.fromtimestamp(1700000000, tz=timezone.utc),  # genuinely BEFORE the real reply below
    )

    fake_client = _FakeGmailClient([
        _FakeGmailMessage(id="reply-1", thread_id="thread-1", label_ids=["INBOX"], subject="Re: original", recipient="me@x.com", internal_date_ms="1700000100000"),  # 100s later
    ])

    outcome, new_sent, new_replies, messages_failed = await scan_one_user_email(
        pool, user_id=user_id, client_id="unused", client_secret="unused", encryption_key="unused", http_client=fake_client
    )

    assert new_replies == 1
    assert messages_failed == 0
    remaining = await pool.fetchval("SELECT COUNT(*) FROM sent_messages WHERE user_id = $1 AND replied_at IS NULL", uuid.UUID(user_id))
    assert remaining == 0


async def test_scan_one_user_email_an_old_inbound_message_never_marks_a_newer_real_send_as_replied(pool, user_id, monkeypatch):
    """The real, live BLOCKER this session's own CRITICAL-tier review
    found (`DEC-140`): a real, old inbound message that simply never
    got archived must never be mistaken for a reply to a real send
    that happened AFTER it. The correctness guard itself lives in
    `waiting_on.py::mark_thread_replied`; this test proves the real,
    live pipeline end to end through `scan_one_user_email`."""
    _patch_valid_token(monkeypatch)

    from quorum_backend.features.waiting_on import record_sent_message

    await record_sent_message(
        pool, user_id=user_id, message_id="newer-send", thread_id="shared-thread", recipient="a@x.com",
        subject="a later real send", sent_at=datetime.fromtimestamp(1700000200, tz=timezone.utc),
    )

    fake_client = _FakeGmailClient([
        _FakeGmailMessage(
            id="old-inbound", thread_id="shared-thread", label_ids=["INBOX"], subject="an old, unarchived message",
            recipient="me@x.com", internal_date_ms="1700000000000",  # genuinely BEFORE the send above
        ),
    ])

    outcome, new_sent, new_replies, messages_failed = await scan_one_user_email(
        pool, user_id=user_id, client_id="unused", client_secret="unused", encryption_key="unused", http_client=fake_client
    )

    assert new_replies == 0  # the old inbound message must NOT close out the newer real send
    assert messages_failed == 0
    remaining = await pool.fetchval("SELECT COUNT(*) FROM sent_messages WHERE user_id = $1 AND replied_at IS NULL", uuid.UUID(user_id))
    assert remaining == 1


async def test_scan_one_user_email_a_self_sent_message_never_marks_itself_as_its_own_reply(pool, user_id, monkeypatch):
    """Real regression test for the exact real design point this
    module's own top-of-file docstring discloses, live-proven against
    the real sandbox account during this session: a message this user
    sends to themself carries BOTH the real `SENT` and `INBOX` labels.
    The fake client here genuinely evaluates Gmail's own real label
    semantics (`-in:sent` excludes anything carrying `SENT`) rather
    than hardcoding the right answer per query string -- a real,
    disclosed CRITICAL-tier review finding (`DEC-140`, M1): a fake that
    hardcodes the answer would keep passing even if the real
    `-in:sent` exclusion were reverted."""
    _patch_valid_token(monkeypatch)

    fake_client = _FakeGmailClient([
        _FakeGmailMessage(id="self-sent", thread_id="self-thread", label_ids=["SENT", "INBOX"], subject="To myself", recipient="me@x.com", internal_date_ms="1700000000000"),
    ])

    outcome, new_sent, new_replies, messages_failed = await scan_one_user_email(
        pool, user_id=user_id, client_id="unused", client_secret="unused", encryption_key="unused", http_client=fake_client
    )

    assert new_sent == 1
    assert new_replies == 0
    assert messages_failed == 0
    assert "in:inbox -in:sent" in fake_client.list_calls  # the real, load-bearing query genuinely ran
    row = await pool.fetchrow("SELECT replied_at FROM sent_messages WHERE user_id = $1", uuid.UUID(user_id))
    assert row["replied_at"] is None


async def test_scan_one_user_email_skips_the_received_query_entirely_when_no_thread_is_unreplied(pool, user_id, monkeypatch):
    _patch_valid_token(monkeypatch)

    fake_client = _FakeGmailClient([])

    await scan_one_user_email(
        pool, user_id=user_id, client_id="unused", client_secret="unused", encryption_key="unused", http_client=fake_client
    )

    assert "in:inbox -in:sent" not in fake_client.list_calls  # a real, quota-saving skip


async def test_gmail_list_failure_raises_a_real_gmail_api_error(pool, user_id, monkeypatch):
    _patch_valid_token(monkeypatch)

    fake_client = _FakeGmailClient([], list_status=500)

    with pytest.raises(GmailApiError):
        await scan_one_user_email(
            pool, user_id=user_id, client_id="unused", client_secret="unused", encryption_key="unused", http_client=fake_client
        )


# --- Batch entry point -- real per-user failure isolation, and the real job-level lock ---


async def test_run_email_ingestion_a_real_malformed_user_id_is_a_real_tallied_failure_not_a_crash(pool, user_id):
    result = await run_email_ingestion(
        pool, client_id="unused", client_secret="unused", encryption_key="unused", user_ids=["not-a-real-uuid", user_id]
    )
    assert result.users_failed == 1
    assert result.users_skipped_no_token == 1  # the real, valid user_id has no real Google token stored
    assert result.already_running is False


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


async def test_run_email_ingestion_is_a_real_honest_no_op_when_a_previous_real_run_still_holds_the_job_lock(pool, user_id):
    """DEC-140 review finding H2: two overlapping real `pg_cron` fires
    must never both scan real users concurrently. A real, already-
    claimed `email_ingestion_job_lock` row makes the second,
    overlapping real run an honest, zero-cost no-op.

    Uses `_try_claim_job_lock`/`_release_job_lock` directly (not a raw
    advisory lock) -- the real, live-discovered PgBouncer-transaction-
    pooling reason those are the correct real primitive here is
    documented in `email_ingestion.py`'s own top-of-file docstring,
    review finding 3."""
    acquired = await _try_claim_job_lock(pool)
    assert acquired is True
    try:
        result = await run_email_ingestion(
            pool, client_id="unused", client_secret="unused", encryption_key="unused", user_ids=[user_id]
        )
        assert result.already_running is True
        assert (result.users_scanned, result.users_failed, result.new_sent_messages) == (0, 0, 0)
    finally:
        await _release_job_lock(pool)


async def test_run_email_ingestion_proceeds_normally_once_the_real_job_lock_is_free(pool, user_id):
    result = await run_email_ingestion(
        pool, client_id="unused", client_secret="unused", encryption_key="unused", user_ids=[user_id]
    )
    assert result.already_running is False


async def test_run_email_ingestion_self_heals_a_real_stale_lock_left_by_a_crashed_previous_run(pool, user_id):
    """A real crash mid-batch (a Cloud Run OOM-kill, a deploy restart)
    must never wedge this job forever. A claim older than `EMAIL_
    INGESTION_JOB_LOCK_STALE_AFTER_SECONDS` is genuinely stale and must
    be reclaimable."""
    from quorum_backend.features.email_ingestion import EMAIL_INGESTION_JOB_LOCK_STALE_AFTER_SECONDS

    await pool.execute(
        "UPDATE email_ingestion_job_lock SET running = true, started_at = now() - ($1 * interval '1 second') WHERE singleton = true",
        EMAIL_INGESTION_JOB_LOCK_STALE_AFTER_SECONDS + 60,
    )
    try:
        result = await run_email_ingestion(
            pool, client_id="unused", client_secret="unused", encryption_key="unused", user_ids=[user_id]
        )
        assert result.already_running is False
    finally:
        await _release_job_lock(pool)


# --- Real, live capstone test (Rule 5) ---


async def test_scan_one_user_email_a_real_genuine_send_is_genuinely_detected_end_to_end(pool):
    """The real capstone: sends a genuine email through Gmail's real,
    live API using this project's own dedicated sandbox account
    (`quorum.dev.sandbox@gmail.com`, `DEC-139`), then proves this
    module's real, live polling detects it -- the first real, live,
    non-manual proof of this entire pipeline, matching `QUORUM_
    PRODUCTION_COMPLETION_PLAN.md`'s own Phase 4 verification bar.

    Cleans up every real `sent_messages` row this run itself adds (not
    just its own marker message) by diffing a before/after snapshot --
    a real, disclosed CRITICAL-tier review finding (`DEC-140`, M2): an
    earlier version of this test only deleted its own marker row,
    leaving every OTHER real message this scan recorded (this real
    account's genuine sent history, up to `MAX_MESSAGES_PER_POLL`)
    behind in the real, live, production database."""
    if not _HAS_REAL_GOOGLE_CONFIG:
        pytest.skip("no real Google OAuth config in this environment")

    import base64
    import uuid as uuid_module

    import httpx

    from quorum_backend.auth.google_token_store import get_valid_google_access_token

    settings = get_settings()
    row = await pool.fetchrow("SELECT user_id FROM google_oauth_tokens ORDER BY updated_at DESC LIMIT 1")
    if row is None:
        pytest.skip("no real, live Google token stored in this environment (see DEC-139)")
    real_user_id = str(row["user_id"])

    pre_existing_ids = {
        r["message_id"] for r in await pool.fetch("SELECT message_id FROM sent_messages WHERE user_id = $1", uuid.UUID(real_user_id))
    }

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

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            send_response = await client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                json={"raw": encoded},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert send_response.status_code == 200
            sent_message_id = send_response.json()["id"]

            outcome, new_sent, new_replies, messages_failed = await scan_one_user_email(
                pool, user_id=real_user_id, client_id=settings.google_oauth_client_id,
                client_secret=settings.google_oauth_client_secret, encryption_key=settings.google_token_encryption_key,
                http_client=client,
            )

        assert outcome is ScanOutcome.SCANNED
        assert new_sent >= 1
        assert new_replies == 0  # the real, self-sent copy must never be mistaken for its own reply
        assert messages_failed == 0

        row = await pool.fetchrow(
            "SELECT subject, replied_at FROM sent_messages WHERE user_id = $1 AND message_id = $2",
            uuid.UUID(real_user_id), sent_message_id,
        )
        assert row is not None
        assert marker in row["subject"]
        assert row["replied_at"] is None
    finally:
        post_run_ids = {
            r["message_id"] for r in await pool.fetch("SELECT message_id FROM sent_messages WHERE user_id = $1", uuid.UUID(real_user_id))
        }
        newly_added_ids = list(post_run_ids - pre_existing_ids)
        if newly_added_ids:
            await pool.execute(
                "DELETE FROM sent_messages WHERE user_id = $1 AND message_id = ANY($2)",
                uuid.UUID(real_user_id), newly_added_ids,
            )
