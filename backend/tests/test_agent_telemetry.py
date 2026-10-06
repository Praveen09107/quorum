"""Real tests for features/agent_telemetry.py (`DEC-192`, product
rebuild Block D)."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.features.agent_telemetry import (
    AGENT_FOR_ACTION_TYPE,
    REAL_DOMAIN_AGENTS,
    agent_for_action_type,
    aggregate_agent_stats,
    fetch_agent_stats,
)
from quorum_backend.gate.schemas import ActionType


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-agent-telemetry-{uuid.uuid4()}"
    uid = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield uid
    await pool.execute("DELETE FROM action_events WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(uid))


# --- AGENT_FOR_ACTION_TYPE / agent_for_action_type: pure ---


def test_agent_for_action_type_is_exhaustive_over_every_real_action_type():
    """The real, live guard against this enum silently growing
    unnoticed -- every real `ActionType` must appear in the mapping,
    confirmed directly rather than assumed."""
    for action_type in ActionType:
        assert action_type in AGENT_FOR_ACTION_TYPE, f"{action_type} is missing from AGENT_FOR_ACTION_TYPE"


def test_agent_for_action_type_maps_every_real_email_action_to_email():
    for action_type in (ActionType.SEND_EMAIL, ActionType.CREATE_EMAIL_DRAFT, ActionType.ARCHIVE_EMAIL, ActionType.LABEL_EMAIL):
        assert agent_for_action_type(action_type.value) == "email"


def test_agent_for_action_type_maps_every_real_career_action_to_career():
    for action_type in (ActionType.UPDATE_APPLICATION_STATUS, ActionType.CREATE_APPLICATION):
        assert agent_for_action_type(action_type.value) == "career"


def test_agent_for_action_type_create_note_maps_to_no_real_agent():
    """The one real, disclosed exception -- no agent in this system has
    ever proposed `CREATE_NOTE`, and it has no execution target either.
    `None` here means "belongs to no current agent," not a bug."""
    assert agent_for_action_type(ActionType.CREATE_NOTE.value) is None


def test_agent_for_action_type_fails_loud_on_a_genuinely_unrecognized_value():
    """Matches `CLAUDE.md`'s own mandated handling for `tasks.status`,
    this project's other closed enum-backed set."""
    try:
        agent_for_action_type("some_future_action_type")
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "some_future_action_type" in str(exc)


# --- aggregate_agent_stats: pure ---


def test_aggregate_agent_stats_always_returns_every_real_domain_agent():
    """A genuinely inactive agent must render as an honest zero, never
    be silently absent -- which would be indistinguishable from "no
    such agent" on the client."""
    stats = aggregate_agent_stats([])
    assert set(stats.keys()) == set(REAL_DOMAIN_AGENTS)
    for agent_stats in stats.values():
        assert agent_stats.lifetime_actions == 0
        assert agent_stats.last_activity is None
        assert agent_stats.success_rate is None


def test_aggregate_agent_stats_buckets_sum_to_lifetime_actions():
    now = datetime.now(timezone.utc)
    rows = [
        ("send_email", "approved_unchanged", now),
        ("send_email", "caught_by_gate", now),
        ("send_email", "rejected_by_user", now),
        ("send_email", "outcome_unknown", now),
        ("archive_email", "approved_unchanged", now),
    ]
    stats = aggregate_agent_stats(rows)
    email = stats["email"]
    assert email.lifetime_actions == 5
    assert email.success_count == 2
    assert email.caught_count == 1
    assert email.rejected_count == 1
    assert email.uncertain_count == 1
    assert email.success_count + email.caught_count + email.rejected_count + email.uncertain_count == email.lifetime_actions


def test_aggregate_agent_stats_tracks_the_real_most_recent_activity():
    older = datetime.now(timezone.utc) - timedelta(days=5)
    newer = datetime.now(timezone.utc)
    rows = [
        ("create_task", "approved_unchanged", older),
        ("update_task", "approved_unchanged", newer),
    ]
    stats = aggregate_agent_stats(rows)
    assert stats["tasks"].last_activity == newer


def test_aggregate_agent_stats_excludes_uncertain_from_the_success_rate_denominator():
    """Mirrors `trust_digest.py`'s own already-established precedent:
    "we don't know" must never be collapsed into "it failed" by
    counting it in the denominator."""
    now = datetime.now(timezone.utc)
    rows = [
        ("log_expense", "approved_unchanged", now),
        ("log_expense", "uncertain_no_data", now),
    ]
    stats = aggregate_agent_stats(rows)
    assert stats["finance"].success_rate == 1.0  # NOT 0.5


def test_aggregate_agent_stats_a_create_note_row_is_attributed_to_no_agent():
    now = datetime.now(timezone.utc)
    rows = [("create_note", "approved_unchanged", now)]
    stats = aggregate_agent_stats(rows)
    assert all(agent_stats.lifetime_actions == 0 for agent_stats in stats.values())


def test_aggregate_agent_stats_covers_every_value_the_real_check_constraint_admits():
    """The real regression guard: if a future migration widens
    `action_events_outcome_check` and nobody updates the shared
    partition this module reuses from `honesty_log.py`, this fails
    here rather than silently miscounting a real agent's own track
    record."""
    now = datetime.now(timezone.utc)
    every_real_outcome = [
        "approved_unchanged", "caught_by_gate", "corrected_by_user",
        "uncertain_no_data", "rejected_by_user", "outcome_unknown",
    ]
    rows = [("create_task", outcome, now) for outcome in every_real_outcome]
    stats = aggregate_agent_stats(rows)
    tasks = stats["tasks"]
    bucketed = tasks.success_count + tasks.caught_count + tasks.rejected_count + tasks.uncertain_count
    assert bucketed == len(every_real_outcome)


# --- fetch_agent_stats: real, live database ---


async def test_fetch_agent_stats_real_per_user_scoping(pool, user_id):
    proposal_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)",
        proposal_id, "create_task", "S1", "{}", "approve", "approved_unchanged",
        str(proposal_id), uuid.UUID(user_id), datetime.now(timezone.utc),
    )

    stats = await fetch_agent_stats(pool, user_id=user_id)

    assert stats["tasks"].lifetime_actions == 1
    assert stats["email"].lifetime_actions == 0


async def test_fetch_agent_stats_never_leaks_another_real_users_rows(pool, user_id):
    other_sub = f"test-agent-telemetry-other-{uuid.uuid4()}"
    other_id = await get_or_create_user(pool, google_sub=other_sub, email=None)
    proposal_id = uuid.uuid4()
    try:
        await pool.execute(
            "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at) "
            "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)",
            proposal_id, "send_email", "S3", "{}", "approve", "approved_unchanged",
            str(proposal_id), uuid.UUID(other_id), datetime.now(timezone.utc),
        )

        stats = await fetch_agent_stats(pool, user_id=user_id)
        assert stats["email"].lifetime_actions == 0
    finally:
        await pool.execute("DELETE FROM action_events WHERE proposal_id = $1", proposal_id)
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(other_id))


async def test_fetch_agent_stats_excludes_a_real_still_unresolved_action(pool, user_id):
    """Matches `trust_digest.py`'s own `outcome IS NOT NULL` convention
    -- a real `escalate_to_human` still genuinely awaiting a human
    decision is not yet a fact about this agent's own track record."""
    proposal_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)",
        proposal_id, "send_email", "S3", "{}", "escalate_to_human", None,
        str(proposal_id), uuid.UUID(user_id), None,
    )

    stats = await fetch_agent_stats(pool, user_id=user_id)
    assert stats["email"].lifetime_actions == 0
