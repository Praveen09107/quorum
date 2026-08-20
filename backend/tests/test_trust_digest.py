"""Real tests for features/trust_digest.py.

The tests below `# --- Real, live database tests` run against the real,
live Supabase database (`DEC-098`) -- real INSERTs, a real query, real
DELETEs in a `finally` block, per `CLAUDE.md` Rule 5 ("real Postgres...
never mocks, when the point is proving an integration works"). Every
inserted row uses a fixed, deliberately obscure date far outside any
real usage of this project, and is deleted by its own generated
`proposal_id`s -- these tests can never collide with real data and never
leave anything behind, even if a test itself fails midway.
"""
import uuid
from datetime import date, datetime, timezone

import pytest_asyncio

from quorum_backend.core import db
from quorum_backend.features.trust_digest import (
    STABLE_THRESHOLD,
    WeeklyTrustSummary,
    aggregate_weekly_summary,
    compare_weeks,
    fetch_trust_digest,
)


def test_improving_trend_detected_above_threshold():
    current = WeeklyTrustSummary(week_start="2026-08-10", total_actions=24, success_rate=0.875)
    previous = WeeklyTrustSummary(week_start="2026-08-03", total_actions=19, success_rate=0.789)
    result = compare_weeks(current, previous)
    assert result.trend == "improving"
    assert result.delta is not None and result.delta > STABLE_THRESHOLD


def test_declining_trend_detected_below_negative_threshold():
    current = WeeklyTrustSummary(week_start="2026-08-10", total_actions=20, success_rate=0.70)
    previous = WeeklyTrustSummary(week_start="2026-08-03", total_actions=20, success_rate=0.90)
    result = compare_weeks(current, previous)
    assert result.trend == "declining"
    assert result.delta is not None and result.delta < -STABLE_THRESHOLD


def test_stable_trend_within_threshold_band():
    current = WeeklyTrustSummary(week_start="2026-08-10", total_actions=20, success_rate=0.81)
    previous = WeeklyTrustSummary(week_start="2026-08-03", total_actions=20, success_rate=0.80)
    result = compare_weeks(current, previous)
    assert result.trend == "stable"


def test_exact_threshold_boundary_is_classified_as_stable_not_improving():
    # Real, live-confirmed floating-point safety: 0.80 + STABLE_THRESHOLD
    # produces 0.8200000000000001 in raw floating point; round(..., 3)
    # cleanly resolves this to exactly STABLE_THRESHOLD, confirmed before
    # writing this test.
    previous = WeeklyTrustSummary(week_start="2026-08-03", total_actions=20, success_rate=0.80)
    current = WeeklyTrustSummary(week_start="2026-08-10", total_actions=20, success_rate=0.80 + STABLE_THRESHOLD)
    result = compare_weeks(current, previous)
    assert result.delta == STABLE_THRESHOLD
    assert result.trend == "stable", "a delta exactly AT the threshold must not count as a real improvement"


def test_no_previous_week_is_insufficient_data():
    current = WeeklyTrustSummary(week_start="2026-08-10", total_actions=24, success_rate=0.875)
    result = compare_weeks(current, None)
    assert result.trend == "insufficient_data"
    assert result.delta is None


def test_previous_week_with_zero_actions_is_insufficient_data():
    current = WeeklyTrustSummary(week_start="2026-08-10", total_actions=24, success_rate=0.875)
    previous = WeeklyTrustSummary(week_start="2026-08-03", total_actions=0, success_rate=0.0)
    result = compare_weeks(current, previous)
    assert result.trend == "insufficient_data"


def test_current_week_with_zero_actions_is_insufficient_data():
    current = WeeklyTrustSummary(week_start="2026-08-10", total_actions=0, success_rate=0.0)
    previous = WeeklyTrustSummary(week_start="2026-08-03", total_actions=19, success_rate=0.789)
    result = compare_weeks(current, previous)
    assert result.trend == "insufficient_data"


# --- Real, live database tests -------------------------------------------


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


async def _insert_test_event(pool, proposal_id, outcome, resolved_at, *, has_resolved_at=True):
    # A real, generated user_id -- required as of migration 0004
    # (DEC-119), added for GET /today's real per-user scoping needs.
    # /trust_digest's own real query still doesn't filter by it (the
    # same disclosed, unchanged limitation since DEC-101) -- any real,
    # valid UUID satisfies the column's NOT NULL constraint here.
    await pool.execute(
        """
        INSERT INTO action_events
            (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, created_at, resolved_at, user_id)
        VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9, $10)
        """,
        proposal_id,
        "create_note",
        "S0",
        "{}",
        "approve",
        outcome,
        f"test-trust-digest-{proposal_id}",
        resolved_at,
        resolved_at if has_resolved_at else None,
        uuid.uuid4(),
    )


async def test_aggregate_weekly_summary_counts_real_rows_and_excludes_uncertain(pool):
    # 2020-01-06 is a real Monday -- deliberately far outside any real
    # usage of this project, so this test can never collide with real
    # production data.
    week_start = date(2020, 1, 6)
    resolved_at = datetime(2020, 1, 7, 12, 0, tzinfo=timezone.utc)
    ids = [uuid.uuid4() for _ in range(4)]
    outcomes = ["approved_unchanged", "approved_unchanged", "caught_by_gate", "uncertain_no_data"]

    try:
        for proposal_id, outcome in zip(ids, outcomes):
            await _insert_test_event(pool, proposal_id, outcome, resolved_at)

        summary = await aggregate_weekly_summary(pool, week_start)

        assert summary.week_start == "2020-01-06"
        # 4 rows inserted, but uncertain_no_data is excluded from
        # total_actions -- the real point of this test.
        assert summary.total_actions == 3
        assert summary.success_rate == round(2 / 3, 3)
    finally:
        await pool.execute("DELETE FROM action_events WHERE proposal_id = ANY($1::uuid[])", ids)


async def test_aggregate_weekly_summary_falls_back_to_created_at_when_resolved_at_is_null(pool):
    # The schema doesn't enforce resolved_at being set alongside outcome
    # -- a real, defensive case this query's COALESCE exists to handle.
    week_start = date(2020, 1, 6)
    created_at = datetime(2020, 1, 8, 9, 0, tzinfo=timezone.utc)
    proposal_id = uuid.uuid4()

    try:
        await _insert_test_event(pool, proposal_id, "approved_unchanged", created_at, has_resolved_at=False)

        summary = await aggregate_weekly_summary(pool, week_start)

        assert summary.total_actions == 1
        assert summary.success_rate == 1.0
    finally:
        await pool.execute("DELETE FROM action_events WHERE proposal_id = $1", proposal_id)


async def test_aggregate_weekly_summary_with_no_real_rows_is_a_real_honest_zero(pool):
    # 1999-01-04 is a real Monday nothing in this project has ever
    # written test data against.
    summary = await aggregate_weekly_summary(pool, date(1999, 1, 4))
    assert summary.total_actions == 0
    assert summary.success_rate == 0.0


async def test_fetch_trust_digest_end_to_end_against_the_real_database(pool):
    # this_week_start = 2020-01-20 (a real Monday); last_week_start = 2020-01-13.
    today = date(2020, 1, 22)
    this_week_resolved = datetime(2020, 1, 21, 10, 0, tzinfo=timezone.utc)
    last_week_resolved = datetime(2020, 1, 14, 10, 0, tzinfo=timezone.utc)

    this_week_ids = [uuid.uuid4(), uuid.uuid4()]
    last_week_ids = [uuid.uuid4(), uuid.uuid4()]
    all_ids = this_week_ids + last_week_ids

    try:
        # This week: 2/2 approved -- success_rate 1.0.
        for proposal_id in this_week_ids:
            await _insert_test_event(pool, proposal_id, "approved_unchanged", this_week_resolved)
        # Last week: 1 approved, 1 caught -- success_rate 0.5.
        await _insert_test_event(pool, last_week_ids[0], "approved_unchanged", last_week_resolved)
        await _insert_test_event(pool, last_week_ids[1], "caught_by_gate", last_week_resolved)

        result = await fetch_trust_digest(pool, today=today)

        assert result.current_week.week_start == "2020-01-20"
        assert result.current_week.total_actions == 2
        assert result.current_week.success_rate == 1.0
        assert result.previous_week is not None
        assert result.previous_week.week_start == "2020-01-13"
        assert result.previous_week.success_rate == 0.5
        assert result.trend == "improving"
        assert result.delta == round(1.0 - 0.5, 3)
    finally:
        await pool.execute("DELETE FROM action_events WHERE proposal_id = ANY($1::uuid[])", all_ids)
