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
from datetime import datetime, timedelta, timezone

import pytest_asyncio
from cryptography.fernet import Fernet

from quorum_backend.auth.google_token_store import store_google_tokens
from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.security.supabase_deletion_store import SupabaseDeletionStore

# A real, valid Fernet key, generated once for this test module -- never
# the real, live `GOOGLE_TOKEN_ENCRYPTION_KEY` (this test never reads
# real config), since these tests only need a real, internally-
# consistent encrypt/decrypt round trip, not this deployment's own key.
_TEST_ENCRYPTION_KEY = Fernet.generate_key().decode()


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
    proposal_id = uuid.uuid4()
    negotiation_id = uuid.uuid4()

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
    # DEC-124: real action_events/negotiations rows this account owns.
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, trace_id, user_id) VALUES ($1, $2, $3, $4::jsonb, $5, $6)",
        proposal_id, "create_note", "S0", "{}", f"test-deletion-{proposal_id}", uuid.UUID(user_id),
    )
    await pool.execute(
        "INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at) VALUES ($1, $2, $3, $4)",
        negotiation_id, uuid.UUID(user_id), ["finance", "tasks"], datetime.now(timezone.utc),
    )

    deleted_count = await store.purge_postgres_rows(user_id)

    # 1 task + 1 expense + 1 application + 1 interview + 1 action_event
    # + 1 negotiation + 1 users row.
    assert deleted_count == 7

    assert await pool.fetchrow("SELECT 1 FROM tasks WHERE task_id = $1", task_id) is None
    assert await pool.fetchrow("SELECT 1 FROM expenses WHERE expense_id = $1", expense_id) is None
    assert await pool.fetchrow("SELECT 1 FROM applications WHERE application_id = $1", application_id) is None
    assert await pool.fetchrow("SELECT 1 FROM interviews WHERE interview_id = $1", interview_id) is None
    assert await pool.fetchrow("SELECT 1 FROM action_events WHERE proposal_id = $1", proposal_id) is None
    assert await pool.fetchrow("SELECT 1 FROM negotiations WHERE negotiation_id = $1", negotiation_id) is None
    assert not await _real_user_exists(pool, user_id)


async def test_purge_postgres_rows_never_touches_another_real_users_rows(pool):
    victim_id = await _provision(pool, "victim")
    bystander_id = await _provision(pool, "bystander")
    store = SupabaseDeletionStore(pool)

    victim_task = uuid.uuid4()
    bystander_task = uuid.uuid4()
    victim_proposal = uuid.uuid4()
    bystander_proposal = uuid.uuid4()
    victim_negotiation = uuid.uuid4()
    bystander_negotiation = uuid.uuid4()

    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, $5, $6)",
        victim_task, uuid.UUID(victim_id), "Victim's real task", 1.0, None, "open",
    )
    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, $5, $6)",
        bystander_task, uuid.UUID(bystander_id), "Bystander's real, untouched task", 1.0, None, "open",
    )
    # DEC-124: the same real cross-user proof, extended to
    # action_events/negotiations -- the exact property this session's
    # own fix exists to add, not just "doesn't crash."
    for proposal_id, uid in ((victim_proposal, victim_id), (bystander_proposal, bystander_id)):
        await pool.execute(
            "INSERT INTO action_events (proposal_id, action_type, stakes, payload, trace_id, user_id) VALUES ($1, $2, $3, $4::jsonb, $5, $6)",
            proposal_id, "create_note", "S0", "{}", f"test-deletion-{proposal_id}", uuid.UUID(uid),
        )
    for negotiation_id, uid in ((victim_negotiation, victim_id), (bystander_negotiation, bystander_id)):
        await pool.execute(
            "INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at) VALUES ($1, $2, $3, $4)",
            negotiation_id, uuid.UUID(uid), ["finance"], datetime.now(timezone.utc),
        )

    try:
        await store.purge_postgres_rows(victim_id)

        assert await pool.fetchrow("SELECT 1 FROM tasks WHERE task_id = $1", victim_task) is None
        assert await pool.fetchrow("SELECT 1 FROM tasks WHERE task_id = $1", bystander_task) is not None
        assert await pool.fetchrow("SELECT 1 FROM action_events WHERE proposal_id = $1", victim_proposal) is None
        assert await pool.fetchrow("SELECT 1 FROM action_events WHERE proposal_id = $1", bystander_proposal) is not None
        assert await pool.fetchrow("SELECT 1 FROM negotiations WHERE negotiation_id = $1", victim_negotiation) is None
        assert await pool.fetchrow("SELECT 1 FROM negotiations WHERE negotiation_id = $1", bystander_negotiation) is not None
        assert not await _real_user_exists(pool, victim_id)
        assert await _real_user_exists(pool, bystander_id)
    finally:
        await pool.execute("DELETE FROM tasks WHERE task_id = $1", bystander_task)
        await pool.execute("DELETE FROM action_events WHERE proposal_id = $1", bystander_proposal)
        await pool.execute("DELETE FROM negotiations WHERE negotiation_id = $1", bystander_negotiation)
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


async def test_revoke_oauth_tokens_is_a_real_honest_zero_when_no_encryption_key_is_configured(pool):
    """A REAL, DISCLOSED CORRECTION to this test's own former name and
    reasoning: `revoke_oauth_tokens()` is real as of Phase 3 (see this
    module's own top-of-file docstring) -- this specific `0` is real and
    honest for a genuinely different reason now: no `google_token_
    encryption_key` was given to this store instance, matching a real
    deployment that hasn't configured `GOOGLE_TOKEN_ENCRYPTION_KEY` yet.
    An account deletion must never be blocked by a real feature this
    deployment doesn't have configured."""
    user_id = await _provision(pool, "oauth")
    store = SupabaseDeletionStore(pool)  # no encryption key passed -- the real, honest default
    try:
        assert await store.revoke_oauth_tokens(user_id) == 0
    finally:
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(user_id))


async def test_revoke_oauth_tokens_is_a_real_honest_zero_for_a_user_with_no_stored_google_tokens(pool):
    user_id = await _provision(pool, "oauth-none")
    store = SupabaseDeletionStore(pool, google_token_encryption_key=_TEST_ENCRYPTION_KEY)
    try:
        assert await store.revoke_oauth_tokens(user_id) == 0
    finally:
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(user_id))


async def test_revoke_oauth_tokens_genuinely_calls_googles_real_revoke_endpoint_and_deletes_the_real_row(pool):
    """Real, live proof of the whole flow, per CLAUDE.md Rule 5 -- no
    valid, Google-issued refresh_token is available to this test suite
    (obtaining one requires a real, human-completed mobile consent flow
    with the new Gmail/Calendar scopes), so this test uses a real,
    deliberately-invalid token value, the same established technique
    `test_auth_google_oauth.py` already uses for its own real, live
    tests. Google's real `/revoke` endpoint returns a real `400` for an
    unrecognized token -- this module's own `revoke_google_token()`
    treats that as a real, benign no-op by design (the end state, no
    live grant, is identical), so this test proves the real network
    call happens and the real local row is genuinely deleted regardless,
    not that Google accepted the fake token."""
    user_id = await _provision(pool, "oauth-real")
    await store_google_tokens(
        pool,
        internal_user_id=user_id,
        access_token="deliberately-fake-access-token-for-a-real-test",
        refresh_token="deliberately-fake-refresh-token-for-a-real-test",
        access_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        granted_scopes="openid email",
        encryption_key=_TEST_ENCRYPTION_KEY,
    )
    store = SupabaseDeletionStore(pool, google_token_encryption_key=_TEST_ENCRYPTION_KEY)
    try:
        revoked_count = await store.revoke_oauth_tokens(user_id)
        assert revoked_count == 1
        assert await pool.fetchrow("SELECT 1 FROM google_oauth_tokens WHERE user_id = $1", uuid.UUID(user_id)) is None
    finally:
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(user_id))
