"""Real tests for features/gate_reveal.py (Phase 6, DEC-146)."""
import uuid
from datetime import datetime, timezone

import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.features.gate_reveal import fetch_gate_reveal


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-gate-reveal-{uuid.uuid4()}"
    uid = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield uid
    await pool.execute("DELETE FROM action_events WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(uid))


async def _insert_action_event(pool, *, proposal_id, user_id, findings=None, objections=None):
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at, findings, objections) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9, $10::jsonb, $11::jsonb)",
        proposal_id, "create_task", "S1", '{"title": "A real task"}', "approve", "approved_unchanged",
        f"trace-{proposal_id}", uuid.UUID(user_id), datetime.now(timezone.utc), findings, objections,
    )


async def test_fetch_gate_reveal_returns_real_findings_and_objections(pool, user_id):
    proposal_id = uuid.uuid4()
    await _insert_action_event(
        pool, proposal_id=proposal_id, user_id=user_id,
        findings='[{"validator": "ProvenanceCheck", "claim": "A real claim", "evidence_state": "verified_true", "source_ref": null, "confidence": 1.0}]',
        objections='[{"category": "tone", "severity": "low", "description": "Fine.", "evidence_ref": null, "suggested_fix": null, "signed_off": true}]',
    )

    bundle = await fetch_gate_reveal(pool, user_id=user_id, proposal_id=str(proposal_id))

    assert bundle is not None
    assert bundle.findings == [
        {"validator": "ProvenanceCheck", "claim": "A real claim", "evidence_state": "verified_true", "source_ref": None, "confidence": 1.0}
    ]
    assert bundle.objections[0]["signed_off"] is True


async def test_fetch_gate_reveal_a_real_null_findings_and_objections_are_honest_empty_lists(pool, user_id):
    """A real row written before migration `0013` (or any real row
    whose stakes never reached Stage B and whose findings/objections
    somehow weren't written) has `NULL` in these columns -- treated as
    a real, honest empty list, never an error."""
    proposal_id = uuid.uuid4()
    await _insert_action_event(pool, proposal_id=proposal_id, user_id=user_id, findings=None, objections=None)

    bundle = await fetch_gate_reveal(pool, user_id=user_id, proposal_id=str(proposal_id))

    assert bundle is not None
    assert bundle.findings == []
    assert bundle.objections == []


async def test_fetch_gate_reveal_returns_none_for_a_real_nonexistent_proposal(pool, user_id):
    bundle = await fetch_gate_reveal(pool, user_id=user_id, proposal_id=str(uuid.uuid4()))
    assert bundle is None


async def test_fetch_gate_reveal_never_leaks_another_real_users_row(pool, user_id):
    other_google_sub = f"test-gate-reveal-bystander-{uuid.uuid4()}"
    other_user_id = await get_or_create_user(pool, google_sub=other_google_sub, email=None)
    proposal_id = uuid.uuid4()
    try:
        await _insert_action_event(pool, proposal_id=proposal_id, user_id=other_user_id)

        bundle = await fetch_gate_reveal(pool, user_id=user_id, proposal_id=str(proposal_id))

        assert bundle is None  # genuinely exists, but not for THIS real user
    finally:
        await pool.execute("DELETE FROM action_events WHERE proposal_id = $1", proposal_id)
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(other_user_id))
