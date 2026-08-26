"""Real tests for features/honesty_log.py (Phase 6, DEC-145)."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.features.honesty_log import HonestyFeed, build_honesty_feed, fetch_honesty_feed


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-honesty-log-{uuid.uuid4()}"
    uid = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield uid
    await pool.execute("DELETE FROM action_events WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(uid))


# --- _describe_action / build_honesty_feed: pure ---


def test_build_honesty_feed_an_empty_list_is_a_real_honest_no_data_state():
    feed = build_honesty_feed([])
    assert feed == HonestyFeed(total=0, success_rate=None, successes=[], failures_and_catches=[], genuinely_uncertain=[])


def test_build_honesty_feed_all_successes_is_a_real_100_percent_rate():
    now = datetime.now(timezone.utc)
    rows = [
        ("a1", now, "approved_unchanged", "create_task", {"title": "Write report"}),
        ("a2", now, "approved_unchanged", "log_expense", {"payee": "Store", "amount": 12.5}),
    ]
    feed = build_honesty_feed(rows)
    assert feed.total == 2
    assert feed.success_rate == 1.0
    assert len(feed.successes) == 2
    assert feed.failures_and_catches == []
    assert feed.genuinely_uncertain == []


def test_build_honesty_feed_caught_by_gate_and_corrected_by_user_both_land_in_failures_and_catches():
    now = datetime.now(timezone.utc)
    rows = [
        ("a1", now, "caught_by_gate", "send_email", {"to": "a@x.com"}),
        ("a2", now, "corrected_by_user", "log_expense", {"payee": "Store", "amount": 5.0}),
    ]
    feed = build_honesty_feed(rows)
    assert feed.total == 2
    assert feed.success_rate == 0.0
    assert {a.outcome for a in feed.failures_and_catches} == {"caught_by_gate", "corrected_by_user"}


def test_build_honesty_feed_uncertain_no_data_is_excluded_from_total_and_rate():
    """The real, load-bearing distinction this module exists to
    preserve, matching `trust_digest.py`'s own established precedent:
    "we don't know" must never be collapsed into "it failed" by
    counting it in the denominator."""
    now = datetime.now(timezone.utc)
    rows = [
        ("a1", now, "approved_unchanged", "create_task", {"title": "x"}),
        ("a2", now, "uncertain_no_data", "send_email", {"to": "a@x.com"}),
    ]
    feed = build_honesty_feed(rows)
    assert feed.total == 1  # the uncertain row is NOT counted
    assert feed.success_rate == 1.0  # NOT 0.5 -- the uncertain row is excluded from the denominator too
    assert len(feed.genuinely_uncertain) == 1


def test_build_honesty_feed_a_real_all_uncertain_feed_has_a_real_honest_null_rate():
    now = datetime.now(timezone.utc)
    rows = [("a1", now, "uncertain_no_data", "send_email", {"to": "a@x.com"})]
    feed = build_honesty_feed(rows)
    assert feed.total == 0
    assert feed.success_rate is None  # genuinely no data to compute a rate FROM, never a real 0.0
    assert len(feed.genuinely_uncertain) == 1


def test_build_honesty_feed_describes_a_real_create_task():
    feed = build_honesty_feed([("a1", datetime.now(timezone.utc), "approved_unchanged", "create_task", {"title": "Write report"})])
    assert feed.successes[0].description == "Created task: Write report"


def test_build_honesty_feed_describes_a_real_log_expense_with_and_without_an_amount():
    now = datetime.now(timezone.utc)
    feed = build_honesty_feed([
        ("a1", now, "approved_unchanged", "log_expense", {"payee": "Store", "amount": 12.5}),
        ("a2", now, "approved_unchanged", "log_expense", {"payee": None, "amount": None}),
    ])
    assert feed.successes[0].description == "Logged expense: Store ($12.5)"
    assert feed.successes[1].description == "Logged expense: an unknown payee"


def test_build_honesty_feed_describes_real_email_actions():
    now = datetime.now(timezone.utc)
    feed = build_honesty_feed([
        ("a1", now, "approved_unchanged", "send_email", {"to": "a@x.com"}),
        ("a2", now, "approved_unchanged", "archive_email", {"message_id": "m1"}),
        ("a3", now, "approved_unchanged", "label_email", {"message_id": "m1", "label_id": "IMPORTANT"}),
    ])
    assert feed.successes[0].description == "Sent an email to a@x.com"
    assert feed.successes[1].description == "Archived an email"
    assert feed.successes[2].description == "Labeled an email"


def test_build_honesty_feed_a_genuinely_unrecognized_action_type_gets_an_honest_generic_description():
    """A real, open-vocabulary fallback -- never raises on a real
    ActionType this module doesn't have a specific sentence for."""
    feed = build_honesty_feed([("a1", datetime.now(timezone.utc), "approved_unchanged", "update_budget", {})])
    assert feed.successes[0].description == "Update budget"


def test_build_honesty_feed_a_real_unrecognized_outcome_is_dropped_not_crashed():
    """A defensive fallback for an outcome value the real schema's own
    CHECK constraint should make unreachable in practice -- confirmed
    here it's a real, silent skip, not a crash."""
    feed = build_honesty_feed([("a1", datetime.now(timezone.utc), "some_future_outcome", "create_task", {})])
    assert feed.total == 0
    assert feed.successes == []
    assert feed.failures_and_catches == []
    assert feed.genuinely_uncertain == []


# --- fetch_honesty_feed: real, live database ---


async def test_fetch_honesty_feed_real_per_user_scoping_and_ordering(pool, user_id):
    now = datetime.now(timezone.utc)
    older = uuid.uuid4()
    newer = uuid.uuid4()
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)",
        older, "create_task", "S1", '{"title": "Older task"}', "approve", "approved_unchanged",
        f"trace-{older}", uuid.UUID(user_id), now - timedelta(hours=2),
    )
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)",
        newer, "log_expense", "S1", '{"payee": "Store", "amount": 9.0}', "approve", "caught_by_gate",
        f"trace-{newer}", uuid.UUID(user_id), now - timedelta(minutes=5),
    )

    feed = await fetch_honesty_feed(pool, user_id=user_id)

    assert feed.total == 2
    # Real, most-recent-first ordering across the whole real feed.
    assert feed.failures_and_catches[0].action_id == str(newer)
    assert feed.successes[0].action_id == str(older)


async def test_fetch_honesty_feed_never_leaks_another_real_users_rows(pool, user_id):
    other_google_sub = f"test-honesty-log-bystander-{uuid.uuid4()}"
    other_user_id = await get_or_create_user(pool, google_sub=other_google_sub, email=None)
    proposal_id = uuid.uuid4()
    try:
        await pool.execute(
            "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at) "
            "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)",
            proposal_id, "create_task", "S1", '{"title": "Bystander task"}', "approve", "approved_unchanged",
            f"trace-{proposal_id}", uuid.UUID(other_user_id), datetime.now(timezone.utc),
        )

        feed = await fetch_honesty_feed(pool, user_id=user_id)

        assert feed.total == 0
        assert str(proposal_id) not in [a.action_id for a in feed.successes]
    finally:
        await pool.execute("DELETE FROM action_events WHERE user_id = $1", uuid.UUID(other_user_id))
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(other_user_id))


async def test_fetch_honesty_feed_excludes_a_real_still_unresolved_escalation(pool, user_id):
    """A real `escalate_to_human` row with no real outcome yet (nobody
    has acted on it) must never appear in any bucket -- it isn't
    resolved, so it isn't logged yet, matching `outcome IS NOT NULL`'s
    own real, deliberate filter."""
    proposal_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)",
        proposal_id, "send_email", "S3", '{"to": "a@x.com"}', "escalate_to_human", None,
        f"trace-{proposal_id}", uuid.UUID(user_id), None,
    )

    feed = await fetch_honesty_feed(pool, user_id=user_id)

    assert feed.total == 0
    assert feed.genuinely_uncertain == []
