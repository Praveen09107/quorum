"""Real tests for features/predictive_risk.py (Phase 6, DEC-149) --
pure-logic unit tests for the real grouping/pooling math, plus real,
live-database integration tests for `fetch_risk_assessment()`, per
CLAUDE.md Rule 5.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.features.predictive_risk import (
    CORRECTION_RATE_THRESHOLD,
    DEADLINE_DENSITY_TOLERANCE,
    HistoricalWeek,
    _is_corrected,
    _week_start,
    assess_upcoming_week,
    compute_historical_weeks,
    fetch_risk_assessment,
)

_NOW = datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)  # a real, fixed Thursday


# --- Pure logic: _week_start / _is_corrected ---


def test_week_start_normalizes_to_a_real_monday_00_00_utc():
    # 2026-08-27 is a real Thursday.
    result = _week_start(_NOW)
    assert result == datetime(2026, 8, 24, 0, 0, tzinfo=timezone.utc)
    assert result.weekday() == 0


def test_week_start_a_real_monday_maps_to_itself():
    monday = datetime(2026, 8, 24, 9, 30, tzinfo=timezone.utc)
    assert _week_start(monday) == datetime(2026, 8, 24, 0, 0, tzinfo=timezone.utc)


def test_is_corrected_a_real_cancelled_task_is_corrected_regardless_of_deadline():
    task = {"status": "cancelled", "deadline": _NOW + timedelta(days=5)}
    assert _is_corrected(task, now=_NOW) is True


def test_is_corrected_a_real_open_task_past_its_own_deadline_is_corrected():
    task = {"status": "open", "deadline": _NOW - timedelta(days=1)}
    assert _is_corrected(task, now=_NOW) is True


def test_is_corrected_a_real_open_task_with_a_future_deadline_is_not_corrected():
    task = {"status": "open", "deadline": _NOW + timedelta(days=1)}
    assert _is_corrected(task, now=_NOW) is False


def test_is_corrected_a_real_done_task_is_never_corrected():
    task = {"status": "done", "deadline": _NOW - timedelta(days=1)}
    assert _is_corrected(task, now=_NOW) is False


# --- Pure logic: compute_historical_weeks ---


def test_compute_historical_weeks_excludes_the_real_current_and_future_weeks():
    current_week_task = {"deadline": _NOW, "status": "open"}
    future_week_task = {"deadline": _NOW + timedelta(weeks=2), "status": "open"}
    past_week_task = {"deadline": _NOW - timedelta(weeks=1), "status": "done"}

    weeks = compute_historical_weeks([current_week_task, future_week_task, past_week_task], now=_NOW)

    assert len(weeks) == 1
    assert weeks[0].total_count == 1


def test_compute_historical_weeks_groups_by_real_iso_week_and_counts_correctly():
    week1 = _NOW - timedelta(weeks=1)
    tasks = [
        {"deadline": week1, "status": "done"},
        {"deadline": week1 + timedelta(days=1), "status": "cancelled"},
        {"deadline": week1 + timedelta(days=2), "status": "done"},
    ]

    weeks = compute_historical_weeks(tasks, now=_NOW)

    assert len(weeks) == 1
    assert weeks[0].deadline_density == 3
    assert weeks[0].total_count == 3
    assert weeks[0].corrected_count == 1  # only the cancelled one
    assert weeks[0].correction_rate == 1 / 3


def test_compute_historical_weeks_ignores_a_real_task_with_no_deadline():
    tasks = [{"deadline": None, "status": "open"}, {"deadline": _NOW - timedelta(weeks=1), "status": "done"}]
    weeks = compute_historical_weeks(tasks, now=_NOW)
    assert len(weeks) == 1
    assert weeks[0].total_count == 1


def test_historical_week_correction_rate_is_a_real_honest_zero_for_an_empty_week():
    week = HistoricalWeek(week_start=_NOW, deadline_density=0, corrected_count=0, total_count=0)
    assert week.correction_rate == 0.0


# --- Pure logic: assess_upcoming_week ---


def test_assess_upcoming_week_flags_risk_when_the_real_pooled_rate_meets_the_real_threshold():
    weeks = [
        HistoricalWeek(week_start=_NOW, deadline_density=3, corrected_count=2, total_count=4),
        HistoricalWeek(week_start=_NOW, deadline_density=3, corrected_count=1, total_count=2),
    ]
    # Pooled: 3 corrected / 6 total = 0.5 -- exactly the real threshold.
    result = assess_upcoming_week(weeks, upcoming_deadline_density=3, upcoming_week_start=_NOW)
    assert result.pooled_correction_rate == 0.5
    assert result.is_at_risk is True
    assert result.matching_historical_weeks == 2


def test_assess_upcoming_week_does_not_flag_when_the_real_pooled_rate_is_below_threshold():
    weeks = [HistoricalWeek(week_start=_NOW, deadline_density=3, corrected_count=1, total_count=4)]
    result = assess_upcoming_week(weeks, upcoming_deadline_density=3, upcoming_week_start=_NOW)
    assert result.pooled_correction_rate == 0.25
    assert result.is_at_risk is False


def test_assess_upcoming_week_pools_weeks_within_the_real_tolerance_boundary():
    assert DEADLINE_DENSITY_TOLERANCE == 1  # this test's own real boundary math depends on this exact value
    weeks = [
        HistoricalWeek(week_start=_NOW, deadline_density=2, corrected_count=1, total_count=1),  # density diff 1 -- matches
        HistoricalWeek(week_start=_NOW, deadline_density=4, corrected_count=1, total_count=1),  # density diff 1 -- matches
        HistoricalWeek(week_start=_NOW, deadline_density=5, corrected_count=1, total_count=1),  # density diff 2 -- excluded
    ]
    result = assess_upcoming_week(weeks, upcoming_deadline_density=3, upcoming_week_start=_NOW)
    assert result.matching_historical_weeks == 2


def test_assess_upcoming_week_a_real_empty_pool_is_an_honest_no_data_case_not_a_fabricated_result():
    result = assess_upcoming_week([], upcoming_deadline_density=3, upcoming_week_start=_NOW)
    assert result.matching_historical_weeks == 0
    assert result.pooled_correction_rate is None  # honest "not enough real history," never a fake 0.0
    assert result.is_at_risk is False


def test_assess_upcoming_week_uses_the_real_specified_threshold_constant():
    assert CORRECTION_RATE_THRESHOLD == 0.5


# --- Real, live-database integration tests ---


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-predictive-risk-{uuid.uuid4()}"
    uid = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield uid
    await pool.execute("DELETE FROM tasks WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(uid))


async def _seed_task(pool, *, user_id: str, deadline: datetime | None, status: str) -> None:
    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, $5, $6)",
        uuid.uuid4(), uuid.UUID(user_id), "A real test task", 1.0, deadline, status,
    )


async def test_fetch_risk_assessment_a_real_brand_new_user_gets_an_honest_no_data_result(pool, user_id):
    result = await fetch_risk_assessment(pool, user_id=user_id, now=_NOW)
    assert result.deadline_density == 0
    assert result.matching_historical_weeks == 0
    assert result.pooled_correction_rate is None
    assert result.is_at_risk is False


async def test_fetch_risk_assessment_a_real_live_end_to_end_risk_flag(pool, user_id):
    """A real, live proof of the whole pipeline: real historical weeks
    with a genuinely high correction rate at a real density of 3,
    real open tasks next week also at density 3 -- must flag risk."""
    week_minus_1 = _NOW - timedelta(weeks=1)
    week_minus_2 = _NOW - timedelta(weeks=2)
    # Week -1: density 3, 2 corrected (cancelled) of 3.
    await _seed_task(pool, user_id=user_id, deadline=week_minus_1, status="cancelled")
    await _seed_task(pool, user_id=user_id, deadline=week_minus_1 + timedelta(days=1), status="cancelled")
    await _seed_task(pool, user_id=user_id, deadline=week_minus_1 + timedelta(days=2), status="done")
    # Week -2: density 3, 1 corrected of 3.
    await _seed_task(pool, user_id=user_id, deadline=week_minus_2, status="cancelled")
    await _seed_task(pool, user_id=user_id, deadline=week_minus_2 + timedelta(days=1), status="done")
    await _seed_task(pool, user_id=user_id, deadline=week_minus_2 + timedelta(days=2), status="done")
    # Upcoming week: 3 real, currently-open tasks.
    upcoming = _week_start(_NOW) + timedelta(weeks=1)
    await _seed_task(pool, user_id=user_id, deadline=upcoming + timedelta(days=1), status="open")
    await _seed_task(pool, user_id=user_id, deadline=upcoming + timedelta(days=2), status="open")
    await _seed_task(pool, user_id=user_id, deadline=upcoming + timedelta(days=3), status="open")

    result = await fetch_risk_assessment(pool, user_id=user_id, now=_NOW)

    assert result.deadline_density == 3
    assert result.matching_historical_weeks == 2
    assert result.pooled_correction_rate == 0.5  # 3 corrected / 6 total, pooled
    assert result.is_at_risk is True


async def test_fetch_risk_assessment_never_counts_a_real_done_or_cancelled_task_toward_upcoming_density(pool, user_id):
    """`upcoming_deadline_density` only counts real, currently-OPEN
    tasks -- a real task already done or cancelled represents no real
    upcoming pressure, even if its deadline technically falls next
    week."""
    upcoming = _week_start(_NOW) + timedelta(weeks=1)
    await _seed_task(pool, user_id=user_id, deadline=upcoming + timedelta(days=1), status="done")
    await _seed_task(pool, user_id=user_id, deadline=upcoming + timedelta(days=2), status="cancelled")
    await _seed_task(pool, user_id=user_id, deadline=upcoming + timedelta(days=3), status="open")

    result = await fetch_risk_assessment(pool, user_id=user_id, now=_NOW)

    assert result.deadline_density == 1


async def test_fetch_risk_assessment_never_counts_another_real_users_tasks(pool, user_id):
    other_google_sub = f"test-predictive-risk-other-{uuid.uuid4()}"
    other_user_id = await get_or_create_user(pool, google_sub=other_google_sub, email=None)
    try:
        upcoming = _week_start(_NOW) + timedelta(weeks=1)
        await _seed_task(pool, user_id=other_user_id, deadline=upcoming + timedelta(days=1), status="open")

        result = await fetch_risk_assessment(pool, user_id=user_id, now=_NOW)

        assert result.deadline_density == 0
    finally:
        await pool.execute("DELETE FROM tasks WHERE user_id = $1", uuid.UUID(other_user_id))
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(other_user_id))


async def test_fetch_risk_assessment_a_real_task_far_outside_the_history_window_is_ignored(pool, user_id):
    from quorum_backend.features.predictive_risk import HISTORY_WINDOW_WEEKS

    too_old = _NOW - timedelta(weeks=HISTORY_WINDOW_WEEKS + 5)
    await _seed_task(pool, user_id=user_id, deadline=too_old, status="cancelled")

    result = await fetch_risk_assessment(pool, user_id=user_id, now=_NOW)

    # No real history within the real window, and no real upcoming
    # tasks either -- an honest no-data result, not a fabricated one
    # built from data outside the real, disclosed window.
    assert result.matching_historical_weeks == 0
    assert result.pooled_correction_rate is None
