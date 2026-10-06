"""Real, live-database tests for features/email_overview.py
(`DEC-199`, product rebuild) -- backs `GET /email/overview`."""
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.features.email_overview import fetch_known_recipients, fetch_recent_drafts, fetch_sent_history
from quorum_backend.features.waiting_on import mark_thread_replied, record_sent_message


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-email-overview-{uuid.uuid4()}"
    uid = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield uid
    await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(uid))


async def _insert_draft_action_event(
    pool, *, user_id: str, recipient: str, subject: str | None, draft_id: str | None,
    outcome: str = "approved_unchanged", resolved_at: datetime | None = None,
):
    proposal_id = uuid.uuid4()
    payload = {"to": recipient, "body": "a real draft body"}
    if subject is not None:
        payload["subject"] = subject
    artifact = {"draft_id": draft_id} if draft_id is not None else None
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at, artifact) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9, $10::jsonb)",
        proposal_id, "create_email_draft", "S1", json.dumps(payload), "approve", outcome,
        str(proposal_id), uuid.UUID(user_id), resolved_at or datetime.now(timezone.utc),
        json.dumps(artifact) if artifact is not None else None,
    )
    return str(proposal_id)


# --- fetch_recent_drafts ---


async def test_fetch_recent_drafts_returns_a_real_approved_draft_with_its_real_artifact(pool, user_id):
    await _insert_draft_action_event(pool, user_id=user_id, recipient="sarah@example.com", subject="Re: proposal", draft_id="draft-abc123")

    drafts = await fetch_recent_drafts(pool, user_id=user_id)

    assert len(drafts) == 1
    assert drafts[0].recipient == "sarah@example.com"
    assert drafts[0].subject == "Re: proposal"
    assert drafts[0].draft_id == "draft-abc123"


async def test_fetch_recent_drafts_excludes_a_real_caught_or_rejected_draft_never_showing_an_unreal_draft(pool, user_id):
    """A real `caught_by_gate`/`rejected_by_user` draft was never
    actually created in Gmail -- showing it here would be exactly the
    kind of fabricated artifact this project's own honesty discipline
    refuses."""
    await _insert_draft_action_event(pool, user_id=user_id, recipient="a@x.com", subject=None, draft_id=None, outcome="caught_by_gate")

    drafts = await fetch_recent_drafts(pool, user_id=user_id)

    assert drafts == []


async def test_fetch_recent_drafts_is_honestly_empty_for_a_user_with_no_drafts(pool, user_id):
    assert await fetch_recent_drafts(pool, user_id=user_id) == []


async def test_fetch_recent_drafts_orders_most_recent_first(pool, user_id):
    now = datetime.now(timezone.utc)
    await _insert_draft_action_event(pool, user_id=user_id, recipient="older@x.com", subject=None, draft_id="d1", resolved_at=now - timedelta(days=1))
    await _insert_draft_action_event(pool, user_id=user_id, recipient="newer@x.com", subject=None, draft_id="d2", resolved_at=now)

    drafts = await fetch_recent_drafts(pool, user_id=user_id)

    assert [d.recipient for d in drafts] == ["newer@x.com", "older@x.com"]


# --- fetch_sent_history ---


async def test_fetch_sent_history_includes_both_replied_and_unreplied_real_messages(pool, user_id):
    await record_sent_message(
        pool, user_id=user_id, message_id="m1", thread_id="t1", recipient="a@x.com", subject="still waiting",
        sent_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    await record_sent_message(
        pool, user_id=user_id, message_id="m2", thread_id="t2", recipient="b@x.com", subject="already answered",
        sent_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    await mark_thread_replied(pool, user_id=user_id, thread_id="t2", replied_at=datetime.now(timezone.utc))

    history = await fetch_sent_history(pool, user_id=user_id)

    by_subject = {m.subject: m for m in history}
    assert by_subject["still waiting"].replied_at is None
    assert by_subject["already answered"].replied_at is not None


async def test_fetch_sent_history_is_honestly_empty_for_a_user_who_never_sent_anything(pool, user_id):
    assert await fetch_sent_history(pool, user_id=user_id) == []


# --- fetch_known_recipients ---


async def test_fetch_known_recipients_groups_by_real_recipient_with_a_real_message_count(pool, user_id):
    await record_sent_message(
        pool, user_id=user_id, message_id="m1", thread_id="t1", recipient="sarah@example.com", subject="first",
        sent_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    await record_sent_message(
        pool, user_id=user_id, message_id="m2", thread_id="t2", recipient="sarah@example.com", subject="second",
        sent_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    await record_sent_message(
        pool, user_id=user_id, message_id="m3", thread_id="t3", recipient="bob@example.com", subject="third",
        sent_at=datetime.now(timezone.utc),
    )

    recipients = await fetch_known_recipients(pool, user_id=user_id)

    by_recipient = {r.recipient: r for r in recipients}
    assert by_recipient["sarah@example.com"].message_count == 2
    assert by_recipient["bob@example.com"].message_count == 1
    # Most-recently-contacted first -- bob's real last message postdates sarah's.
    assert recipients[0].recipient == "bob@example.com"


async def test_fetch_known_recipients_is_honestly_empty_for_a_user_who_never_sent_anything(pool, user_id):
    assert await fetch_known_recipients(pool, user_id=user_id) == []
