"""Real tests for features/today.py -- pure-function arithmetic
(hand-verified before being trusted, the same discipline every prior
real numeric module in this backend already holds itself to) plus real
tests against the real, live Supabase database (`DEC-098`), real
INSERTs, real queries, real DELETEs in a `finally` block, per
`CLAUDE.md` Rule 5.

Real per-user scoping from this module's first line (`DEC-119`) --
unlike `test_tasks_feature.py`/`test_career_pipeline_feature.py`, no
retrofit was needed; every test below provisions a real, fresh test
identity via the `user_id` fixture, same established pattern.
"""
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.features.today import (
    compute_budget_state,
    compute_capacity_state,
    fetch_active_negotiations,
    fetch_pending_actions,
    fetch_today_budget,
    fetch_today_capacity,
)


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-today-{uuid.uuid4()}"
    real_user_id = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield real_user_id
    await pool.execute("DELETE FROM users WHERE google_sub = $1", google_sub)


# -- compute_capacity_state(): hand-verified in Python before trusting --

def test_compute_capacity_state_the_real_hand_verified_partial_day_case():
    # 8.0 - 3.0 = 5.0 remaining; 5.0 / 8.0 = 0.625 -- computed by hand
    # before this assertion was written.
    result = compute_capacity_state(total_working_hours_today=8.0, hours_committed_today=3.0)
    assert result.hours_remaining_today == 5.0
    assert result.remaining_fraction == 0.625
    assert result.source == "live_backend"


def test_compute_capacity_state_a_real_overcommitted_day_clamps_to_zero_never_negative():
    result = compute_capacity_state(total_working_hours_today=8.0, hours_committed_today=10.0)
    assert result.hours_remaining_today == 0.0
    assert result.remaining_fraction == 0.0


def test_compute_capacity_state_zero_total_hours_is_a_real_honest_zero_not_a_division_crash():
    result = compute_capacity_state(total_working_hours_today=0.0, hours_committed_today=0.0)
    assert result.hours_remaining_today == 0.0
    assert result.remaining_fraction == 0.0


def test_compute_capacity_state_zero_committed_leaves_the_full_real_day_remaining():
    result = compute_capacity_state(total_working_hours_today=8.0, hours_committed_today=0.0)
    assert result.hours_remaining_today == 8.0
    assert result.remaining_fraction == 1.0


# -- compute_budget_state(): hand-verified in Python before trusting --

def test_compute_budget_state_the_real_hand_verified_partial_month_case():
    # 50000 - 12000 = 38000 remaining; 38000 / 50000 = 0.76 -- computed
    # by hand before this assertion was written.
    result = compute_budget_state(monthly_limit=50000.0, spent_so_far=12000.0)
    assert result.amount_remaining == 38000.0
    assert result.remaining_fraction == 0.76
    assert result.source == "live_backend"


def test_compute_budget_state_a_real_overspent_month_clamps_to_zero_never_negative():
    result = compute_budget_state(monthly_limit=50000.0, spent_so_far=60000.0)
    assert result.amount_remaining == 0.0
    assert result.remaining_fraction == 0.0


def test_compute_budget_state_zero_limit_is_a_real_honest_zero_not_a_division_crash():
    result = compute_budget_state(monthly_limit=0.0, spent_so_far=0.0)
    assert result.amount_remaining == 0.0
    assert result.remaining_fraction == 0.0


# -- fetch_pending_actions(): real, live-DB --

async def _insert_action_event(pool, proposal_id, *, action_type, stakes, payload, resolved_at, user_id):
    await pool.execute(
        """
        INSERT INTO action_events (proposal_id, action_type, stakes, payload, trace_id, resolved_at, user_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        proposal_id,
        action_type,
        stakes,
        json.dumps(payload),
        f"trace-{proposal_id}",
        resolved_at,
        uuid.UUID(user_id),
    )


async def test_fetch_pending_actions_returns_a_real_unresolved_row_with_correct_shape_and_types(pool, user_id):
    proposal_id = uuid.uuid4()
    try:
        await _insert_action_event(
            pool,
            proposal_id,
            action_type="send_email",
            stakes="S3",
            payload={"to": "priya@x.com", "body": "a real, deliberately obscure test payload"},
            resolved_at=None,
            user_id=user_id,
        )

        records = await fetch_pending_actions(pool, user_id=user_id)
        match = next(r for r in records if r.proposal_id == str(proposal_id))

        assert match.action_type == "send_email"
        assert match.stakes == "S3"
        assert isinstance(match.payload, dict)
        assert match.payload == {"to": "priya@x.com", "body": "a real, deliberately obscure test payload"}
        assert match.created_at.endswith("Z")
    finally:
        await pool.execute("DELETE FROM action_events WHERE proposal_id = $1", proposal_id)


async def test_fetch_pending_actions_excludes_a_real_resolved_row(pool, user_id):
    proposal_id = uuid.uuid4()
    try:
        await _insert_action_event(
            pool,
            proposal_id,
            action_type="log_expense",
            stakes="S1",
            payload={"amount": 100},
            resolved_at=datetime.now(timezone.utc),
            user_id=user_id,
        )

        records = await fetch_pending_actions(pool, user_id=user_id)
        assert all(r.proposal_id != str(proposal_id) for r in records)
    finally:
        await pool.execute("DELETE FROM action_events WHERE proposal_id = $1", proposal_id)


async def test_fetch_pending_actions_returns_a_real_empty_list_never_a_crash_when_nothing_matches(pool, user_id):
    records = await fetch_pending_actions(pool, user_id=user_id)
    assert records == []


async def test_fetch_pending_actions_never_returns_another_real_users_rows(pool, user_id):
    other_google_sub = f"test-today-other-{uuid.uuid4()}"
    other_user_id = await get_or_create_user(pool, google_sub=other_google_sub, email=None)
    proposal_id = uuid.uuid4()

    try:
        await _insert_action_event(
            pool,
            proposal_id,
            action_type="send_email",
            stakes="S3",
            payload={"to": "someone-else@x.com"},
            resolved_at=None,
            user_id=other_user_id,
        )

        records = await fetch_pending_actions(pool, user_id=user_id)
        assert all(r.proposal_id != str(proposal_id) for r in records)
    finally:
        await pool.execute("DELETE FROM action_events WHERE proposal_id = $1", proposal_id)
        await pool.execute("DELETE FROM users WHERE google_sub = $1", other_google_sub)


# -- fetch_active_negotiations(): real, live-DB --

async def _insert_negotiation(pool, negotiation_id, *, conflicted_domains, started_at, resolved_at, user_id):
    await pool.execute(
        """
        INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at, resolved_at)
        VALUES ($1, $2, $3, $4, $5)
        """,
        negotiation_id,
        uuid.UUID(user_id),
        conflicted_domains,
        started_at,
        resolved_at,
    )


async def test_fetch_active_negotiations_returns_a_real_unresolved_row_with_correct_shape_and_types(pool, user_id):
    negotiation_id = uuid.uuid4()
    started_at = datetime(2026, 8, 20, 9, 0, tzinfo=timezone.utc)
    try:
        await _insert_negotiation(
            pool,
            negotiation_id,
            conflicted_domains=["calendar", "finance"],
            started_at=started_at,
            resolved_at=None,
            user_id=user_id,
        )

        records = await fetch_active_negotiations(pool, user_id=user_id)
        match = next(r for r in records if r.negotiation_id == str(negotiation_id))

        assert match.conflicted_domains == ["calendar", "finance"]
        assert match.started_at == "2026-08-20T09:00:00Z"
    finally:
        await pool.execute("DELETE FROM negotiations WHERE negotiation_id = $1", negotiation_id)


async def test_fetch_active_negotiations_excludes_a_real_resolved_row(pool, user_id):
    negotiation_id = uuid.uuid4()
    try:
        await _insert_negotiation(
            pool,
            negotiation_id,
            conflicted_domains=["tasks", "career"],
            started_at=datetime.now(timezone.utc),
            resolved_at=datetime.now(timezone.utc),
            user_id=user_id,
        )

        records = await fetch_active_negotiations(pool, user_id=user_id)
        assert all(r.negotiation_id != str(negotiation_id) for r in records)
    finally:
        await pool.execute("DELETE FROM negotiations WHERE negotiation_id = $1", negotiation_id)


async def test_fetch_active_negotiations_returns_a_real_empty_list_never_a_crash_when_nothing_matches(pool, user_id):
    records = await fetch_active_negotiations(pool, user_id=user_id)
    assert records == []


async def test_fetch_active_negotiations_never_returns_another_real_users_rows(pool, user_id):
    other_google_sub = f"test-today-neg-other-{uuid.uuid4()}"
    other_user_id = await get_or_create_user(pool, google_sub=other_google_sub, email=None)
    negotiation_id = uuid.uuid4()

    try:
        await _insert_negotiation(
            pool,
            negotiation_id,
            conflicted_domains=["email"],
            started_at=datetime.now(timezone.utc),
            resolved_at=None,
            user_id=other_user_id,
        )

        records = await fetch_active_negotiations(pool, user_id=user_id)
        assert all(r.negotiation_id != str(negotiation_id) for r in records)
    finally:
        await pool.execute("DELETE FROM negotiations WHERE negotiation_id = $1", negotiation_id)
        await pool.execute("DELETE FROM users WHERE google_sub = $1", other_google_sub)


# -- fetch_today_capacity(): real, live-DB --

async def test_fetch_today_capacity_counts_only_real_open_tasks_due_today(pool, user_id):
    today_task = uuid.uuid4()
    tomorrow_task = uuid.uuid4()
    done_today_task = uuid.uuid4()
    now = datetime.now(timezone.utc)
    try:
        await pool.execute(
            "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1,$2,$3,$4,$5,$6)",
            today_task, uuid.UUID(user_id), "Due today, open", 3.0, now, "open",
        )
        await pool.execute(
            "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1,$2,$3,$4,$5,$6)",
            tomorrow_task, uuid.UUID(user_id), "Due tomorrow", 5.0, now + timedelta(days=1), "open",
        )
        await pool.execute(
            "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1,$2,$3,$4,$5,$6)",
            done_today_task, uuid.UUID(user_id), "Due today, already done", 2.0, now, "done",
        )

        result = await fetch_today_capacity(pool, user_id=user_id)

        # Only the 3.0-hour open task due today counts: 8.0 - 3.0 = 5.0.
        assert result.hours_remaining_today == 5.0
        assert result.source == "live_backend"
    finally:
        await pool.execute("DELETE FROM tasks WHERE task_id = ANY($1::uuid[])", [today_task, tomorrow_task, done_today_task])


async def test_fetch_today_capacity_is_a_real_full_day_when_nothing_is_committed(pool, user_id):
    result = await fetch_today_capacity(pool, user_id=user_id)
    assert result.hours_remaining_today == 8.0
    assert result.remaining_fraction == 1.0


async def test_fetch_today_capacity_never_counts_another_real_users_tasks(pool, user_id):
    other_google_sub = f"test-today-cap-other-{uuid.uuid4()}"
    other_user_id = await get_or_create_user(pool, google_sub=other_google_sub, email=None)
    other_task = uuid.uuid4()

    try:
        await pool.execute(
            "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1,$2,$3,$4,$5,$6)",
            other_task, uuid.UUID(other_user_id), "Another user's real task, due today", 4.0, datetime.now(timezone.utc), "open",
        )

        result = await fetch_today_capacity(pool, user_id=user_id)
        assert result.hours_remaining_today == 8.0  # unaffected by the other user's real commitment
    finally:
        await pool.execute("DELETE FROM tasks WHERE task_id = $1", other_task)
        await pool.execute("DELETE FROM users WHERE google_sub = $1", other_google_sub)


# -- fetch_today_budget(): real, live-DB --

async def test_fetch_today_budget_counts_only_real_expenses_this_calendar_month(pool, user_id):
    now = datetime.now(timezone.utc)
    this_month_expense = uuid.uuid4()
    # A real, deliberately obscure prior month -- always genuinely in
    # the past relative to "now", whatever "now" actually is.
    other_month = now.replace(day=1) - timedelta(days=45)
    other_month_expense = uuid.uuid4()
    try:
        await pool.execute(
            "INSERT INTO expenses (expense_id, user_id, payee, amount, occurred_at, source) VALUES ($1,$2,$3,$4,$5,$6)",
            this_month_expense, uuid.UUID(user_id), "A real vendor", 12000.0, now, "manual",
        )
        await pool.execute(
            "INSERT INTO expenses (expense_id, user_id, payee, amount, occurred_at, source) VALUES ($1,$2,$3,$4,$5,$6)",
            other_month_expense, uuid.UUID(user_id), "A real, out-of-month vendor", 99999.0, other_month, "manual",
        )

        result = await fetch_today_budget(pool, user_id=user_id)

        # Only the 12000 this-month expense counts: 50000 - 12000 = 38000.
        assert result.amount_remaining == 38000.0
        assert result.source == "live_backend"
    finally:
        await pool.execute("DELETE FROM expenses WHERE expense_id = ANY($1::uuid[])", [this_month_expense, other_month_expense])


async def test_fetch_today_budget_is_the_real_full_limit_when_nothing_spent(pool, user_id):
    result = await fetch_today_budget(pool, user_id=user_id)
    assert result.amount_remaining == 50000.0
    assert result.remaining_fraction == 1.0


async def test_fetch_today_budget_never_counts_another_real_users_expenses(pool, user_id):
    other_google_sub = f"test-today-budget-other-{uuid.uuid4()}"
    other_user_id = await get_or_create_user(pool, google_sub=other_google_sub, email=None)
    other_expense = uuid.uuid4()

    try:
        await pool.execute(
            "INSERT INTO expenses (expense_id, user_id, payee, amount, occurred_at, source) VALUES ($1,$2,$3,$4,$5,$6)",
            other_expense, uuid.UUID(other_user_id), "Another user's real expense", 20000.0, datetime.now(timezone.utc), "manual",
        )

        result = await fetch_today_budget(pool, user_id=user_id)
        assert result.amount_remaining == 50000.0  # unaffected by the other user's real spending
    finally:
        await pool.execute("DELETE FROM expenses WHERE expense_id = $1", other_expense)
        await pool.execute("DELETE FROM users WHERE google_sub = $1", other_google_sub)
