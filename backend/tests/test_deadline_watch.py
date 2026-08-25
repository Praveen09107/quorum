"""Real tests for features/deadline_watch.py (Phase 2, DEC-13x) -- real,
live-database integration tests proving the real per-user scan, real
claim/domain-state construction, real trigger, and real idempotency
guard, all against real Postgres rows, per CLAUDE.md Rule 5. No LLM
calls anywhere in this module's own real logic, so no fake call
injection is needed here (unlike test_retry_queue_drainer.py).

A REAL, DELIBERATE SAFETY BOUNDARY, DISCLOSED HERE: every test below
either calls `scan_one_user()` directly, or calls `run_deadline_watch()`
with its `user_ids` explicitly scoped to specific, cleaned-up test-only
rows -- the real, live default (`user_ids=None`, the whole `users`
table) is never exercised here. Unlike `drain_due_jobs()` (`test_
retry_queue_drainer.py`), which only ever processes rows a test
explicitly enqueued into a real, naturally-empty `retry_queue`, an
unscoped `run_deadline_watch()` would touch the ENTIRE real `users`
table -- including this deployment's one real, live, non-test account
(`scripts/seed_demo_dataset.py`'s own established fact) -- risking a
real, unwanted write against real, production-meaningful data as a
side effect of running this test suite. `test_main.py`'s route-level
test covers the real, unscoped default path separately, via a
monkeypatched `run_deadline_watch()`, never a real, whole-table call
either.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.features.deadline_watch import ScanOutcome, run_deadline_watch, scan_one_user


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-deadline-watch-{uuid.uuid4()}"
    uid = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield uid
    await pool.execute("DELETE FROM negotiations WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM tasks WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM expenses WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(uid))


async def _seed_task(
    pool, *, user_id: str, hours: float, deadline_offset_days: int | None = None,
    deadline: datetime | None = None, status: str = "open",
) -> None:
    if deadline is None:
        deadline = datetime.now(timezone.utc) + timedelta(days=deadline_offset_days)
    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, $5, $6)",
        uuid.uuid4(), uuid.UUID(user_id), "real test task", hours, deadline, status,
    )


async def _seed_expense(pool, *, user_id: str, amount: float, occurred_days_ago: int = 0) -> None:
    now = datetime.now(timezone.utc)
    await pool.execute(
        "INSERT INTO expenses (expense_id, user_id, payee, amount, occurred_at, source) VALUES ($1, $2, $3, $4, $5, $6)",
        uuid.uuid4(), uuid.UUID(user_id), "real test payee", amount, now - timedelta(days=occurred_days_ago), "manual",
    )


async def test_scan_one_user_returns_no_claim_when_no_real_task_has_a_future_deadline(pool, user_id):
    # A real, done task with a past deadline -- genuinely no real, open,
    # future commitment to build a claim from.
    await _seed_task(pool, user_id=user_id, hours=2.0, deadline_offset_days=-3, status="done")

    async with pool.acquire() as conn:
        outcome, negotiation_id = await scan_one_user(conn, user_id=user_id)

    assert outcome is ScanOutcome.NO_CLAIM
    assert negotiation_id is None


async def test_scan_one_user_returns_no_conflict_for_real_light_commitments(pool, user_id):
    # A real task due in 5 real days needing only 2 hours -- 5 * 8.0 = 40
    # real available hours, genuinely not exceeded. A small real expense,
    # genuinely nowhere near half the real monthly budget.
    await _seed_task(pool, user_id=user_id, hours=2.0, deadline_offset_days=5)
    await _seed_expense(pool, user_id=user_id, amount=100.0)

    async with pool.acquire() as conn:
        outcome, negotiation_id = await scan_one_user(conn, user_id=user_id)

    assert outcome is ScanOutcome.NO_CONFLICT
    assert negotiation_id is None

    row = await pool.fetchrow("SELECT 1 FROM negotiations WHERE user_id = $1", uuid.UUID(user_id))
    assert row is None


async def test_scan_one_user_creates_a_real_negotiation_for_a_genuine_conflict(pool, user_id):
    # A real task due tomorrow (1 real day -> 8.0 real available hours)
    # needing 12 real hours -- genuinely exceeds real available capacity.
    await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)
    # A real expense this real month exceeding half the 50000.0 real
    # monthly budget limit (30000 > 25000).
    await _seed_expense(pool, user_id=user_id, amount=30000.0)

    async with pool.acquire() as conn:
        outcome, negotiation_id = await scan_one_user(conn, user_id=user_id)

    assert outcome is ScanOutcome.CREATED
    assert negotiation_id is not None

    row = await pool.fetchrow(
        "SELECT user_id, conflicted_domains, resolved_at, positions, options FROM negotiations WHERE negotiation_id = $1",
        uuid.UUID(negotiation_id),
    )
    assert row is not None
    assert str(row["user_id"]) == user_id
    assert set(row["conflicted_domains"]) == {"tasks", "finance"}
    assert row["resolved_at"] is None
    # A real, honest, bare negotiation -- detail generation is a real,
    # separate, still-open item, not silently fabricated here.
    assert row["positions"] is None
    assert row["options"] is None


async def test_scan_one_user_skips_when_a_real_unresolved_negotiation_already_exists(pool, user_id):
    await pool.execute(
        "INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at, trigger_source) VALUES ($1, $2, $3, $4, $5)",
        uuid.uuid4(), uuid.UUID(user_id), ["finance", "tasks"], datetime.now(timezone.utc), "deadline_watch",
    )
    await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)
    await _seed_expense(pool, user_id=user_id, amount=30000.0)

    async with pool.acquire() as conn:
        outcome, negotiation_id = await scan_one_user(conn, user_id=user_id)

    assert outcome is ScanOutcome.ALREADY_NEGOTIATING
    assert negotiation_id is None

    count = await pool.fetchval("SELECT COUNT(*) FROM negotiations WHERE user_id = $1", uuid.UUID(user_id))
    assert count == 1  # never duplicated


async def test_scan_one_user_only_conflicts_tasks_domain_when_finance_is_genuinely_fine(pool, user_id):
    # Real overcommitted tasks, but real light spending -- a genuine
    # single-domain conflict never triggers a negotiation
    # (scan_for_conflicts requires 2+ conflicted domains by design).
    await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)
    await _seed_expense(pool, user_id=user_id, amount=100.0)

    async with pool.acquire() as conn:
        outcome, negotiation_id = await scan_one_user(conn, user_id=user_id)

    assert outcome is ScanOutcome.NO_CONFLICT
    assert negotiation_id is None


async def test_run_deadline_watch_scans_exactly_the_real_users_it_is_given_and_tallies_real_outcomes(pool, user_id):
    # A second, genuinely independent real test user, alongside the
    # fixture's own -- proves run_deadline_watch iterates every real
    # user IN ITS GIVEN SCOPE, not just the first one found. Scoped
    # explicitly to these two real, test-owned user_ids only -- see
    # this module's own top-of-file docstring for why the real,
    # whole-table default is never exercised here.
    other_google_sub = f"test-deadline-watch-{uuid.uuid4()}"
    other_user_id = await get_or_create_user(pool, google_sub=other_google_sub, email=None)
    try:
        await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)
        await _seed_expense(pool, user_id=user_id, amount=30000.0)
        # other_user_id gets no real tasks/expenses at all -- a real,
        # honest NO_CLAIM case.

        result = await run_deadline_watch(pool, user_ids=[user_id, other_user_id])

        assert result.users_scanned == 2
        assert result.users_failed == 0
        assert result.negotiations_created == 1
        assert result.outcome_counts["CREATED"] == 1
        assert result.outcome_counts["NO_CLAIM"] == 1

        row = await pool.fetchrow("SELECT 1 FROM negotiations WHERE user_id = $1", uuid.UUID(user_id))
        assert row is not None
    finally:
        await pool.execute("DELETE FROM negotiations WHERE user_id = $1", uuid.UUID(other_user_id))
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(other_user_id))


async def test_run_deadline_watch_a_real_failure_for_one_user_never_blocks_the_rest(pool, user_id):
    """Real regression test for the real bug this session's own
    adversarial self-review found and fixed, before any review
    subagent ran: a genuine per-user failure -- here, a real,
    malformed user_id causing a real `uuid.UUID()` ValueError inside
    `run_deadline_watch()`'s own `FOR UPDATE` lock line, before
    `scan_one_user()` is ever reached for that user -- must never
    abort the scan for every other real user in the same run. (This
    session's own CRITICAL-tier review found this docstring originally
    overstated where the real failure occurs -- corrected here; see
    `test_scan_one_user_negotiation_insert_rolls_back_if_the_same_
    transaction_later_fails` below for the real, separate proof that a
    failure occurring AFTER a real INSERT, within the same real
    transaction, also rolls back correctly.)"""
    await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)
    await _seed_expense(pool, user_id=user_id, amount=30000.0)

    result = await run_deadline_watch(pool, user_ids=["not-a-real-uuid", user_id])

    assert result.users_failed == 1
    assert result.users_scanned == 1  # only the real, valid user_id counts as genuinely scanned
    assert result.negotiations_created == 1
    assert result.outcome_counts["CREATED"] == 1

    row = await pool.fetchrow("SELECT 1 FROM negotiations WHERE user_id = $1", uuid.UUID(user_id))
    assert row is not None


async def test_run_deadline_watch_a_real_nonexistent_user_id_is_a_real_tallied_failure_not_a_silent_unlocked_scan(pool, user_id):
    """Real regression test for a second real bug this session's own
    CRITICAL-tier review found: a syntactically valid but genuinely
    nonexistent user_id previously made `run_deadline_watch()`'s own
    `SELECT ... FOR UPDATE` lock silently no-op (lock nothing, return
    no row) and then continue scanning that user completely
    unserialized -- reachable live via this module's own `user_ids`
    scoping parameter. Fixed: a missing lock row now raises
    `DeadlineWatchUserNotFoundError`, caught by the same real per-user
    failure isolation as any other genuine failure."""
    ghost_user_id = str(uuid.uuid4())  # syntactically real, genuinely no real users row
    await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)
    await _seed_expense(pool, user_id=user_id, amount=30000.0)

    result = await run_deadline_watch(pool, user_ids=[ghost_user_id, user_id])

    assert result.users_failed == 1
    assert result.users_scanned == 1
    assert result.negotiations_created == 1

    row = await pool.fetchrow("SELECT 1 FROM negotiations WHERE user_id = $1", uuid.UUID(ghost_user_id))
    assert row is None  # never created for a real, nonexistent user


async def test_scan_one_user_negotiation_insert_rolls_back_if_the_same_transaction_later_fails(pool, user_id):
    """Real, direct proof of the real transaction-boundary property
    `run_deadline_watch()` itself relies on: a genuine failure AFTER
    `scan_one_user()`'s own real negotiation INSERT, but still within
    the same real transaction, correctly rolls back that insert --
    never leaving an orphaned, un-tallied negotiation row behind. This
    session's own CRITICAL-tier review found the existing regression
    test above only covered a failure BEFORE any real work happened;
    this test covers the other, more consequential half directly,
    using the exact same real transaction pattern `run_deadline_
    watch()` itself uses."""
    await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)
    await _seed_expense(pool, user_id=user_id, amount=30000.0)

    with pytest.raises(RuntimeError, match="simulated real failure"):
        async with pool.acquire() as conn:
            async with conn.transaction():
                outcome, negotiation_id = await scan_one_user(conn, user_id=user_id)
                assert outcome is ScanOutcome.CREATED
                assert negotiation_id is not None
                raise RuntimeError("simulated real failure after a real INSERT, same transaction")

    row = await pool.fetchrow("SELECT 1 FROM negotiations WHERE user_id = $1", uuid.UUID(user_id))
    assert row is None  # genuinely rolled back, never persisted


async def test_scan_one_user_a_same_day_deadline_uses_a_real_full_working_day_not_zero(pool, user_id):
    """Real regression test for a second real bug this session's own
    CRITICAL-tier review found: a task due later TODAY previously
    computed zero real available hours (`available_hours_before_
    deadline`'s own same-day behavior, correct for `retry_queue_
    drainer.py`'s different real use case but wrong for this module's),
    causing a real false-positive conflict for even a tiny, 1-hour
    same-day task. A light, 1-hour same-day task with light real
    spending must NOT trigger a negotiation. Real, deliberate headroom
    (6 hours out, not `deadline_offset_days=0`, which computes to
    "right now" and can race `_fetch_nearest_upcoming_task_deadline`'s
    own `deadline > now()` filter by the time the query actually
    runs -- a real timing bug this session's own test run caught
    directly, not a hypothetical)."""
    await _seed_task(pool, user_id=user_id, hours=1.0, deadline=datetime.now(timezone.utc) + timedelta(hours=6))
    await _seed_expense(pool, user_id=user_id, amount=100.0)

    async with pool.acquire() as conn:
        outcome, negotiation_id = await scan_one_user(conn, user_id=user_id)

    assert outcome is ScanOutcome.NO_CONFLICT
    assert negotiation_id is None


async def test_scan_one_user_a_real_stale_bare_negotiation_does_not_block_a_new_genuine_one_forever(pool, user_id):
    """Real regression test for the most severe real bug this session's
    own CRITICAL-tier review found: an earlier version treated ANY
    unresolved negotiation as blocking a new one -- but a bare
    negotiation (no real options) can NEVER become resolved through any
    real code path in this backend (`features/negotiation_choice.py`
    requires real options to choose), live-proven to PERMANENTLY
    silence this trigger for a real user after its very first firing.
    A negotiation started well outside `BARE_NEGOTIATION_COOLDOWN_HOURS`
    ago, still bare, must NOT block a new, genuine detection."""
    stale_negotiation_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at, trigger_source) VALUES ($1, $2, $3, $4, $5)",
        stale_negotiation_id, uuid.UUID(user_id), ["finance", "tasks"],
        datetime.now(timezone.utc) - timedelta(hours=48), "deadline_watch",
    )
    await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)
    await _seed_expense(pool, user_id=user_id, amount=30000.0)

    async with pool.acquire() as conn:
        outcome, negotiation_id = await scan_one_user(conn, user_id=user_id)

    assert outcome is ScanOutcome.CREATED
    assert negotiation_id is not None
    assert negotiation_id != str(stale_negotiation_id)

    count = await pool.fetchval("SELECT COUNT(*) FROM negotiations WHERE user_id = $1", uuid.UUID(user_id))
    assert count == 2  # the real, stale bare one, plus this new, genuine one


async def test_scan_one_user_a_real_negotiation_with_real_options_blocks_unconditionally_even_if_stale(pool, user_id):
    """Real, complementary proof: unlike a bare negotiation, one with
    real options (genuinely actionable, truly awaiting the user's real
    choice) blocks a new one unconditionally -- age never matters,
    since the user genuinely still has something real to act on."""
    await pool.execute(
        "INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at, options, trigger_source) "
        "VALUES ($1, $2, $3, $4, $5::jsonb, $6)",
        uuid.uuid4(), uuid.UUID(user_id), ["finance", "tasks"],
        datetime.now(timezone.utc) - timedelta(hours=48),
        '[{"option_id": "do_nothing", "description": "Do nothing.", "source_domains": []}]',
        "deadline_watch",
    )
    await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)
    await _seed_expense(pool, user_id=user_id, amount=30000.0)

    async with pool.acquire() as conn:
        outcome, negotiation_id = await scan_one_user(conn, user_id=user_id)

    assert outcome is ScanOutcome.ALREADY_NEGOTIATING
    assert negotiation_id is None

    count = await pool.fetchval("SELECT COUNT(*) FROM negotiations WHERE user_id = $1", uuid.UUID(user_id))
    assert count == 1  # never duplicated


async def test_scan_one_user_a_fresh_negotiation_from_a_different_real_trigger_source_never_blocks(pool, user_id):
    """Real, direct proof of this session's own cross-job isolation
    fix: a fresh, genuinely unresolved negotiation created by a
    DIFFERENT real autonomous job (`spend_alert:Netflix`, this
    session's own new module) must never block `deadline_watch`'s own,
    genuinely unrelated real conflict from being detected -- the exact
    real gap `features/negotiation_trigger_support.py`'s own top-of-
    file docstring discloses fixing, proven here for real."""
    await pool.execute(
        "INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at, trigger_source) VALUES ($1, $2, $3, $4, $5)",
        uuid.uuid4(), uuid.UUID(user_id), ["finance", "tasks"], datetime.now(timezone.utc), "spend_alert:Netflix",
    )
    await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)
    await _seed_expense(pool, user_id=user_id, amount=30000.0)

    async with pool.acquire() as conn:
        outcome, negotiation_id = await scan_one_user(conn, user_id=user_id)

    assert outcome is ScanOutcome.CREATED
    assert negotiation_id is not None

    count = await pool.fetchval("SELECT COUNT(*) FROM negotiations WHERE user_id = $1", uuid.UUID(user_id))
    assert count == 2  # the real spend_alert one, plus this new, genuine deadline_watch one
