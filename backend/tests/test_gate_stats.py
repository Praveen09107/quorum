"""Real tests for features/gate_stats.py (`DEC-193`, product rebuild
Block E)."""
import json
import uuid
from datetime import datetime, timezone

import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.features.gate_stats import fetch_gate_stats


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-gate-stats-{uuid.uuid4()}"
    uid = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield uid
    await pool.execute("DELETE FROM action_events WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(uid))


async def _insert_event(pool, *, user_id, stakes, outcome, gate_timeline=None, revision_count=None):
    proposal_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, "
        "user_id, resolved_at, gate_timeline, revision_count) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9, $10::jsonb, $11)",
        proposal_id, "create_task", stakes, "{}", "approve", outcome,
        str(proposal_id), uuid.UUID(user_id), datetime.now(timezone.utc),
        json.dumps(gate_timeline) if gate_timeline is not None else None, revision_count,
    )
    return proposal_id


async def test_fetch_gate_stats_a_real_user_with_no_activity_gets_honest_zeros(pool, user_id):
    stats = await fetch_gate_stats(pool, user_id=user_id)
    assert stats.total_resolved == 0
    assert stats.stakes_counts == {}
    assert stats.catch_rate is None


async def test_fetch_gate_stats_real_stakes_distribution(pool, user_id):
    await _insert_event(pool, user_id=user_id, stakes="S1", outcome="approved_unchanged")
    await _insert_event(pool, user_id=user_id, stakes="S1", outcome="approved_unchanged")
    await _insert_event(pool, user_id=user_id, stakes="S3", outcome="rejected_by_user")

    stats = await fetch_gate_stats(pool, user_id=user_id)
    assert stats.total_resolved == 3
    assert stats.stakes_counts == {"S1": 2, "S3": 1}


async def test_fetch_gate_stats_buckets_sum_to_total_resolved(pool, user_id):
    await _insert_event(pool, user_id=user_id, stakes="S1", outcome="approved_unchanged")
    await _insert_event(pool, user_id=user_id, stakes="S2", outcome="caught_by_gate")
    await _insert_event(pool, user_id=user_id, stakes="S3", outcome="rejected_by_user")
    await _insert_event(pool, user_id=user_id, stakes="S3", outcome="outcome_unknown")

    stats = await fetch_gate_stats(pool, user_id=user_id)
    assert stats.total_resolved == 4
    bucketed = stats.success_count + stats.caught_count + stats.rejected_count + stats.uncertain_count
    assert bucketed == stats.total_resolved


async def test_fetch_gate_stats_catch_rate_excludes_uncertain_from_the_denominator(pool, user_id):
    await _insert_event(pool, user_id=user_id, stakes="S1", outcome="approved_unchanged")
    await _insert_event(pool, user_id=user_id, stakes="S3", outcome="outcome_unknown")

    stats = await fetch_gate_stats(pool, user_id=user_id)
    assert stats.catch_rate == 0.0  # NOT skewed by the uncertain row


async def test_fetch_gate_stats_reads_the_real_stage_b_ran_fact_from_the_recorded_timeline(pool, user_id):
    """The real point of using the recorded timeline rather than a
    stakes-tier guess: a real S3 proposal whose Stage A hard-failed
    never reached Stage B at all, and the real timeline says so."""
    await _insert_event(
        pool, user_id=user_id, stakes="S3", outcome="caught_by_gate",
        gate_timeline=[{"event": "stage_a.check"}, {"event": "done", "stage_b_ran": False}],
    )
    await _insert_event(
        pool, user_id=user_id, stakes="S3", outcome="approved_unchanged",
        gate_timeline=[{"event": "stage_b.judge"}, {"event": "done", "stage_b_ran": True}],
    )

    stats = await fetch_gate_stats(pool, user_id=user_id)
    assert stats.rows_with_recorded_timeline == 2
    assert stats.stage_b_ran_count == 1  # only the second real row genuinely reached Stage B


async def test_fetch_gate_stats_a_row_with_no_recorded_timeline_is_not_counted_either_way(pool, user_id):
    """Migration `0021` left every pre-existing row with a genuinely
    NULL timeline -- must not be silently counted as `stage_b_ran=False`,
    which would assert a fact this backend never actually recorded."""
    await _insert_event(pool, user_id=user_id, stakes="S3", outcome="approved_unchanged", gate_timeline=None)

    stats = await fetch_gate_stats(pool, user_id=user_id)
    assert stats.rows_with_recorded_timeline == 0
    assert stats.stage_b_ran_count == 0


async def test_fetch_gate_stats_counts_real_revisions(pool, user_id):
    await _insert_event(pool, user_id=user_id, stakes="S3", outcome="approved_unchanged", revision_count=1)
    await _insert_event(pool, user_id=user_id, stakes="S3", outcome="approved_unchanged", revision_count=0)
    await _insert_event(pool, user_id=user_id, stakes="S1", outcome="approved_unchanged", revision_count=None)

    stats = await fetch_gate_stats(pool, user_id=user_id)
    assert stats.revised_count == 1


async def test_fetch_gate_stats_never_leaks_another_real_users_rows(pool, user_id):
    other_sub = f"test-gate-stats-other-{uuid.uuid4()}"
    other_id = await get_or_create_user(pool, google_sub=other_sub, email=None)
    try:
        await _insert_event(pool, user_id=other_id, stakes="S3", outcome="approved_unchanged")

        stats = await fetch_gate_stats(pool, user_id=user_id)
        assert stats.total_resolved == 0
    finally:
        await pool.execute("DELETE FROM action_events WHERE user_id = $1", uuid.UUID(other_id))
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(other_id))


async def test_fetch_gate_stats_excludes_a_real_still_unresolved_action(pool, user_id):
    proposal_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)",
        proposal_id, "send_email", "S3", "{}", "escalate_to_human", None,
        str(proposal_id), uuid.UUID(user_id), None,
    )

    stats = await fetch_gate_stats(pool, user_id=user_id)
    assert stats.total_resolved == 0
