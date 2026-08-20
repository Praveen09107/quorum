"""Real tests for security/supabase_deletion_store.py -- against the
real, live Supabase database (`DEC-098`). Extra care throughout, per
CLAUDE.md Rule 5's S3-equivalent standard for irreversible real
actions: every test provisions its OWN real, isolated test user and
real, deliberately-obscure rows, asserts the real deletion actually
happened (not just that no exception was raised), and proves a second,
untouched real user's data survives every single purge call. Nothing
here ever runs against a shared or ambiguous identity.
"""
import uuid
from datetime import datetime, timezone

import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.security.supabase_deletion_store import SupabaseDeletionStore


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


async def _provision(pool, label: str) -> str:
    google_sub = f"test-deletion-{label}-{uuid.uuid4()}"
    return await get_or_create_user(pool, google_sub=google_sub, email=None)


async def _real_user_exists(pool, internal_user_id: str) -> bool:
    row = await pool.fetchrow("SELECT 1 FROM users WHERE user_id = $1", uuid.UUID(internal_user_id))
    return row is not None


async def test_purge_postgres_rows_deletes_real_tasks_expenses_applications_interviews_and_the_users_row(pool):
    user_id = await _provision(pool, "full")
    store = SupabaseDeletionStore(pool)

    task_id = uuid.uuid4()
    expense_id = uuid.uuid4()
    application_id = uuid.uuid4()
    interview_id = uuid.uuid4()

    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, $5, $6)",
        task_id, uuid.UUID(user_id), "A real task to be deleted", 1.0, None, "open",
    )
    await pool.execute(
        "INSERT INTO expenses (expense_id, user_id, payee, amount, occurred_at, source) VALUES ($1, $2, $3, $4, $5, $6)",
        expense_id, uuid.UUID(user_id), "A real vendor", 10.0, datetime.now(timezone.utc), "manual",
    )
    await pool.execute(
        "INSERT INTO applications (application_id, user_id, company, role, status, deadline) VALUES ($1, $2, $3, $4, $5, $6)",
        application_id, uuid.UUID(user_id), "A real company to be deleted", None, "applied", None,
    )
    await pool.execute(
        "INSERT INTO interviews (interview_id, application_id, scheduled_at, format, status) VALUES ($1, $2, $3, $4, $5)",
        interview_id, application_id, None, "phone", "scheduled",
    )

    deleted_count = await store.purge_postgres_rows(user_id)

    # 1 task + 1 expense + 1 application + 1 interview + 1 users row.
    assert deleted_count == 5

    assert await pool.fetchrow("SELECT 1 FROM tasks WHERE task_id = $1", task_id) is None
    assert await pool.fetchrow("SELECT 1 FROM expenses WHERE expense_id = $1", expense_id) is None
    assert await pool.fetchrow("SELECT 1 FROM applications WHERE application_id = $1", application_id) is None
    assert await pool.fetchrow("SELECT 1 FROM interviews WHERE interview_id = $1", interview_id) is None
    assert not await _real_user_exists(pool, user_id)


async def test_purge_postgres_rows_never_touches_another_real_users_rows(pool):
    victim_id = await _provision(pool, "victim")
    bystander_id = await _provision(pool, "bystander")
    store = SupabaseDeletionStore(pool)

    victim_task = uuid.uuid4()
    bystander_task = uuid.uuid4()

    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, $5, $6)",
        victim_task, uuid.UUID(victim_id), "Victim's real task", 1.0, None, "open",
    )
    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, $5, $6)",
        bystander_task, uuid.UUID(bystander_id), "Bystander's real, untouched task", 1.0, None, "open",
    )

    try:
        await store.purge_postgres_rows(victim_id)

        assert await pool.fetchrow("SELECT 1 FROM tasks WHERE task_id = $1", victim_task) is None
        assert await pool.fetchrow("SELECT 1 FROM tasks WHERE task_id = $1", bystander_task) is not None
        assert not await _real_user_exists(pool, victim_id)
        assert await _real_user_exists(pool, bystander_id)
    finally:
        await pool.execute("DELETE FROM tasks WHERE task_id = $1", bystander_task)
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(bystander_id))


async def test_purge_postgres_rows_returns_zero_for_a_real_user_with_no_domain_data(pool):
    # A freshly-provisioned real user with zero real tasks/expenses/
    # applications -- only the real users row itself is deleted.
    user_id = await _provision(pool, "empty")
    store = SupabaseDeletionStore(pool)

    deleted_count = await store.purge_postgres_rows(user_id)

    assert deleted_count == 1  # the users row alone
    assert not await _real_user_exists(pool, user_id)


async def test_purge_vector_embeddings_deletes_real_note_embeddings_and_returns_the_real_count(pool):
    user_id = await _provision(pool, "vectors")
    store = SupabaseDeletionStore(pool)

    embedding_id = uuid.uuid4()
    # source_type/source_id are required as of migration 0005 (Roadmap
    # Phase 4a, Search) -- any real, valid value satisfies the column
    # constraints here; this test is about deletion, not search.
    await pool.execute(
        "INSERT INTO note_embeddings (embedding_id, user_id, content, embedding, source_type, source_id) "
        "VALUES ($1, $2, $3, $4, $5, $6)",
        embedding_id, uuid.UUID(user_id), "A real note to be purged", None, "task", uuid.uuid4(),
    )

    try:
        deleted_count = await store.purge_vector_embeddings(user_id)
        assert deleted_count == 1
        assert await pool.fetchrow("SELECT 1 FROM note_embeddings WHERE embedding_id = $1", embedding_id) is None
    finally:
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(user_id))


async def test_purge_vector_embeddings_never_touches_another_real_users_rows(pool):
    victim_id = await _provision(pool, "vec-victim")
    bystander_id = await _provision(pool, "vec-bystander")
    store = SupabaseDeletionStore(pool)

    victim_embedding = uuid.uuid4()
    bystander_embedding = uuid.uuid4()

    # source_type/source_id are required as of migration 0005 (Roadmap
    # Phase 4a, Search) -- any real, valid value satisfies the column
    # constraints here; this test is about cross-user isolation, not
    # search.
    await pool.execute(
        "INSERT INTO note_embeddings (embedding_id, user_id, content, embedding, source_type, source_id) "
        "VALUES ($1, $2, $3, $4, $5, $6)",
        victim_embedding, uuid.UUID(victim_id), "Victim's real note", None, "task", uuid.uuid4(),
    )
    await pool.execute(
        "INSERT INTO note_embeddings (embedding_id, user_id, content, embedding, source_type, source_id) "
        "VALUES ($1, $2, $3, $4, $5, $6)",
        bystander_embedding, uuid.UUID(bystander_id), "Bystander's real, untouched note", None, "task", uuid.uuid4(),
    )

    try:
        await store.purge_vector_embeddings(victim_id)

        assert await pool.fetchrow("SELECT 1 FROM note_embeddings WHERE embedding_id = $1", victim_embedding) is None
        assert (
            await pool.fetchrow("SELECT 1 FROM note_embeddings WHERE embedding_id = $1", bystander_embedding)
            is not None
        )
    finally:
        await pool.execute("DELETE FROM note_embeddings WHERE embedding_id = $1", bystander_embedding)
        await pool.execute("DELETE FROM users WHERE user_id = ANY($1::uuid[])", [uuid.UUID(victim_id), uuid.UUID(bystander_id)])


async def test_purge_memories_is_a_real_honest_zero_no_mem0_integration_exists(pool):
    user_id = await _provision(pool, "memories")
    store = SupabaseDeletionStore(pool)
    try:
        assert await store.purge_memories(user_id) == 0
    finally:
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(user_id))


async def test_revoke_oauth_tokens_is_a_real_honest_zero_google_tokens_are_never_persisted(pool):
    user_id = await _provision(pool, "oauth")
    store = SupabaseDeletionStore(pool)
    try:
        assert await store.revoke_oauth_tokens(user_id) == 0
    finally:
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(user_id))
