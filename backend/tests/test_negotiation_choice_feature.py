"""Real tests for features/negotiation_choice.py -- real INSERTs/UPDATEs,
real queries, real DELETEs in a `finally` block, per `CLAUDE.md` Rule 5.
"""
import json
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.features.negotiation_choice import (
    InvalidChosenOption,
    NegotiationAlreadyResolved,
    NegotiationNotFound,
    NegotiationNotReadyToChoose,
    choose_negotiation_option,
)


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-negotiation-choice-{uuid.uuid4()}"
    real_user_id = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield real_user_id
    await pool.execute("DELETE FROM users WHERE google_sub = $1", google_sub)


_REAL_OPTIONS = [
    {"option_id": "option_a", "description": "halt spending", "source_domains": ["finance"]},
    {"option_id": "option_b", "description": "drop a task", "source_domains": ["tasks"]},
    {"option_id": "do_nothing", "description": "do nothing", "source_domains": []},
]


async def _insert_negotiation(pool, *, user_id: str, with_options: bool = True, resolved: bool = False) -> str:
    negotiation_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at, options, resolved_at, chosen_option_id) "
        "VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)",
        negotiation_id,
        uuid.UUID(user_id),
        ["finance", "tasks"],
        datetime.now(timezone.utc),
        json.dumps(_REAL_OPTIONS) if with_options else None,
        datetime.now(timezone.utc) if resolved else None,
        "option_a" if resolved else None,
    )
    return str(negotiation_id)


async def test_choose_negotiation_option_marks_it_resolved_and_enqueues_a_real_retry_queue_row(pool, user_id):
    negotiation_id = await _insert_negotiation(pool, user_id=user_id)
    try:
        result = await choose_negotiation_option(pool, user_id=user_id, negotiation_id=negotiation_id, chosen_option="option_a")

        assert result.option_id == "option_a"
        assert result.description == "halt spending"
        assert result.source_domains == ["finance"]

        row = await pool.fetchrow(
            "SELECT resolved_at, chosen_option_id FROM negotiations WHERE negotiation_id = $1", uuid.UUID(negotiation_id)
        )
        assert row["resolved_at"] is not None
        assert row["chosen_option_id"] == "option_a"

        job = await pool.fetchrow(
            "SELECT job_type, payload FROM retry_queue WHERE payload->>'negotiation_id' = $1", negotiation_id
        )
        assert job is not None
        assert job["job_type"] == "negotiation_downstream_action"
        payload = json.loads(job["payload"])
        assert payload["chosen_option_id"] == "option_a"
        assert payload["user_id"] == user_id
        assert payload["source_domains"] == ["finance"]
    finally:
        await pool.execute("DELETE FROM retry_queue WHERE payload->>'negotiation_id' = $1", negotiation_id)
        await pool.execute("DELETE FROM negotiations WHERE negotiation_id = $1", uuid.UUID(negotiation_id))


async def test_choose_negotiation_option_do_nothing_is_a_real_valid_choice(pool, user_id):
    negotiation_id = await _insert_negotiation(pool, user_id=user_id)
    try:
        result = await choose_negotiation_option(pool, user_id=user_id, negotiation_id=negotiation_id, chosen_option="do_nothing")
        assert result.option_id == "do_nothing"
    finally:
        await pool.execute("DELETE FROM retry_queue WHERE payload->>'negotiation_id' = $1", negotiation_id)
        await pool.execute("DELETE FROM negotiations WHERE negotiation_id = $1", uuid.UUID(negotiation_id))


async def test_choose_negotiation_option_raises_not_found_for_a_real_nonexistent_id(pool, user_id):
    with pytest.raises(NegotiationNotFound):
        await choose_negotiation_option(pool, user_id=user_id, negotiation_id=str(uuid.uuid4()), chosen_option="option_a")


async def test_choose_negotiation_option_raises_not_found_for_another_real_users_negotiation(pool, user_id):
    other_google_sub = f"test-negotiation-choice-other-{uuid.uuid4()}"
    other_user_id = await get_or_create_user(pool, google_sub=other_google_sub, email=None)
    negotiation_id = await _insert_negotiation(pool, user_id=other_user_id)
    try:
        with pytest.raises(NegotiationNotFound):
            await choose_negotiation_option(pool, user_id=user_id, negotiation_id=negotiation_id, chosen_option="option_a")
    finally:
        await pool.execute("DELETE FROM negotiations WHERE negotiation_id = $1", uuid.UUID(negotiation_id))
        await pool.execute("DELETE FROM users WHERE google_sub = $1", other_google_sub)


async def test_choose_negotiation_option_raises_not_ready_when_options_are_still_null(pool, user_id):
    negotiation_id = await _insert_negotiation(pool, user_id=user_id, with_options=False)
    try:
        with pytest.raises(NegotiationNotReadyToChoose):
            await choose_negotiation_option(pool, user_id=user_id, negotiation_id=negotiation_id, chosen_option="option_a")
    finally:
        await pool.execute("DELETE FROM negotiations WHERE negotiation_id = $1", uuid.UUID(negotiation_id))


async def test_choose_negotiation_option_raises_already_resolved_and_never_double_enqueues(pool, user_id):
    negotiation_id = await _insert_negotiation(pool, user_id=user_id, resolved=True)
    try:
        with pytest.raises(NegotiationAlreadyResolved):
            await choose_negotiation_option(pool, user_id=user_id, negotiation_id=negotiation_id, chosen_option="option_b")
        # Real, live proof the guard fires before any real write --
        # no retry_queue row was created by the rejected attempt.
        job_count = await pool.fetchval(
            "SELECT COUNT(*) FROM retry_queue WHERE payload->>'negotiation_id' = $1", negotiation_id
        )
        assert job_count == 0
    finally:
        await pool.execute("DELETE FROM negotiations WHERE negotiation_id = $1", uuid.UUID(negotiation_id))


async def test_choose_negotiation_option_raises_invalid_for_an_ungrounded_option(pool, user_id):
    negotiation_id = await _insert_negotiation(pool, user_id=user_id)
    try:
        with pytest.raises(InvalidChosenOption):
            await choose_negotiation_option(pool, user_id=user_id, negotiation_id=negotiation_id, chosen_option="option_that_was_never_synthesized")
        row = await pool.fetchrow("SELECT resolved_at FROM negotiations WHERE negotiation_id = $1", uuid.UUID(negotiation_id))
        assert row["resolved_at"] is None  # a real, rejected choice never resolves the negotiation
    finally:
        await pool.execute("DELETE FROM negotiations WHERE negotiation_id = $1", uuid.UUID(negotiation_id))
