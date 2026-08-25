"""Real tests for features/spend_alert.py (Phase 2, DEC-13x) -- real,
live-database integration tests, mirroring test_deadline_watch.py's
own established real pattern exactly: real Postgres rows, real
`scan_one_user()`/`run_spend_alert()` calls, and the exact same real
test-safety boundary (`run_spend_alert()`'s own real, live default --
the whole real `users` table -- is never exercised here; every call
either uses `scan_one_user()` directly or an explicit, test-owned
`user_ids` list). See that file's own top-of-file docstring for the
full real reasoning, not repeated here.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.features.spend_alert import ScanOutcome, run_spend_alert, scan_one_user


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-spend-alert-{uuid.uuid4()}"
    uid = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield uid
    await pool.execute("DELETE FROM negotiations WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM tasks WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM expenses WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(uid))


async def _seed_task(pool, *, user_id: str, hours: float, deadline_offset_days: int, status: str = "open") -> None:
    now = datetime.now(timezone.utc)
    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, $5, $6)",
        uuid.uuid4(), uuid.UUID(user_id), "real test task", hours,
        now + timedelta(days=deadline_offset_days), status,
    )


async def _seed_expense(pool, *, user_id: str, payee: str, amount: float, occurred_days_ago: int) -> None:
    now = datetime.now(timezone.utc)
    await pool.execute(
        "INSERT INTO expenses (expense_id, user_id, payee, amount, occurred_at, source) VALUES ($1, $2, $3, $4, $5, $6)",
        uuid.uuid4(), uuid.UUID(user_id), payee, amount, now - timedelta(days=occurred_days_ago), "manual",
    )


async def _seed_real_recurring_subscription(pool, *, user_id: str, payee: str, amount: float) -> None:
    # Real, detectable per subscription_detective.py's own real,
    # already-tested parameters (MIN_OCCURRENCES_TO_COUNT_AS_RECURRING
    # = 3, INTERVAL_TARGET_DAYS = 30.0, INTERVAL_TOLERANCE_DAYS = 5.0)
    # -- three real charges, 30 real days apart, the same real pattern
    # scripts/seed_demo_dataset.py's own real Spotify data already used.
    for offset in (60, 30, 0):
        await _seed_expense(pool, user_id=user_id, payee=payee, amount=amount, occurred_days_ago=offset)


async def test_scan_one_user_returns_no_claim_when_no_real_subscription_is_detected(pool, user_id):
    # A real, one-off expense only -- genuinely not recurring (fewer
    # than subscription_detective.py's own real MIN_OCCURRENCES = 3).
    await _seed_expense(pool, user_id=user_id, payee="OneOff", amount=500.0, occurred_days_ago=0)

    async with pool.acquire() as conn:
        outcome, negotiation_id = await scan_one_user(conn, user_id=user_id)

    assert outcome is ScanOutcome.NO_CLAIM
    assert negotiation_id is None


async def test_scan_one_user_returns_no_conflict_for_a_real_light_subscription(pool, user_id):
    # A real, genuinely detected, light recurring subscription (₹199,
    # matching scripts/seed_demo_dataset.py's own real Spotify value) --
    # nowhere near a real ₹50000 remaining budget, and no real tasks
    # overcommitment either.
    await _seed_real_recurring_subscription(pool, user_id=user_id, payee="Spotify", amount=199.0)

    async with pool.acquire() as conn:
        outcome, negotiation_id = await scan_one_user(conn, user_id=user_id)

    assert outcome is ScanOutcome.NO_CONFLICT
    assert negotiation_id is None


async def test_scan_one_user_creates_a_real_negotiation_for_a_genuine_conflict(pool, user_id):
    # A real, detected recurring subscription (₹5000) plus a real,
    # separate one-off expense THIS real month (₹46000) -- together
    # genuinely exceed the real ₹50000 monthly budget regardless of
    # which real calendar day this test runs on (the -60/-30-day
    # occurrences may or may not fall in the current real month; the
    # ₹46000 one-off, seeded at day 0, always does). A real, genuinely
    # overcommitted task too.
    await _seed_real_recurring_subscription(pool, user_id=user_id, payee="Coworking", amount=5000.0)
    await _seed_expense(pool, user_id=user_id, payee="BigOneOff", amount=46000.0, occurred_days_ago=0)
    await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)

    async with pool.acquire() as conn:
        outcome, negotiation_id = await scan_one_user(conn, user_id=user_id)

    assert outcome is ScanOutcome.CREATED
    assert negotiation_id is not None

    row = await pool.fetchrow(
        "SELECT user_id, conflicted_domains, resolved_at, positions, options, trigger_source "
        "FROM negotiations WHERE negotiation_id = $1",
        uuid.UUID(negotiation_id),
    )
    assert row is not None
    assert str(row["user_id"]) == user_id
    assert set(row["conflicted_domains"]) == {"tasks", "finance"}
    assert row["resolved_at"] is None
    assert row["positions"] is None
    assert row["options"] is None
    assert row["trigger_source"] == "spend_alert:Coworking"


async def test_scan_one_user_uses_the_real_sum_of_every_detected_subscription_not_just_one(pool, user_id):
    # Two real, individually-modest recurring subscriptions whose real
    # SUM crosses the real remaining budget, even though neither alone
    # would -- proves the real claim is the total recurring burden, not
    # a single subscription's own amount.
    await _seed_real_recurring_subscription(pool, user_id=user_id, payee="Gym", amount=3000.0)
    await _seed_real_recurring_subscription(pool, user_id=user_id, payee="Cloud Storage", amount=2500.0)
    await _seed_expense(pool, user_id=user_id, payee="BigOneOff", amount=46000.0, occurred_days_ago=0)
    await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)

    async with pool.acquire() as conn:
        outcome, negotiation_id = await scan_one_user(conn, user_id=user_id)

    assert outcome is ScanOutcome.CREATED
    assert negotiation_id is not None
    # The real, deterministic anchor is the single MOST EXPENSIVE real
    # detected subscription (Gym, ₹3000 > Cloud Storage's ₹2500).
    row = await pool.fetchrow("SELECT trigger_source FROM negotiations WHERE negotiation_id = $1", uuid.UUID(negotiation_id))
    assert row["trigger_source"] == "spend_alert:Gym"


async def test_scan_one_user_skips_when_a_real_unresolved_negotiation_for_the_same_payee_already_exists(pool, user_id):
    await pool.execute(
        "INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at, trigger_source) VALUES ($1, $2, $3, $4, $5)",
        uuid.uuid4(), uuid.UUID(user_id), ["finance", "tasks"], datetime.now(timezone.utc), "spend_alert:Coworking",
    )
    await _seed_real_recurring_subscription(pool, user_id=user_id, payee="Coworking", amount=5000.0)
    await _seed_expense(pool, user_id=user_id, payee="BigOneOff", amount=46000.0, occurred_days_ago=0)
    await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)

    async with pool.acquire() as conn:
        outcome, negotiation_id = await scan_one_user(conn, user_id=user_id)

    assert outcome is ScanOutcome.ALREADY_NEGOTIATING
    assert negotiation_id is None

    count = await pool.fetchval("SELECT COUNT(*) FROM negotiations WHERE user_id = $1", uuid.UUID(user_id))
    assert count == 1  # never duplicated


async def test_scan_one_user_a_fresh_deadline_watch_negotiation_never_blocks_spend_alert(pool, user_id):
    """Real, complementary proof to test_deadline_watch.py's own
    cross-job isolation test (the reverse direction): a fresh, genuinely
    unresolved `deadline_watch`-created negotiation must never block
    `spend_alert`'s own, genuinely unrelated real concern."""
    await pool.execute(
        "INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at, trigger_source) VALUES ($1, $2, $3, $4, $5)",
        uuid.uuid4(), uuid.UUID(user_id), ["finance", "tasks"], datetime.now(timezone.utc), "deadline_watch",
    )
    await _seed_real_recurring_subscription(pool, user_id=user_id, payee="Coworking", amount=5000.0)
    await _seed_expense(pool, user_id=user_id, payee="BigOneOff", amount=46000.0, occurred_days_ago=0)
    await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)

    async with pool.acquire() as conn:
        outcome, negotiation_id = await scan_one_user(conn, user_id=user_id)

    assert outcome is ScanOutcome.CREATED
    assert negotiation_id is not None

    count = await pool.fetchval("SELECT COUNT(*) FROM negotiations WHERE user_id = $1", uuid.UUID(user_id))
    assert count == 2  # the real deadline_watch one, plus this new, genuine spend_alert one


async def test_run_spend_alert_scans_exactly_the_real_users_it_is_given_and_tallies_real_outcomes(pool, user_id):
    other_google_sub = f"test-spend-alert-{uuid.uuid4()}"
    other_user_id = await get_or_create_user(pool, google_sub=other_google_sub, email=None)
    try:
        await _seed_real_recurring_subscription(pool, user_id=user_id, payee="Coworking", amount=5000.0)
        await _seed_expense(pool, user_id=user_id, payee="BigOneOff", amount=46000.0, occurred_days_ago=0)
        await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)
        # other_user_id gets no real expenses at all -- a real, honest NO_CLAIM case.

        result = await run_spend_alert(pool, user_ids=[user_id, other_user_id])

        assert result.users_scanned == 2
        assert result.users_failed == 0
        assert result.negotiations_created == 1
        assert result.outcome_counts["CREATED"] == 1
        assert result.outcome_counts["NO_CLAIM"] == 1
    finally:
        await pool.execute("DELETE FROM negotiations WHERE user_id = $1", uuid.UUID(other_user_id))
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(other_user_id))


async def test_run_spend_alert_a_real_failure_for_one_user_never_blocks_the_rest(pool, user_id):
    await _seed_real_recurring_subscription(pool, user_id=user_id, payee="Coworking", amount=5000.0)
    await _seed_expense(pool, user_id=user_id, payee="BigOneOff", amount=46000.0, occurred_days_ago=0)
    await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)

    result = await run_spend_alert(pool, user_ids=["not-a-real-uuid", user_id])

    assert result.users_failed == 1
    assert result.users_scanned == 1
    assert result.negotiations_created == 1


async def test_run_spend_alert_a_real_nonexistent_user_id_is_a_real_tallied_failure(pool, user_id):
    ghost_user_id = str(uuid.uuid4())
    await _seed_real_recurring_subscription(pool, user_id=user_id, payee="Coworking", amount=5000.0)
    await _seed_expense(pool, user_id=user_id, payee="BigOneOff", amount=46000.0, occurred_days_ago=0)
    await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)

    result = await run_spend_alert(pool, user_ids=[ghost_user_id, user_id])

    assert result.users_failed == 1
    assert result.users_scanned == 1
    assert result.negotiations_created == 1

    row = await pool.fetchrow("SELECT 1 FROM negotiations WHERE user_id = $1", uuid.UUID(ghost_user_id))
    assert row is None


async def test_scan_one_user_negotiation_insert_rolls_back_if_the_same_transaction_later_fails(pool, user_id):
    await _seed_real_recurring_subscription(pool, user_id=user_id, payee="Coworking", amount=5000.0)
    await _seed_expense(pool, user_id=user_id, payee="BigOneOff", amount=46000.0, occurred_days_ago=0)
    await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)

    with pytest.raises(RuntimeError, match="simulated real failure"):
        async with pool.acquire() as conn:
            async with conn.transaction():
                outcome, negotiation_id = await scan_one_user(conn, user_id=user_id)
                assert outcome is ScanOutcome.CREATED
                assert negotiation_id is not None
                raise RuntimeError("simulated real failure after a real INSERT, same transaction")

    row = await pool.fetchrow("SELECT 1 FROM negotiations WHERE user_id = $1", uuid.UUID(user_id))
    assert row is None
