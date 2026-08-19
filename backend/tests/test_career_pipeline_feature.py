"""Real tests for features/career_pipeline.py -- against the real, live
Supabase database (`DEC-098`), real INSERTs, a real query, real
DELETEs in a `finally` block, mirroring `test_tasks_feature.py`'s own
established pattern. Every inserted row uses a real, generated
`application_id` and is deleted by that same id -- these tests can
never collide with real data and never leave anything behind, even if
a test itself fails midway.

Real per-user scoping retrofit (`DEC-110`): `fetch_career_pipeline()`
now requires a real, provisioned internal `user_id`. The `user_id`
fixture below provisions one real, fresh test identity per test (via
the real `users` table, mirroring what `/auth/token` does at real
sign-in) and cleans it up afterward.
"""
import uuid
from datetime import datetime, timezone

import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.features.career_pipeline import fetch_career_pipeline


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-career-{uuid.uuid4()}"
    real_user_id = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield real_user_id
    await pool.execute("DELETE FROM users WHERE google_sub = $1", google_sub)


async def _insert_test_application(pool, application_id, *, company, role, status, deadline, user_id):
    await pool.execute(
        """
        INSERT INTO applications (application_id, user_id, company, role, status, deadline)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        application_id,
        uuid.UUID(user_id),
        company,
        role,
        status,
        deadline,
    )


async def test_fetch_career_pipeline_returns_real_rows_with_correct_shape_and_types(pool, user_id):
    application_id = uuid.uuid4()
    deadline = datetime(2020, 2, 1, 0, 0, tzinfo=timezone.utc)

    try:
        await _insert_test_application(
            pool,
            application_id,
            company="A real, deliberately obscure test company",
            role="Software Engineer",
            status="applied",
            deadline=deadline,
            user_id=user_id,
        )

        records = await fetch_career_pipeline(pool, user_id=user_id)
        match = next(r for r in records if r.application_id == str(application_id))

        assert match.company == "A real, deliberately obscure test company"
        assert match.role == "Software Engineer"
        assert match.status == "applied"
        assert match.deadline == "2020-02-01T00:00:00Z"
    finally:
        await pool.execute("DELETE FROM applications WHERE application_id = $1", application_id)


async def test_fetch_career_pipeline_handles_a_real_null_role_and_deadline(pool, user_id):
    application_id = uuid.uuid4()

    try:
        await _insert_test_application(
            pool,
            application_id,
            company="A real company with no role or deadline yet",
            role=None,
            status="applied",
            deadline=None,
            user_id=user_id,
        )

        records = await fetch_career_pipeline(pool, user_id=user_id)
        match = next(r for r in records if r.application_id == str(application_id))

        assert match.role is None
        assert match.deadline is None
    finally:
        await pool.execute("DELETE FROM applications WHERE application_id = $1", application_id)


async def test_fetch_career_pipeline_preserves_a_real_genuinely_open_status_vocabulary(pool, user_id):
    # applications.status has NO real CHECK constraint (the deliberate
    # opposite of tasks.status) -- this test proves an unrecognized,
    # made-up status value round-trips through the query completely
    # unchanged, never rejected or normalized.
    application_id = uuid.uuid4()
    made_up_status = "phone_screen_pending"

    try:
        await _insert_test_application(
            pool,
            application_id,
            company="A real company with a genuinely novel status",
            role=None,
            status=made_up_status,
            deadline=None,
            user_id=user_id,
        )

        records = await fetch_career_pipeline(pool, user_id=user_id)
        match = next(r for r in records if r.application_id == str(application_id))

        assert match.status == made_up_status
    finally:
        await pool.execute("DELETE FROM applications WHERE application_id = $1", application_id)


async def test_fetch_career_pipeline_returns_a_real_empty_list_never_a_crash_when_nothing_matches(pool, user_id):
    # A real, honest proof this query never assumes at least one row --
    # a freshly-provisioned real user genuinely has zero real
    # applications.
    records = await fetch_career_pipeline(pool, user_id=user_id)
    assert records == []


async def test_fetch_career_pipeline_never_returns_another_real_users_rows(pool, user_id):
    other_google_sub = f"test-career-other-{uuid.uuid4()}"
    other_user_id = await get_or_create_user(pool, google_sub=other_google_sub, email=None)
    application_id = uuid.uuid4()

    try:
        await _insert_test_application(
            pool,
            application_id,
            company="Another real user's real, private company",
            role=None,
            status="applied",
            deadline=None,
            user_id=other_user_id,
        )

        records = await fetch_career_pipeline(pool, user_id=user_id)
        assert all(r.application_id != str(application_id) for r in records)
    finally:
        await pool.execute("DELETE FROM applications WHERE application_id = $1", application_id)
        await pool.execute("DELETE FROM users WHERE google_sub = $1", other_google_sub)
