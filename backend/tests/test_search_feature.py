"""Real tests for features/search.py.

Pure content-formatting tests need no real infrastructure. The tests
below `# --- Real, live tests` run against the real, live Supabase
database AND the real, live Gemini embedding API (`DEC-098`) -- real
INSERTs, real embedding calls, real queries, real DELETEs (including
each test's own `note_embeddings` rows) in a `finally` block, per
`CLAUDE.md` Rule 5. Skipped, not failed, without a real
`GEMINI_API_KEY` configured (e.g. CI) -- the same honest-skip
discipline `test_embeddings.py` already established.
"""
import uuid

import pytest
import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.core.config import get_settings
from quorum_backend.features.search import (
    _content_for_application,
    _content_for_decision,
    _content_for_expense,
    _content_for_task,
    backfill_missing_embeddings,
    search,
)

_HAS_REAL_KEY = get_settings().gemini_api_key is not None
pytestmark = pytest.mark.skipif(not _HAS_REAL_KEY, reason="no real GEMINI_API_KEY configured in this environment")


# --- Pure content formatting (no real infrastructure needed) ---


def test_content_for_task_is_the_real_title_verbatim():
    assert _content_for_task(title="Finish Q3 budget review") == "Finish Q3 budget review"


def test_content_for_expense_includes_the_real_payee_and_amount():
    assert _content_for_expense(payee="Spotify", amount=199.0) == "Spotify — ₹199.00"


def test_content_for_application_includes_role_when_present():
    assert _content_for_application(company="Notion", role="Software Engineer") == "Notion — Software Engineer"


def test_content_for_application_falls_back_to_company_only_when_role_is_null():
    assert _content_for_application(company="Notion", role=None) == "Notion"


def test_content_for_decision_prefers_outcome_over_gate_decision():
    assert _content_for_decision(action_type="send_email", outcome="approved_unchanged", gate_decision="approve") == "send_email: approved_unchanged"


def test_content_for_decision_falls_back_to_gate_decision_when_outcome_is_null():
    assert _content_for_decision(action_type="send_email", outcome=None, gate_decision="escalate_to_human") == "send_email: escalate_to_human"


def test_content_for_decision_falls_back_to_pending_when_both_are_null():
    assert _content_for_decision(action_type="send_email", outcome=None, gate_decision=None) == "send_email: pending"


# --- Real, live tests (database + Gemini) ---


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-search-{uuid.uuid4()}"
    real_user_id = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield real_user_id
    await pool.execute("DELETE FROM note_embeddings WHERE user_id = $1", uuid.UUID(real_user_id))
    await pool.execute("DELETE FROM users WHERE google_sub = $1", google_sub)


@pytest_asyncio.fixture
async def api_key():
    return get_settings().gemini_api_key


async def test_backfill_embeds_a_real_task_and_is_idempotent_on_a_second_run(pool, user_id, api_key):
    task_id = uuid.uuid4()
    try:
        await pool.execute(
            "INSERT INTO tasks (task_id, user_id, title, estimated_hours) VALUES ($1, $2, $3, $4)",
            task_id, uuid.UUID(user_id), "A real, distinctive test task title", 1.0,
        )

        await backfill_missing_embeddings(pool, user_id=user_id, api_key=api_key)
        rows = await pool.fetch(
            "SELECT source_type, source_id, content FROM note_embeddings WHERE user_id = $1", uuid.UUID(user_id)
        )
        assert len(rows) == 1
        assert rows[0]["source_type"] == "task"
        assert rows[0]["source_id"] == task_id
        assert rows[0]["content"] == "A real, distinctive test task title"

        # Real idempotency check: a second run must not re-embed or
        # duplicate -- the real UNIQUE index plus the NOT EXISTS query
        # both guarantee this, not just application-level care.
        await backfill_missing_embeddings(pool, user_id=user_id, api_key=api_key)
        rows_again = await pool.fetch("SELECT * FROM note_embeddings WHERE user_id = $1", uuid.UUID(user_id))
        assert len(rows_again) == 1
    finally:
        await pool.execute("DELETE FROM tasks WHERE task_id = $1", task_id)


async def test_search_ranks_a_real_semantically_related_task_first(pool, user_id, api_key):
    budget_task_id = uuid.uuid4()
    groceries_task_id = uuid.uuid4()
    passport_task_id = uuid.uuid4()
    try:
        await pool.executemany(
            "INSERT INTO tasks (task_id, user_id, title, estimated_hours) VALUES ($1, $2, $3, $4)",
            [
                (budget_task_id, uuid.UUID(user_id), "Finish Q3 budget review before the deadline", 2.0),
                (groceries_task_id, uuid.UUID(user_id), "Buy groceries for the week", 0.5),
                (passport_task_id, uuid.UUID(user_id), "Renew passport before it expires", 1.0),
            ],
        )

        results = await search(pool, user_id=user_id, query="quarterly financial report deadline", api_key=api_key)

        assert len(results) > 0
        assert results[0].item_id == str(budget_task_id)
        assert results[0].item_type == "task"
    finally:
        await pool.execute(
            "DELETE FROM tasks WHERE task_id = ANY($1::uuid[])",
            [budget_task_id, groceries_task_id, passport_task_id],
        )


async def test_search_never_leaks_another_real_users_rows(pool, user_id, api_key):
    other_google_sub = f"test-search-other-{uuid.uuid4()}"
    other_user_id = await get_or_create_user(pool, google_sub=other_google_sub, email=None)
    my_task_id = uuid.uuid4()
    other_task_id = uuid.uuid4()
    try:
        await pool.execute(
            "INSERT INTO tasks (task_id, user_id, title, estimated_hours) VALUES ($1, $2, $3, $4)",
            my_task_id, uuid.UUID(user_id), "My own real, private task", 1.0,
        )
        await pool.execute(
            "INSERT INTO tasks (task_id, user_id, title, estimated_hours) VALUES ($1, $2, $3, $4)",
            other_task_id, uuid.UUID(other_user_id), "A different real user's private task", 1.0,
        )

        results = await search(pool, user_id=user_id, query="private task", api_key=api_key)

        returned_ids = {item.item_id for item in results}
        assert str(my_task_id) in returned_ids
        assert str(other_task_id) not in returned_ids
    finally:
        await pool.execute("DELETE FROM tasks WHERE task_id = ANY($1::uuid[])", [my_task_id, other_task_id])
        await pool.execute("DELETE FROM note_embeddings WHERE user_id = $1", uuid.UUID(other_user_id))
        await pool.execute("DELETE FROM users WHERE google_sub = $1", other_google_sub)


async def test_search_covers_all_four_real_domains_and_caps_at_ten(pool, user_id, api_key):
    task_id = uuid.uuid4()
    expense_id = uuid.uuid4()
    application_id = uuid.uuid4()
    proposal_id = uuid.uuid4()
    try:
        await pool.execute(
            "INSERT INTO tasks (task_id, user_id, title, estimated_hours) VALUES ($1, $2, $3, $4)",
            task_id, uuid.UUID(user_id), "A real cross-domain search test task", 1.0,
        )
        await pool.execute(
            "INSERT INTO expenses (expense_id, user_id, payee, amount, occurred_at, source) VALUES ($1, $2, $3, $4, now(), 'manual')",
            expense_id, uuid.UUID(user_id), "A real cross-domain test payee", 42.0,
        )
        await pool.execute(
            "INSERT INTO applications (application_id, user_id, company, role) VALUES ($1, $2, $3, $4)",
            application_id, uuid.UUID(user_id), "A real cross-domain test company", "Test Role",
        )
        await pool.execute(
            """
            INSERT INTO action_events (proposal_id, user_id, action_type, stakes, payload, trace_id)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6)
            """,
            proposal_id, uuid.UUID(user_id), "create_note", "S0", "{}", f"test-search-{proposal_id}",
        )

        results = await search(pool, user_id=user_id, query="cross-domain test", limit=10, api_key=api_key)

        item_types = {item.item_type for item in results}
        assert item_types == {"task", "expense", "application", "decision"}
        assert len(results) <= 10
    finally:
        await pool.execute("DELETE FROM tasks WHERE task_id = $1", task_id)
        await pool.execute("DELETE FROM expenses WHERE expense_id = $1", expense_id)
        await pool.execute("DELETE FROM applications WHERE application_id = $1", application_id)
        await pool.execute("DELETE FROM action_events WHERE proposal_id = $1", proposal_id)
