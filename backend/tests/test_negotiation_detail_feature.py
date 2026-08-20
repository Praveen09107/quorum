"""Real tests for features/negotiation_detail.py -- real INSERTs/UPDATEs,
real queries, real DELETEs in a `finally` block, per `CLAUDE.md` Rule 5.
"""
import uuid
from datetime import datetime, timezone

import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.features.negotiation_detail import fetch_negotiation_detail, persist_negotiation_detail
from quorum_backend.gate.schemas import ImpactDelta, NegotiationOption, Position


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-negotiation-detail-{uuid.uuid4()}"
    real_user_id = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield real_user_id
    await pool.execute("DELETE FROM users WHERE google_sub = $1", google_sub)


async def _insert_negotiation(pool, *, user_id: str) -> str:
    negotiation_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at) VALUES ($1, $2, $3, $4)",
        negotiation_id,
        uuid.UUID(user_id),
        ["finance", "tasks"],
        datetime.now(timezone.utc),
    )
    return str(negotiation_id)


async def test_fetch_negotiation_detail_returns_none_for_a_real_nonexistent_id(pool, user_id):
    result = await fetch_negotiation_detail(pool, user_id=user_id, negotiation_id=str(uuid.uuid4()))
    assert result is None


async def test_fetch_negotiation_detail_returns_real_empty_lists_for_an_in_progress_negotiation(pool, user_id):
    """A real, honest distinction: a row that exists but has no detail
    computed yet is NOT the same as a nonexistent one -- see the
    module's own docstring."""
    negotiation_id = await _insert_negotiation(pool, user_id=user_id)
    try:
        result = await fetch_negotiation_detail(pool, user_id=user_id, negotiation_id=negotiation_id)
        assert result is not None
        assert result.positions == []
        assert result.options == []
    finally:
        await pool.execute("DELETE FROM negotiations WHERE negotiation_id = $1", uuid.UUID(negotiation_id))


async def test_persist_then_fetch_round_trips_real_positions_and_merges_real_impact_onto_options(pool, user_id):
    negotiation_id = await _insert_negotiation(pool, user_id=user_id)
    try:
        positions = [
            Position(domain="finance", concern="budget at risk", severity_claim="high", proposed_resolution="halt spending"),
        ]
        options = [
            NegotiationOption(option_id="option_a", description="halt spending", source_domains=["finance"]),
            NegotiationOption(option_id="do_nothing", description="do nothing", source_domains=[]),
        ]
        impact = {
            "option_a": [ImpactDelta(metric="budget_remaining_fraction", before=0.08, after=0.18, direction="improves")],
            "do_nothing": [ImpactDelta(metric="budget_remaining_fraction", before=0.08, after=0.08, direction="unchanged")],
        }

        await persist_negotiation_detail(pool, negotiation_id=negotiation_id, positions=positions, options=options, impact=impact)
        result = await fetch_negotiation_detail(pool, user_id=user_id, negotiation_id=negotiation_id)

        assert result.positions == [{"domain": "finance", "concern": "budget at risk", "severity_claim": "high", "resource_claims": [], "proposed_resolution": "halt spending", "evidence": []}]
        assert len(result.options) == 2
        option_a = next(o for o in result.options if o["option_id"] == "option_a")
        assert option_a["impact"] == [{"metric": "budget_remaining_fraction", "before": 0.08, "after": 0.18, "direction": "improves"}]
        do_nothing = next(o for o in result.options if o["option_id"] == "do_nothing")
        assert do_nothing["impact"][0]["direction"] == "unchanged"
    finally:
        await pool.execute("DELETE FROM negotiations WHERE negotiation_id = $1", uuid.UUID(negotiation_id))


async def test_fetch_negotiation_detail_never_leaks_another_real_users_row(pool, user_id):
    other_google_sub = f"test-negotiation-detail-other-{uuid.uuid4()}"
    other_user_id = await get_or_create_user(pool, google_sub=other_google_sub, email=None)
    negotiation_id = await _insert_negotiation(pool, user_id=other_user_id)
    try:
        result = await fetch_negotiation_detail(pool, user_id=user_id, negotiation_id=negotiation_id)
        assert result is None  # exists, but not owned by this caller -- must never be returned
    finally:
        await pool.execute("DELETE FROM negotiations WHERE negotiation_id = $1", uuid.UUID(negotiation_id))
        await pool.execute("DELETE FROM users WHERE google_sub = $1", other_google_sub)
