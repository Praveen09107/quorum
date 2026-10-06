"""Real tests for main.py -- confirms core/config.py is genuinely
consumed at real app startup, not just an unreferenced file, and (Batch
10 Phase 3) that the real auth routes and the real Bearer-auth gate on
/trust_digest genuinely work end to end against the real, live database.
"""
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest_asyncio
from fastapi.testclient import TestClient

from quorum_backend.auth.access_token import create_access_token
from quorum_backend.auth.refresh_token import TokenRevoked, issue_refresh_token, rotate_refresh_token
from quorum_backend.auth.revocation_store import SupabaseRevocationStore
from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.core.config import get_settings
from quorum_backend.main import app

import pytest


def _auth_header() -> dict[str, str]:
    """A real, valid access token, created directly via the real
    create_access_token() -- bypasses the real Google login flow
    (which needs a live browser this environment doesn't have), while
    still exercising the real signing key and the real decode path on
    the receiving end. Deliberately NOT real-provisioned -- correct for
    tests that only need a syntactically valid session (missing-auth,
    malformed-header, 503 cases). Any test exercising a real per-user
    query needs `_provisioned_auth_header()` below instead, or this
    real identity will correctly 404 (DEC-110)."""
    settings = get_settings()
    token = create_access_token("test-user-" + str(uuid.uuid4()), settings.jwt_signing_key)
    return {"Authorization": f"Bearer {token}"}


async def _provisioned_auth_header(pool, provisioned_users: list[str]) -> tuple[dict[str, str], str]:
    """Real end-to-end: provisions a real `users` row for a fresh, fake
    Google identity (mirroring what `/auth/token` does for a real
    sign-in), then mints a real access token for that same identity.
    Returns both the header and the real internal UUID, so a test can
    insert domain rows scoped to the exact same real user this token
    resolves to (DEC-110).

    A real, disclosed correction, found by fresh-context review before
    merge: the original version of this helper provisioned a real row
    and never cleaned it up -- confirmed live, this left 10 real
    orphaned rows in the live `users` table from this session's own
    test runs alone. `google_sub` is appended to `provisioned_users`
    (the `provisioned_users` fixture below) so every real row this
    helper creates is genuinely deleted on teardown, even if the test
    itself fails midway."""
    settings = get_settings()
    google_sub = f"test-user-{uuid.uuid4()}"
    internal_user_id = await get_or_create_user(pool, google_sub=google_sub, email=None)
    provisioned_users.append(google_sub)
    token = create_access_token(google_sub, settings.jwt_signing_key)
    return {"Authorization": f"Bearer {token}"}, internal_user_id


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def provisioned_users(pool):
    """Real, automatic cleanup for every real `users` row
    `_provisioned_auth_header()` creates during a test -- collects each
    real `google_sub` as it's provisioned, deletes them all in one real
    pass on teardown, the same `finally`-guaranteed cleanup discipline
    every other real fixture in this project's test suite already
    holds itself to."""
    created: list[str] = []
    yield created
    if created:
        await pool.execute("DELETE FROM users WHERE google_sub = ANY($1::text[])", created)


def test_health_endpoint_still_works():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_real_startup_warns_when_the_insecure_default_jwt_key_is_still_active(monkeypatch, caplog):
    monkeypatch.delenv("JWT_SIGNING_KEY", raising=False)
    get_settings.cache_clear()

    with caplog.at_level(logging.WARNING, logger="quorum_backend"):
        with TestClient(app):
            pass  # entering the context manager runs the real lifespan startup

    assert any("insecure default" in record.message.lower() for record in caplog.records)
    get_settings.cache_clear()


def test_real_startup_does_not_warn_once_a_real_secret_is_configured(monkeypatch, caplog):
    monkeypatch.setenv("JWT_SIGNING_KEY", "a-real-generated-production-secret")
    get_settings.cache_clear()

    with caplog.at_level(logging.WARNING, logger="quorum_backend"):
        with TestClient(app):
            pass

    assert not any("insecure default" in record.message.lower() for record in caplog.records)
    get_settings.cache_clear()


def test_trust_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.get("/trust")
    assert response.status_code == 401


def test_trust_endpoint_runs_the_real_default_scenario_suite_against_the_real_gate():
    """Real, live -- no mocking of self_test_harness.py or gate.review().
    Confirms the exact real, current default suite (3 scenarios, all
    genuinely expected to pass -- clean S0 approval, a Stage A hard-fail
    revise, a real S3 Critic-objection escalation) and the real, honest
    `target` label this repository always produces."""
    with TestClient(app) as client:
        response = client.get("/trust", headers=_auth_header())
    assert response.status_code == 200
    body = response.json()

    assert set(body.keys()) == {"total", "caught", "missed", "results", "target"}
    assert body["target"] == "real_gate"
    assert body["total"] == 3
    assert body["caught"] == 3
    assert body["missed"] == []
    assert len(body["results"]) == 3

    for result in body["results"]:
        # `verdict` added `DEC-193` -- real, disclosed correction: the
        # spec's own example for this route literally reads "every
        # ScenarioResult, never filtered," and `self_test_harness.py`'s
        # own docstring already said the same thing; this route had
        # been the one real, unforced deviation from both. See
        # `_serialize_scenario_result()`'s own docstring for the full
        # account.
        assert set(result.keys()) == {"scenario_id", "expected", "actual", "passed", "verdict"}
        assert result["passed"] is True
        assert result["expected"] == result["actual"]
        # The real, full Gate verdict behind this scenario -- genuinely
        # present, not an empty placeholder.
        assert result["verdict"]["decision"] in ("approve", "revise", "reject", "escalate_to_human")
        assert "trace_id" in result["verdict"]

    scenario_ids = {r["scenario_id"] for r in body["results"]}
    assert scenario_ids == {"S0_clean_approval", "S2_stage_a_hard_fail", "S3_real_critic_objection_escalates"}


def test_trust_endpoint_missed_is_a_real_honest_subset_never_hidden(monkeypatch):
    """A real, deliberately mis-specified scenario (a genuine expectation
    mismatch, not a Gate bug) must surface in `missed` with the same
    prominence as a catch -- the same real proof self_test_harness.py's
    own test suite already establishes at the function level, exercised
    here through the real HTTP route."""
    from quorum_backend import main as main_module
    from quorum_backend.features.self_test_harness import (
        AdversarialScenario,
        _default_scenarios,
        run_self_test as real_run_self_test,
    )

    real_scenarios = _default_scenarios()
    mis_specified = AdversarialScenario(
        scenario_id="deliberately_mis_specified",
        description="A real clean approval, deliberately asserted against the wrong expected decision.",
        proposal=real_scenarios[0].proposal,
        stakes=real_scenarios[0].stakes,
        stage_a_checks=real_scenarios[0].stage_a_checks,
        critic_call=real_scenarios[0].critic_call,
        judge_call=real_scenarios[0].judge_call,
        expected_decision="reject",  # the real Gate will actually approve this
    )

    async def _fake_run_self_test(scenarios=None, target="real_gate"):
        return await real_run_self_test(scenarios=[mis_specified], target=target)

    monkeypatch.setattr(main_module, "run_self_test", _fake_run_self_test)

    with TestClient(app) as client:
        response = client.get("/trust", headers=_auth_header())

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["caught"] == 0
    assert len(body["missed"]) == 1
    assert body["missed"][0]["scenario_id"] == "deliberately_mis_specified"
    assert body["missed"][0]["passed"] is False


def test_trust_digest_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.get("/trust_digest")
    assert response.status_code == 401


def test_trust_digest_rejects_a_malformed_authorization_header():
    with TestClient(app) as client:
        response = client.get("/trust_digest", headers={"Authorization": "not-a-bearer-token"})
    assert response.status_code == 401


def test_trust_digest_rejects_a_real_but_expired_access_token():
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expired_token = jwt.encode(
        {"sub": "test-user", "iat": now - timedelta(minutes=30), "exp": now - timedelta(minutes=15)},
        settings.jwt_signing_key,
        algorithm="HS256",
    )
    with TestClient(app) as client:
        response = client.get("/trust_digest", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


async def test_trust_digest_endpoint_is_real_and_live_not_mocked_with_a_real_valid_token(pool, provisioned_users):
    """Real, end-to-end: the real lifespan creates a real DB pool
    against the real, live Supabase database (DEC-098), and this
    request genuinely round-trips through it once a real, valid,
    PROVISIONED access token is presented -- `DEC-150` real per-user
    scoping means `_auth_header()`'s own unprovisioned identity would
    now correctly 404 here, so this test uses `_provisioned_auth_
    header()` instead, matching every other real per-user-scoped route
    test in this file. Asserts shape and types only, never specific
    counts -- real production data changes as this project actually
    gets used, and a value-based assertion here would be exactly the
    stale-restated-number drift pattern CLAUDE.md warns against."""
    headers, _internal_user_id = await _provisioned_auth_header(pool, provisioned_users)

    with TestClient(app) as client:
        response = client.get("/trust_digest", headers=headers)

    assert response.status_code == 200
    body = response.json()

    assert set(body.keys()) == {"current_week", "previous_week", "trend", "delta"}
    assert body["trend"] in {"improving", "declining", "stable", "insufficient_data"}

    current = body["current_week"]
    assert set(current.keys()) == {"week_start", "total_actions", "success_rate"}
    assert isinstance(current["total_actions"], int)
    assert isinstance(current["success_rate"], float)

    if body["previous_week"] is not None:
        assert set(body["previous_week"].keys()) == {"week_start", "total_actions", "success_rate"}


async def test_trust_digest_endpoint_never_counts_another_real_users_action_events(pool, provisioned_users):
    """RESOLVED, `DEC-150`: the real, load-bearing correctness property
    this fix exists to guarantee -- two distinct real users, two
    distinct real `action_events` rows this real calendar week, a
    request as user A must report a real digest reflecting only A's own
    row, never B's. Before this fix, both rows would have been
    aggregated together regardless of which user's token was presented."""
    headers_a, user_a = await _provisioned_auth_header(pool, provisioned_users)
    _headers_b, user_b = await _provisioned_auth_header(pool, provisioned_users)
    proposal_a, proposal_b = uuid.uuid4(), uuid.uuid4()
    now = datetime.now(timezone.utc)

    async def _insert(proposal_id, user_id):
        await pool.execute(
            "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at) "
            "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)",
            proposal_id, "create_note", "S0", "{}", "approve", "approved_unchanged",
            f"test-trust-digest-isolation-{proposal_id}", uuid.UUID(user_id), now,
        )

    try:
        await _insert(proposal_a, user_a)
        await _insert(proposal_b, user_b)

        with TestClient(app) as client:
            response_a = client.get("/trust_digest", headers=headers_a)

        assert response_a.status_code == 200
        # User A's own real week must show exactly the 1 real action
        # they own -- never 2, which would mean user B's row leaked in.
        assert response_a.json()["current_week"]["total_actions"] == 1
    finally:
        await pool.execute("DELETE FROM action_events WHERE proposal_id = ANY($1::uuid[])", [proposal_a, proposal_b])


def test_trust_digest_returns_503_not_a_crash_when_the_real_pool_is_unavailable():
    """Proves /health's own independence from database reachability
    (the real reasoning documented in main.py's lifespan): simulates a
    real startup-failure state by clearing the real pool reference
    after a genuine successful startup, confirms the endpoint that
    needs it fails loud with a real 503 rather than a raw exception,
    and that /health is entirely unaffected.

    A plain try/finally, not `monkeypatch`, restores the real pool
    reference deliberately: it must happen BEFORE the `with TestClient`
    block exits, since exiting runs the real lifespan shutdown, which
    closes whatever `app.state.db_pool` currently is -- `monkeypatch`'s
    own teardown only runs after that point, which would leave the
    real pool this fixture created never actually closed.
    """
    with TestClient(app) as client:
        real_pool = app.state.db_pool
        app.state.db_pool = None
        try:
            digest_response = client.get("/trust_digest", headers=_auth_header())
            health_response = client.get("/health")
            assert digest_response.status_code == 503
            assert health_response.status_code == 200
        finally:
            app.state.db_pool = real_pool


def test_tasks_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.get("/tasks")
    assert response.status_code == 401


async def test_tasks_endpoint_is_real_and_live_not_mocked_with_a_real_valid_token(pool, provisioned_users):
    """Real, end-to-end: real-provisions a real user (DEC-110), inserts
    a real row scoped to that exact user into the real, live `tasks`
    table, confirms `GET /tasks` genuinely round-trips through it with
    a real, valid access token for that same real identity, then cleans
    up. Asserts shape and the specific inserted row's own values, never
    a total count -- real production rows may already exist, and
    asserting a count would be the exact stale-restated-number drift
    pattern CLAUDE.md warns against."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    task_id = uuid.uuid4()
    await pool.execute(
        """
        INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        task_id,
        uuid.UUID(internal_user_id),
        "A real end-to-end test task",
        3.5,
        None,
        "open",
    )

    try:
        with TestClient(app) as client:
            response = client.get("/tasks", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)

        match = next(t for t in body if t["task_id"] == str(task_id))
        assert set(match.keys()) == {"task_id", "title", "estimated_hours", "deadline", "status"}
        assert match["title"] == "A real end-to-end test task"
        assert match["estimated_hours"] == 3.5
        assert match["deadline"] is None
        assert match["status"] == "open"
    finally:
        await pool.execute("DELETE FROM tasks WHERE task_id = $1", task_id)


async def test_tasks_endpoint_never_leaks_another_real_users_rows(pool, provisioned_users):
    """The real, load-bearing correctness property DEC-110 exists to
    guarantee: two distinct real users, two distinct real tasks -- a
    request as user A must see only user A's task, never user B's."""
    headers_a, user_a = await _provisioned_auth_header(pool, provisioned_users)
    _headers_b, user_b = await _provisioned_auth_header(pool, provisioned_users)
    task_a, task_b = uuid.uuid4(), uuid.uuid4()

    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, $5, $6)",
        task_a,
        uuid.UUID(user_a),
        "User A's real, private task",
        1.0,
        None,
        "open",
    )
    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, $5, $6)",
        task_b,
        uuid.UUID(user_b),
        "User B's real, private task",
        1.0,
        None,
        "open",
    )

    try:
        with TestClient(app) as client:
            response = client.get("/tasks", headers=headers_a)

        body = response.json()
        ids_seen = {t["task_id"] for t in body}
        assert str(task_a) in ids_seen
        assert str(task_b) not in ids_seen
    finally:
        await pool.execute("DELETE FROM tasks WHERE task_id = ANY($1::uuid[])", [task_a, task_b])


def test_tasks_returns_503_not_a_crash_when_the_real_pool_is_unavailable():
    """Same real, honest failure mode as /trust_digest's own equivalent
    test -- /health stays unaffected, /tasks fails loud with a real 503
    rather than a raw exception."""
    with TestClient(app) as client:
        real_pool = app.state.db_pool
        app.state.db_pool = None
        try:
            tasks_response = client.get("/tasks", headers=_auth_header())
            health_response = client.get("/health")
            assert tasks_response.status_code == 503
            assert health_response.status_code == 200
        finally:
            app.state.db_pool = real_pool


# --- POST /quick_capture (Phase 7, DEC-153) ---


def test_quick_capture_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.post("/quick_capture", json={"text": "finish the report"})
    assert response.status_code == 401


def test_quick_capture_rejects_blank_text_with_a_real_422_before_any_real_extraction_call():
    with TestClient(app) as client:
        response = client.post("/quick_capture", json={"text": "   "}, headers=_auth_header())
    assert response.status_code == 422


def test_quick_capture_returns_503_when_the_extraction_provider_is_not_configured(monkeypatch):
    """Same real, established convention `test_search_returns_503_when_
    the_embedding_provider_is_not_configured` already uses -- a real
    `model_copy()` override, not a hand-rolled fake settings object
    that would break the app's own real startup lifespan. Checks the
    real extraction provider -- Gemini, DELIBERATELY kept, not migrated
    to Groq alongside 3 of the 4 other real call sites `DEC-166`
    touched: a CRITICAL-tier review caught, before merge, that moving
    this specific call to Groq would violate CLAUDE.md's own Generator/
    Judge-vs-Critic provider-diversity rule, which groups the real
    Generator (this extraction call) and the real Judge together as one
    same-provider unit -- NOT because the real Critic would otherwise
    review this call's own output (a later, `DEC-170` follow-up review
    found and corrected that specific claim: `CREATE_TASK` is real
    `Stakes.S1`, so Stage B -- and the Critic with it -- never runs on
    this route at all). See `main.py`'s own route docstring for the
    full, corrected account. `QUORUM_FINAL_COMPLETION_PLAN.md` Session 4
    later extended this same real Gemini call to a second domain (Finance)
    rather than adding a second, Groq-backed one, for the identical
    real reason -- see that route's own docstring addendum."""
    from quorum_backend import main as main_module

    fake_settings = get_settings().model_copy(update={"gemini_api_key": None})
    monkeypatch.setattr(main_module, "get_settings", lambda: fake_settings)
    with TestClient(app) as client:
        response = client.post("/quick_capture", json={"text": "finish the report"}, headers=_auth_header())
    assert response.status_code == 503


@pytest.mark.skipif(get_settings().gemini_api_key is None, reason="no real GEMINI_API_KEY configured in this environment")
async def test_quick_capture_endpoint_is_real_and_live_creates_a_real_task_end_to_end(pool, provisioned_users):
    """The real, live, end-to-end proof `QUORUM_PRODUCTION_COMPLETION_
    PLAN.md`'s own Phase 7 verification line asks for: a real proposal
    created from real free text, reviewed by the real Gate, and
    genuinely visible afterward (here, via a direct real `tasks` row
    read -- the same real table `GET /today`'s own Holding Steady zone
    and `GET /tasks` both already read from)."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    marker = f"real quick-capture test {uuid.uuid4()}"

    try:
        with TestClient(app) as client:
            response = client.post(
                "/quick_capture",
                json={"text": f"{marker}, should take about one hour, no particular deadline"},
                headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["stakes"] == "S1"
        assert body["domain"] == "tasks"
        # A real, genuine approve is the overwhelmingly likely real
        # outcome here (a fresh user, no existing tasks to conflict
        # with) -- asserted directly rather than treated as optional,
        # since a live, unexpected Gate rejection on this simple a
        # real input would itself be a real, worth-investigating bug.
        assert body["executed"] is True
        assert body["decision"] == "approve"
        assert marker in body["title"]

        row = await pool.fetchrow(
            "SELECT title, estimated_hours FROM tasks WHERE user_id = $1 AND title LIKE $2",
            uuid.UUID(internal_user_id), f"%{marker}%",
        )
        assert row is not None
        assert row["estimated_hours"] > 0
    finally:
        await pool.execute("DELETE FROM tasks WHERE user_id = $1", uuid.UUID(internal_user_id))
        await pool.execute("DELETE FROM action_events WHERE user_id = $1", uuid.UUID(internal_user_id))


# --- POST /applications (`DEC-194`, product rebuild Block F) ---


def test_create_application_endpoint_requires_real_auth():
    with TestClient(app) as client:
        response = client.post("/applications", json={"company": "Stripe"})
    assert response.status_code == 401


async def test_create_application_endpoint_is_real_and_live_creates_a_real_application_end_to_end(pool, provisioned_users):
    """The real, first end-to-end proof that a job application can be
    created at all -- closing the single most explicitly-named backend
    gap in the original rebuild mandate. `CREATE_APPLICATION` is real
    `Stakes.S1`, so Stage B never runs -- no real Gemini/Groq key is
    needed for this to pass, matching `CREATE_TASK`'s own identical
    real precedent."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    marker = f"Real Co {uuid.uuid4()}"

    try:
        with TestClient(app) as client:
            response = client.post(
                "/applications",
                json={"company": marker, "role": "Backend Engineer"},
                headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["stakes"] == "S1"
        assert body["domain"] == "career"
        assert body["operation"] == "create"
        assert body["executed"] is True
        assert body["decision"] == "approve"
        assert body["company"] == marker

        row = await pool.fetchrow(
            "SELECT company, role, status FROM applications WHERE user_id = $1 AND company = $2",
            uuid.UUID(internal_user_id), marker,
        )
        assert row is not None
        assert row["role"] == "Backend Engineer"
        assert row["status"] == "applied"
    finally:
        await pool.execute("DELETE FROM applications WHERE user_id = $1", uuid.UUID(internal_user_id))
        await pool.execute("DELETE FROM action_events WHERE user_id = $1", uuid.UUID(internal_user_id))


async def test_create_application_endpoint_rejects_an_empty_company_with_a_real_502_not_a_500(pool, provisioned_users):
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    with TestClient(app) as client:
        response = client.post("/applications", json={"company": "   "}, headers=headers)
    assert response.status_code == 502


# --- POST /interviews (`DEC-195`, product rebuild Block F remainder) ---


def test_schedule_interview_endpoint_requires_real_auth():
    with TestClient(app) as client:
        response = client.post("/interviews", json={"application_id": "app_1"})
    assert response.status_code == 401


async def test_schedule_interview_endpoint_is_real_and_live_schedules_a_real_interview_end_to_end(pool, provisioned_users):
    """The real, first end-to-end proof that the `interviews` table
    (unused since migration `0001`) can genuinely be written to at
    all. `CREATE_INTERVIEW` is real `Stakes.S1` -- no real Gemini/Groq
    key is needed for this to pass, matching `POST /applications`'s
    own identical real precedent."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    application_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO applications (application_id, user_id, company) VALUES ($1, $2, $3)",
        application_id, uuid.UUID(internal_user_id), "Stripe",
    )

    try:
        with TestClient(app) as client:
            response = client.post(
                "/interviews",
                json={"application_id": str(application_id), "scheduled_at_iso": "2027-03-01T10:00:00+00:00", "format": "video"},
                headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["stakes"] == "S1"
        assert body["domain"] == "career"
        assert body["operation"] == "create"
        assert body["executed"] is True
        assert body["decision"] == "approve"

        row = await pool.fetchrow("SELECT format, status FROM interviews WHERE application_id = $1", application_id)
        assert row is not None
        assert row["format"] == "video"
        assert row["status"] == "scheduled"

        job = await pool.fetchrow("SELECT job_type FROM retry_queue")
        assert job is not None
        assert job["job_type"] == "interview_prep_tasks"
    finally:
        await pool.execute("DELETE FROM retry_queue")
        await pool.execute("DELETE FROM interviews WHERE application_id = $1", application_id)
        await pool.execute("DELETE FROM applications WHERE application_id = $1", application_id)
        await pool.execute("DELETE FROM action_events WHERE user_id = $1", uuid.UUID(internal_user_id))


async def test_schedule_interview_endpoint_rejects_an_unowned_application_with_an_honest_non_execution(pool, provisioned_users):
    """A real, structural ownership check, not an HTTP-layer guess --
    the Gate genuinely approves the proposal (nothing about it looks
    malformed), and `action_executor.py`'s own real `CREATE_INTERVIEW`
    branch is what refuses to execute against an application this
    user does not own. Matches this backend's own established "fail
    safely, not loudly" contract."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    other_sub = f"test-interview-other-{uuid.uuid4()}"
    other_user_id = await get_or_create_user(pool, google_sub=other_sub, email=None)
    application_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO applications (application_id, user_id, company) VALUES ($1, $2, $3)",
        application_id, uuid.UUID(other_user_id), "Someone Else's Company",
    )

    try:
        with TestClient(app) as client:
            response = client.post("/interviews", json={"application_id": str(application_id)}, headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert body["executed"] is False
        assert await pool.fetchrow("SELECT 1 FROM interviews WHERE application_id = $1", application_id) is None
    finally:
        await pool.execute("DELETE FROM applications WHERE application_id = $1", application_id)
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(other_user_id))
        await pool.execute("DELETE FROM action_events WHERE user_id = $1", uuid.UUID(internal_user_id))


@pytest.mark.skipif(get_settings().gemini_api_key is None, reason="no real GEMINI_API_KEY configured in this environment")
async def test_quick_capture_endpoint_is_real_and_live_creates_a_real_expense_end_to_end(pool, provisioned_users):
    """The real, live, end-to-end Finance-domain proof `QUORUM_FINAL_
    COMPLETION_PLAN.md` Session 4's own verification line asks for: a
    real free-text expense, extracted by the SAME real, unified Gemini
    call the tasks test above already exercises, reviewed by the real
    Gate, and genuinely visible afterward in the real `expenses` table."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    marker = f"real-quick-capture-finance-test-{uuid.uuid4()}"

    try:
        with TestClient(app) as client:
            response = client.post(
                "/quick_capture",
                json={"text": f"spent 42 on {marker}"},
                headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["stakes"] == "S1"
        assert body["domain"] == "finance"
        # Same reasoning as the tasks test above: a fresh user, a
        # simple, unambiguous real expense -- a genuine approve is the
        # overwhelmingly likely real outcome, asserted directly.
        assert body["executed"] is True
        assert body["decision"] == "approve"
        assert body["finance_action"] == "log_expense"
        assert body["amount"] == 42.0
        assert body["title"] is None  # a real, honest tasks-only field, never populated for finance

        # `user_id` alone genuinely, uniquely identifies this row -- this
        # test's own fresh, real, provisioned user has never had any
        # other real `expenses` row written for it.
        row = await pool.fetchrow("SELECT amount FROM expenses WHERE user_id = $1", uuid.UUID(internal_user_id))
        assert row is not None
        assert float(row["amount"]) == 42.0
    finally:
        await pool.execute("DELETE FROM expenses WHERE user_id = $1", uuid.UUID(internal_user_id))
        await pool.execute("DELETE FROM action_events WHERE user_id = $1", uuid.UUID(internal_user_id))


@pytest.mark.skipif(get_settings().gemini_api_key is None or get_settings().groq_api_key is None, reason="no real GEMINI_API_KEY/GROQ_API_KEY configured in this environment")
async def test_quick_capture_endpoint_is_real_and_live_reviews_an_external_calendar_invite_via_the_real_full_stage_b_debate(pool, provisioned_users):
    """The real, live, end-to-end Calendar-domain proof `QUORUM_FINAL_
    COMPLETION_PLAN.md` Session 5's own verification asks for -- with
    Session 5's own real, disclosed correction applied: this can never
    produce a real Google Calendar booking (see `main.py`'s own route
    docstring for the full account), so this test's own real point is
    proving the full, real pipeline -- real Gemini extraction, real
    Stage A, the real FULL Stage B debate (Groq Critic AND Gemini
    Judge, genuinely different providers, zero collision) -- resolves
    correctly end to end for a genuine external-invitee request, and
    that the real S3 backstop correctly refuses to auto-execute
    regardless of the real, live Gate's own verdict."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/quick_capture",
                json={"text": "set up a call with jane@company.com next Tuesday at 10am for 30 minutes"},
                headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["domain"] == "calendar"
        assert body["stakes"] == "S3"
        assert body["calendar_action"] == "create_calendar_event_external"
        # The real, load-bearing safety proof: NEVER executed, no matter
        # what the real, live Gate decided -- confirmed directly, not
        # just documented.
        assert body["executed"] is False
    finally:
        await pool.execute("DELETE FROM action_events WHERE user_id = $1", uuid.UUID(internal_user_id))


# --- POST /quick_capture/extracted (QUORUM_FINAL_COMPLETION_PLAN.md Session 8) ---


def test_quick_capture_extracted_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.post("/quick_capture/extracted", json={"domain": "tasks", "operation": "create"})
    assert response.status_code == 401


def test_quick_capture_extracted_rejects_a_missing_domain_field_with_a_real_422():
    """`domain` is the one real, required field on `QuickCaptureExtractedRequest`
    -- everything else is nullable, mirroring `_QUICK_CAPTURE_EXTRACTION_
    SCHEMA`'s own real shape exactly."""
    with TestClient(app) as client:
        response = client.post("/quick_capture/extracted", json={"operation": "create"}, headers=_auth_header())
    assert response.status_code == 422


async def test_quick_capture_extracted_rejects_an_unsupported_domain_with_a_real_502_not_a_500(pool, provisioned_users):
    """Real, defense-in-depth: this route never trusts `body.domain` any
    more than the real Gemini extraction path already doesn't --
    `capture_action_from_extracted_args()`'s own real domain-dispatch
    `else` branch raises `QuickCaptureError` for a genuinely unsupported
    combination, mapped here to the exact same real `502` the other
    route already uses, never a raw `500`."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    with TestClient(app) as client:
        response = client.post(
            "/quick_capture/extracted",
            json={"domain": "not_a_real_domain", "operation": "create"},
            headers=headers,
        )
    assert response.status_code == 502


async def test_quick_capture_extracted_endpoint_never_calls_the_real_extraction_provider_and_still_creates_a_real_task(monkeypatch, pool, provisioned_users):
    """THE real, load-bearing proof of this whole session: a pre-
    extracted `CREATE_TASK` submission succeeds end to end even with
    `GEMINI_API_KEY` genuinely unset -- direct, live proof that this
    route really does skip the real extraction call entirely, not just
    a claim in its own docstring. `CREATE_TASK` is real `Stakes.S1`,
    so Stage B (and therefore the real Judge too) never runs either --
    this test needs no real external LLM call of any kind to pass."""
    from quorum_backend import main as main_module

    fake_settings = get_settings().model_copy(update={"gemini_api_key": None})
    monkeypatch.setattr(main_module, "get_settings", lambda: fake_settings)

    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    marker = f"real quick-capture-extracted test {uuid.uuid4()}"

    try:
        with TestClient(app) as client:
            response = client.post(
                "/quick_capture/extracted",
                json={
                    "domain": "tasks",
                    "operation": "create",
                    "title": marker,
                    "estimated_hours": 1.0,
                    "deadline_iso": None,
                },
                headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["stakes"] == "S1"
        assert body["domain"] == "tasks"
        assert body["executed"] is True
        assert body["decision"] == "approve"
        assert body["title"] == marker

        row = await pool.fetchrow(
            "SELECT title, estimated_hours FROM tasks WHERE user_id = $1 AND title = $2",
            uuid.UUID(internal_user_id), marker,
        )
        assert row is not None
        assert row["estimated_hours"] == 1.0
    finally:
        await pool.execute("DELETE FROM tasks WHERE user_id = $1", uuid.UUID(internal_user_id))
        await pool.execute("DELETE FROM action_events WHERE user_id = $1", uuid.UUID(internal_user_id))


async def test_quick_capture_extracted_endpoint_creates_a_real_expense_end_to_end_with_no_live_llm_call_needed(pool, provisioned_users):
    """`log_expense` is also real `Stakes.S1` -- the same real "no live
    LLM call needed at all" property as the tasks test above, proven
    for a second real domain."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    marker = f"real-quick-capture-extracted-finance-test-{uuid.uuid4()}"

    try:
        with TestClient(app) as client:
            response = client.post(
                "/quick_capture/extracted",
                json={"domain": "finance", "action": "log_expense", "amount": 42.0, "payee": marker, "category": "test"},
                headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["stakes"] == "S1"
        assert body["domain"] == "finance"
        assert body["executed"] is True
        assert body["decision"] == "approve"
        assert body["amount"] == 42.0

        row = await pool.fetchrow("SELECT amount FROM expenses WHERE user_id = $1 AND payee = $2", uuid.UUID(internal_user_id), marker)
        assert row is not None
        assert float(row["amount"]) == 42.0
    finally:
        await pool.execute("DELETE FROM expenses WHERE user_id = $1", uuid.UUID(internal_user_id))
        await pool.execute("DELETE FROM action_events WHERE user_id = $1", uuid.UUID(internal_user_id))


@pytest.mark.skipif(get_settings().gemini_api_key is None or get_settings().groq_api_key is None, reason="no real GEMINI_API_KEY/GROQ_API_KEY configured in this environment")
async def test_quick_capture_extracted_endpoint_reviews_a_real_external_calendar_invite_via_the_real_full_stage_b_debate_and_never_executes(pool, provisioned_users):
    """The real, live proof that a pre-extracted `Stakes.S3` submission
    through this NEW route gets the exact same real Gate treatment (the
    real Groq Critic AND the real Gemini Judge, both genuinely invoked)
    and the exact same real S3 human-approval backstop as the existing
    `/quick_capture` route's own equivalent test -- proving the safety
    properties this session's own docstrings claim are identical are
    genuinely, not just theoretically, identical."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/quick_capture/extracted",
                json={
                    "domain": "calendar",
                    "operation": "create",
                    "title": "Call with Jane",
                    "start_iso": "2027-01-01T10:00:00+00:00",
                    "end_iso": "2027-01-01T10:30:00+00:00",
                    "invitee_email": "jane@company.com",
                },
                headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["domain"] == "calendar"
        assert body["stakes"] == "S3"
        assert body["calendar_action"] == "create_calendar_event_external"
        # The identical real safety proof as the existing route's own
        # equivalent test: NEVER executed, no matter what the real,
        # live Gate decided.
        assert body["executed"] is False
    finally:
        await pool.execute("DELETE FROM action_events WHERE user_id = $1", uuid.UUID(internal_user_id))


async def test_quick_capture_logs_a_real_fallback_line_when_the_mobile_client_reports_an_on_device_attempt(monkeypatch, caplog, pool, provisioned_users):
    """Real, minimal proof of this session's own "every fallback is
    logged, not silent" requirement -- a request through the EXISTING
    `/quick_capture` route that sets `on_device_attempted=True` produces
    a real, observable log line naming the real reason, logged right
    after this real, provisioned user is resolved and before the real
    extraction call ever runs. The real extraction call itself is
    monkeypatched to a cheap stub that raises immediately -- this test's
    own point is proving the log line fires, not re-proving a live
    Gemini round trip already covered elsewhere, so it stays hermetic
    and fast rather than needing a real network call.

    RESOLVED, a real, live CI failure found the first time this test
    ever ran outside this developer's own local environment (PR #84's
    own merge-triggered `main` CI run): this test never forced a real,
    non-`None` `gemini_api_key`, implicitly relying on this developer's
    own local `.env` happening to have one configured. CI's own real
    environment has no `GEMINI_API_KEY` secret at all (confirmed
    directly from that run's own env dump) -- `settings.gemini_api_key
    is None` was genuinely `True` there, so the route's own earlier
    `503` short-circuit fired before ever reaching the monkeypatched
    extraction call, and this test asserted the wrong status code
    entirely. Fixed by explicitly forcing a real, non-`None` dummy key
    via the same `model_copy()` pattern this file's own "provider not
    configured" test already uses, rather than trusting ambient
    environment state."""
    from quorum_backend import main as main_module
    import logging as logging_module

    from quorum_backend.features.quick_capture import QuickCaptureError

    fake_settings = get_settings().model_copy(update={"gemini_api_key": "ci-only-dummy-key-never-used-for-a-real-call"})
    monkeypatch.setattr(main_module, "get_settings", lambda: fake_settings)

    async def _stub_extraction_call(_text: str):
        raise QuickCaptureError("stub extraction failure -- this test never needs a real Gemini call")

    monkeypatch.setattr(main_module, "make_gemini_quick_capture_extraction_call", lambda **_kwargs: _stub_extraction_call)

    headers, _internal_user_id = await _provisioned_auth_header(pool, provisioned_users)

    with caplog.at_level(logging_module.INFO, logger="quorum_backend"):
        with TestClient(app) as client:
            response = client.post(
                "/quick_capture",
                json={
                    "text": "finish the report",
                    "on_device_attempted": True,
                    "on_device_failure_reason": "estimated_hours missing",
                },
                headers=headers,
            )

    assert response.status_code == 502
    assert "fell back to cloud extraction" in caplog.text
    assert "estimated_hours missing" in caplog.text


# --- POST /device_token (QUORUM_FINAL_COMPLETION_PLAN.md Session 9, DEC-176) ---


def test_device_token_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.post("/device_token", json={"fcm_token": "a-real-fake-token"})
    assert response.status_code == 401


def test_device_token_rejects_a_blank_token_with_a_real_422():
    with TestClient(app) as client:
        response = client.post("/device_token", json={"fcm_token": ""}, headers=_auth_header())
    assert response.status_code == 422


async def test_device_token_registers_a_real_row_for_a_real_provisioned_user(pool, provisioned_users):
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)

    with TestClient(app) as client:
        response = client.post("/device_token", json={"fcm_token": "a-real-fake-fcm-token"}, headers=headers)

    assert response.status_code == 200
    row = await pool.fetchrow("SELECT fcm_token FROM device_tokens WHERE user_id = $1", uuid.UUID(internal_user_id))
    assert row is not None
    assert row["fcm_token"] == "a-real-fake-fcm-token"


async def test_device_token_a_second_real_registration_overwrites_the_first_never_duplicates(pool, provisioned_users):
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)

    with TestClient(app) as client:
        client.post("/device_token", json={"fcm_token": "first-real-device-token"}, headers=headers)
        response = client.post("/device_token", json={"fcm_token": "second-real-device-token"}, headers=headers)

    assert response.status_code == 200
    rows = await pool.fetch("SELECT fcm_token FROM device_tokens WHERE user_id = $1", uuid.UUID(internal_user_id))
    assert len(rows) == 1
    assert rows[0]["fcm_token"] == "second-real-device-token"


# --- GET /predictive_risk (Phase 6, DEC-149) ---


def test_predictive_risk_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.get("/predictive_risk")
    assert response.status_code == 401


async def test_predictive_risk_endpoint_is_real_and_live_not_mocked_with_a_real_valid_token(pool, provisioned_users):
    """Real, end-to-end: real-provisions a real user (DEC-110), confirms
    `GET /predictive_risk` genuinely round-trips through `fetch_risk_
    assessment()` with a real, valid access token. A freshly provisioned
    real user has no real task history, so the real, honest response
    is the no-data case -- asserted precisely, not just a 200."""
    headers, _internal_user_id = await _provisioned_auth_header(pool, provisioned_users)

    with TestClient(app) as client:
        response = client.get("/predictive_risk", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "week_start", "deadline_density", "matching_historical_weeks", "pooled_correction_rate", "is_at_risk",
    }
    assert body["matching_historical_weeks"] == 0
    assert body["pooled_correction_rate"] is None
    assert body["is_at_risk"] is False


async def test_predictive_risk_endpoint_never_counts_another_real_users_tasks(pool, provisioned_users):
    headers_a, _user_a = await _provisioned_auth_header(pool, provisioned_users)
    _headers_b, user_b = await _provisioned_auth_header(pool, provisioned_users)
    task_b = uuid.uuid4()
    upcoming = datetime.now(timezone.utc) + timedelta(weeks=1)

    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, $5, $6)",
        task_b, uuid.UUID(user_b), "User B's real, private upcoming task", 1.0, upcoming, "open",
    )

    try:
        with TestClient(app) as client:
            response = client.get("/predictive_risk", headers=headers_a)
        assert response.json()["deadline_density"] == 0  # user A never sees user B's real task
    finally:
        await pool.execute("DELETE FROM tasks WHERE task_id = $1", task_b)


def test_predictive_risk_returns_503_not_a_crash_when_the_real_pool_is_unavailable():
    with TestClient(app) as client:
        real_pool = app.state.db_pool
        app.state.db_pool = None
        try:
            response = client.get("/predictive_risk", headers=_auth_header())
            health_response = client.get("/health")
            assert response.status_code == 503
            assert health_response.status_code == 200
        finally:
            app.state.db_pool = real_pool


async def test_today_endpoint_is_real_and_live_not_mocked_with_a_real_valid_token(pool, provisioned_users):
    """Real, end-to-end: real-provisions a real user, inserts a real,
    unresolved `action_events` row and a real, unresolved `negotiations`
    row scoped to that exact user, confirms `GET /today` genuinely
    round-trips through both real tables with a real, valid access
    token, then cleans up. Real per-user scoped from this endpoint's
    first line (`DEC-119`) -- no retrofit needed, unlike `/tasks`."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    proposal_id = uuid.uuid4()
    negotiation_id = uuid.uuid4()

    await pool.execute(
        """
        INSERT INTO action_events (proposal_id, action_type, stakes, payload, trace_id, resolved_at, user_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        proposal_id,
        "send_email",
        "S3",
        json.dumps({"to": "priya@x.com"}),
        f"trace-{proposal_id}",
        None,
        uuid.UUID(internal_user_id),
    )
    await pool.execute(
        """
        INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at, resolved_at)
        VALUES ($1, $2, $3, $4, $5)
        """,
        negotiation_id,
        uuid.UUID(internal_user_id),
        ["calendar", "finance"],
        datetime.now(timezone.utc),
        None,
    )

    try:
        with TestClient(app) as client:
            response = client.get("/today", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert set(body.keys()) == {"capacity", "budget", "needs_you_now", "in_motion"}
        assert set(body["capacity"].keys()) == {"hours_remaining_today", "remaining_fraction", "source"}
        assert body["capacity"]["source"] == "live_backend"
        assert set(body["budget"].keys()) == {"amount_remaining", "remaining_fraction", "source"}
        assert body["budget"]["source"] == "live_backend"

        action_match = next(a for a in body["needs_you_now"] if a["proposal_id"] == str(proposal_id))
        assert action_match["action_type"] == "send_email"
        assert action_match["stakes"] == "S3"
        assert action_match["payload"] == {"to": "priya@x.com"}

        negotiation_match = next(n for n in body["in_motion"] if n["negotiation_id"] == str(negotiation_id))
        assert negotiation_match["conflicted_domains"] == ["calendar", "finance"]
    finally:
        await pool.execute("DELETE FROM action_events WHERE proposal_id = $1", proposal_id)
        await pool.execute("DELETE FROM negotiations WHERE negotiation_id = $1", negotiation_id)


async def test_today_endpoint_never_leaks_another_real_users_rows(pool, provisioned_users):
    """The same real, load-bearing cross-user-isolation property every
    other per-user endpoint in this backend proves, applied to both of
    `/today`'s real tables at once."""
    headers_a, user_a = await _provisioned_auth_header(pool, provisioned_users)
    _headers_b, user_b = await _provisioned_auth_header(pool, provisioned_users)
    proposal_a, proposal_b = uuid.uuid4(), uuid.uuid4()
    negotiation_a, negotiation_b = uuid.uuid4(), uuid.uuid4()

    for proposal_id, user_id in ((proposal_a, user_a), (proposal_b, user_b)):
        await pool.execute(
            """
            INSERT INTO action_events (proposal_id, action_type, stakes, payload, trace_id, resolved_at, user_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            proposal_id, "send_email", "S2", json.dumps({}), f"trace-{proposal_id}", None, uuid.UUID(user_id),
        )
    for negotiation_id, user_id in ((negotiation_a, user_a), (negotiation_b, user_b)):
        await pool.execute(
            """
            INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at, resolved_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            negotiation_id, uuid.UUID(user_id), ["tasks"], datetime.now(timezone.utc), None,
        )

    try:
        with TestClient(app) as client:
            response = client.get("/today", headers=headers_a)

        body = response.json()
        action_ids_seen = {a["proposal_id"] for a in body["needs_you_now"]}
        negotiation_ids_seen = {n["negotiation_id"] for n in body["in_motion"]}
        assert str(proposal_a) in action_ids_seen
        assert str(proposal_b) not in action_ids_seen
        assert str(negotiation_a) in negotiation_ids_seen
        assert str(negotiation_b) not in negotiation_ids_seen
    finally:
        await pool.execute("DELETE FROM action_events WHERE proposal_id = ANY($1::uuid[])", [proposal_a, proposal_b])
        await pool.execute("DELETE FROM negotiations WHERE negotiation_id = ANY($1::uuid[])", [negotiation_a, negotiation_b])


def test_today_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.get("/today")
    assert response.status_code == 401


def test_today_returns_503_not_a_crash_when_the_real_pool_is_unavailable():
    """Same real, honest failure mode as every other real per-user
    endpoint's own equivalent test -- /health stays unaffected, /today
    fails loud with a real 503 rather than a raw exception."""
    with TestClient(app) as client:
        real_pool = app.state.db_pool
        app.state.db_pool = None
        try:
            today_response = client.get("/today", headers=_auth_header())
            health_response = client.get("/health")
            assert today_response.status_code == 503
            assert health_response.status_code == 200
        finally:
            app.state.db_pool = real_pool


async def test_today_summary_endpoint_is_real_and_live_not_mocked_with_a_real_valid_token(pool, provisioned_users):
    """Real, end-to-end: real-provisions a real user, inserts one real
    row in each of the four real source tables, confirms `GET /today/
    summary` genuinely round-trips through `fetch_week_summary()`."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    task_id = uuid.uuid4()
    expense_id = uuid.uuid4()
    application_id = uuid.uuid4()
    try:
        await pool.execute(
            "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, now() + interval '2 days', 'open')",
            task_id, uuid.UUID(internal_user_id), "A real end-to-end due-soon task", 1.0,
        )
        await pool.execute(
            "INSERT INTO expenses (expense_id, user_id, payee, amount, occurred_at, source) VALUES ($1, $2, $3, $4, now(), 'manual')",
            expense_id, uuid.UUID(internal_user_id), "A real end-to-end payee", 250.0,
        )
        await pool.execute(
            "INSERT INTO applications (application_id, user_id, company, role, status) VALUES ($1, $2, $3, $4, 'applied')",
            application_id, uuid.UUID(internal_user_id), "A real end-to-end company", "Engineer",
        )

        with TestClient(app) as client:
            response = client.get("/today/summary", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert set(body.keys()) == {
            "tasks_due_this_week", "month_to_date_spend", "monthly_budget_limit",
            "applications_in_progress", "waiting_on_count",
        }
        assert body["tasks_due_this_week"] == 1
        assert body["month_to_date_spend"] == 250.0
        assert body["monthly_budget_limit"] > 0
        assert body["applications_in_progress"] == 1
        assert body["waiting_on_count"] == 0
    finally:
        await pool.execute("DELETE FROM tasks WHERE task_id = $1", task_id)
        await pool.execute("DELETE FROM expenses WHERE expense_id = $1", expense_id)
        await pool.execute("DELETE FROM applications WHERE application_id = $1", application_id)


def test_today_summary_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.get("/today/summary")
    assert response.status_code == 401


def test_today_summary_returns_503_not_a_crash_when_the_real_pool_is_unavailable():
    with TestClient(app) as client:
        real_pool = app.state.db_pool
        app.state.db_pool = None
        try:
            response = client.get("/today/summary", headers=_auth_header())
            assert response.status_code == 503
        finally:
            app.state.db_pool = real_pool


async def test_negotiation_detail_endpoint_is_real_and_live_not_mocked_with_a_real_valid_token(pool, provisioned_users):
    """Real, end-to-end: real-provisions a real user, inserts a real
    negotiation row with real, persisted positions/options, confirms
    `GET /negotiations/{id}` genuinely round-trips through the real
    database with a real, valid access token."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    negotiation_id = uuid.uuid4()

    await pool.execute(
        "INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at, positions, options) "
        "VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb)",
        negotiation_id,
        uuid.UUID(internal_user_id),
        ["finance", "tasks"],
        datetime.now(timezone.utc),
        json.dumps([{"domain": "finance", "concern": "c", "severity_claim": "s", "resource_claims": [], "proposed_resolution": "r", "evidence": []}]),
        json.dumps([{"option_id": "option_a", "description": "d", "source_domains": ["finance"], "impact": []}]),
    )

    try:
        with TestClient(app) as client:
            response = client.get(f"/negotiations/{negotiation_id}", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert set(body.keys()) == {"positions", "options", "resolved_at", "chosen_option_id"}
        assert body["positions"][0]["domain"] == "finance"
        assert body["options"][0]["option_id"] == "option_a"
        assert body["resolved_at"] is None  # genuinely still open -- never rows this test didn't seed as resolved
        assert body["chosen_option_id"] is None
    finally:
        await pool.execute("DELETE FROM negotiations WHERE negotiation_id = $1", negotiation_id)


async def test_negotiation_detail_endpoint_reports_a_real_already_chosen_negotiation_honestly(pool, provisioned_users):
    """RESOLVED, a real, disclosed gap found on-device (Session 2,
    `QUORUM_FINAL_COMPLETION_PLAN.md`, `DEC-168`): a real user re-
    opening an already-decided negotiation previously received the
    identical response shape as a genuinely open one -- discoverable as
    already-resolved only via a real `409` from `POST .../choose` AFTER
    tapping "Choose this option" again. This test proves the real,
    live route fix end to end, not just the underlying fetch function's
    own unit test."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    negotiation_id = uuid.uuid4()

    await pool.execute(
        "INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at, positions, options, resolved_at, chosen_option_id) "
        "VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, now(), $7)",
        negotiation_id,
        uuid.UUID(internal_user_id),
        ["finance", "tasks"],
        datetime.now(timezone.utc),
        json.dumps([{"domain": "finance", "concern": "c", "severity_claim": "s", "resource_claims": [], "proposed_resolution": "r", "evidence": []}]),
        json.dumps([{"option_id": "option_a", "description": "d", "source_domains": ["finance"], "impact": []}]),
        "option_a",
    )

    try:
        with TestClient(app) as client:
            response = client.get(f"/negotiations/{negotiation_id}", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert body["resolved_at"] is not None
        assert body["chosen_option_id"] == "option_a"
    finally:
        await pool.execute("DELETE FROM negotiations WHERE negotiation_id = $1", negotiation_id)


async def test_negotiation_detail_endpoint_never_leaks_another_real_users_negotiation(pool, provisioned_users):
    headers_a, _user_a = await _provisioned_auth_header(pool, provisioned_users)
    _headers_b, user_b = await _provisioned_auth_header(pool, provisioned_users)
    negotiation_id = uuid.uuid4()

    await pool.execute(
        "INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at) VALUES ($1, $2, $3, $4)",
        negotiation_id, uuid.UUID(user_b), ["finance"], datetime.now(timezone.utc),
    )

    try:
        with TestClient(app) as client:
            response = client.get(f"/negotiations/{negotiation_id}", headers=headers_a)
        assert response.status_code == 404
    finally:
        await pool.execute("DELETE FROM negotiations WHERE negotiation_id = $1", negotiation_id)


def test_negotiation_detail_endpoint_a_real_syntactically_invalid_id_is_a_real_404_not_a_500():
    with TestClient(app) as client:
        response = client.get("/negotiations/not-a-real-uuid", headers=_auth_header())
    assert response.status_code == 404


def test_negotiation_detail_endpoint_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.get(f"/negotiations/{uuid.uuid4()}")
    assert response.status_code == 401


def test_negotiation_detail_endpoint_returns_503_not_a_crash_when_the_real_pool_is_unavailable():
    with TestClient(app) as client:
        real_pool = app.state.db_pool
        app.state.db_pool = None
        try:
            response = client.get(f"/negotiations/{uuid.uuid4()}", headers=_auth_header())
            health_response = client.get("/health")
            assert response.status_code == 503
            assert health_response.status_code == 200
        finally:
            app.state.db_pool = real_pool


async def test_gate_reveal_endpoint_is_real_and_live_not_mocked_with_a_real_valid_token(pool, provisioned_users):
    """Real, end-to-end: real-provisions a real user (DEC-110), inserts
    a real `action_events` row with real findings/objections scoped to
    that exact user, confirms `GET /gate_reveal/{proposal_id}` genuinely
    round-trips through `fetch_gate_reveal()` with a real, valid access
    token, then cleans up."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    proposal_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at, findings, objections) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9, $10::jsonb, $11::jsonb)",
        proposal_id, "create_task", "S1", '{"title": "A real end-to-end task"}', "approve", "approved_unchanged",
        f"trace-{proposal_id}", uuid.UUID(internal_user_id), datetime.now(timezone.utc),
        '[{"validator": "ProvenanceCheck", "claim": "A real claim", "evidence_state": "verified_true", "source_ref": null, "confidence": 1.0}]',
        '[]',
    )

    try:
        with TestClient(app) as client:
            response = client.get(f"/gate_reveal/{proposal_id}", headers=headers)

        assert response.status_code == 200
        body = response.json()
        # REAL, DISCLOSED EXTENSION (the redesign's own real Approve/
        # Reject work): `action_type`/`gate_decision`/`resolved_at` are
        # new, real, needed fields -- the mobile client uses them to
        # decide whether to show real Approve/Reject controls at all.
        # `payload` joined them (CRITICAL-tier review, HIGH-3): the real
        # payload a human "Approve" tap would execute, surfaced so a
        # user can actually see what they're approving before they do.
        assert set(body.keys()) == {"stakes", "findings", "objections", "action_type", "gate_decision", "resolved_at", "payload"}
        assert body["stakes"] == "S1"
        assert len(body["findings"]) == 1
        assert body["findings"][0]["validator"] == "ProvenanceCheck"
        assert body["objections"] == []
        assert body["action_type"] == "create_task"
        assert body["gate_decision"] == "approve"
        assert body["resolved_at"] is not None
        assert body["payload"] == {"title": "A real end-to-end task"}
    finally:
        await pool.execute("DELETE FROM action_events WHERE proposal_id = $1", proposal_id)


async def test_gate_reveal_endpoint_returns_404_for_a_real_proposal_belonging_to_another_real_user(pool, provisioned_users):
    headers_a, _user_a = await _provisioned_auth_header(pool, provisioned_users)
    _headers_b, user_b = await _provisioned_auth_header(pool, provisioned_users)
    proposal_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)",
        proposal_id, "create_task", "S1", '{"title": "User B real task"}', "approve", "approved_unchanged",
        f"trace-{proposal_id}", uuid.UUID(user_b), datetime.now(timezone.utc),
    )

    try:
        with TestClient(app) as client:
            response = client.get(f"/gate_reveal/{proposal_id}", headers=headers_a)
        assert response.status_code == 404
    finally:
        await pool.execute("DELETE FROM action_events WHERE proposal_id = $1", proposal_id)


def test_gate_reveal_endpoint_a_real_syntactically_invalid_id_is_a_real_404_not_a_500():
    with TestClient(app) as client:
        response = client.get("/gate_reveal/not-a-real-uuid", headers=_auth_header())
    assert response.status_code == 404


def test_gate_reveal_endpoint_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.get(f"/gate_reveal/{uuid.uuid4()}")
    assert response.status_code == 401


def test_gate_reveal_endpoint_returns_503_not_a_crash_when_the_real_pool_is_unavailable():
    with TestClient(app) as client:
        real_pool = app.state.db_pool
        app.state.db_pool = None
        try:
            response = client.get(f"/gate_reveal/{uuid.uuid4()}", headers=_auth_header())
            health_response = client.get("/health")
            assert response.status_code == 503
            assert health_response.status_code == 200
        finally:
            app.state.db_pool = real_pool


async def test_approve_action_endpoint_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.post(f"/actions/{uuid.uuid4()}/approve")
    assert response.status_code == 401


def test_approve_action_endpoint_a_real_syntactically_invalid_id_is_a_real_404_not_a_500():
    with TestClient(app) as client:
        response = client.post("/actions/not-a-real-uuid/approve", headers=_auth_header())
    assert response.status_code == 404


async def test_approve_action_endpoint_returns_404_for_a_real_nonexistent_proposal(pool, provisioned_users):
    headers, _user_id = await _provisioned_auth_header(pool, provisioned_users)
    with TestClient(app) as client:
        response = client.post(f"/actions/{uuid.uuid4()}/approve", headers=headers)
    assert response.status_code == 404


async def test_approve_action_endpoint_returns_409_when_the_gate_never_approved_it(pool, provisioned_users):
    """Real, end-to-end: a `revise` verdict genuinely has nothing for a
    human approval to execute -- confirmed through the real route, not
    just the lower-level `action_approval.py` function."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    proposal_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)",
        proposal_id, "send_email", "S3", '{"to": "test@example.com", "body": "hi"}', "revise", "caught_by_gate",
        f"trace-{proposal_id}", uuid.UUID(internal_user_id), datetime.now(timezone.utc),
    )
    try:
        with TestClient(app) as client:
            response = client.post(f"/actions/{proposal_id}/approve", headers=headers)
        assert response.status_code == 409
    finally:
        await pool.execute("DELETE FROM action_events WHERE proposal_id = $1", proposal_id)


async def test_approve_action_endpoint_returns_409_for_an_action_type_with_no_execution_path(pool, provisioned_users):
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    proposal_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)",
        proposal_id, "create_calendar_event_local", "S2",
        '{"start": "2026-10-01T10:00:00Z", "end": "2026-10-01T11:00:00Z", "title": "A real meeting"}',
        "approve", None, f"trace-{proposal_id}", uuid.UUID(internal_user_id), None,
    )
    try:
        with TestClient(app) as client:
            response = client.post(f"/actions/{proposal_id}/approve", headers=headers)
        assert response.status_code == 409
    finally:
        await pool.execute("DELETE FROM action_events WHERE proposal_id = $1", proposal_id)


async def test_approve_action_endpoint_returns_502_with_an_honest_detail_when_execution_fails(pool, provisioned_users):
    """This real, freshly-provisioned test user has no real Google
    account connected -- a real, honest execution failure, surfaced as
    a real `502` with the specific real reason, never a fabricated
    success."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    proposal_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)",
        proposal_id, "send_email", "S3", '{"to": "test@example.com", "body": "hi"}', "approve", None,
        f"trace-{proposal_id}", uuid.UUID(internal_user_id), None,
    )
    try:
        with TestClient(app) as client:
            response = client.post(f"/actions/{proposal_id}/approve", headers=headers)
        assert response.status_code == 502
        assert "google" in response.json()["detail"].lower()
        row = await pool.fetchrow("SELECT resolved_at FROM action_events WHERE proposal_id = $1", proposal_id)
        assert row["resolved_at"] is None
    finally:
        await pool.execute("DELETE FROM action_events WHERE proposal_id = $1", proposal_id)


async def test_reject_action_endpoint_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.post(f"/actions/{uuid.uuid4()}/reject")
    assert response.status_code == 401


async def test_reject_action_endpoint_returns_404_for_a_real_nonexistent_proposal(pool, provisioned_users):
    headers, _user_id = await _provisioned_auth_header(pool, provisioned_users)
    with TestClient(app) as client:
        response = client.post(f"/actions/{uuid.uuid4()}/reject", headers=headers)
    assert response.status_code == 404


async def test_reject_action_endpoint_resolves_a_real_pending_row_end_to_end(pool, provisioned_users):
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    proposal_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)",
        proposal_id, "send_email", "S3", '{"to": "test@example.com", "body": "hi"}', "approve", None,
        f"trace-{proposal_id}", uuid.UUID(internal_user_id), None,
    )
    try:
        with TestClient(app) as client:
            response = client.post(f"/actions/{proposal_id}/reject", headers=headers)
        assert response.status_code == 200
        assert response.json() == {"status": "rejected"}
        row = await pool.fetchrow("SELECT outcome, resolved_at FROM action_events WHERE proposal_id = $1", proposal_id)
        assert row["outcome"] == "rejected_by_user"
        assert row["resolved_at"] is not None
    finally:
        await pool.execute("DELETE FROM action_events WHERE proposal_id = $1", proposal_id)


async def test_reject_action_endpoint_returns_409_when_already_resolved(pool, provisioned_users):
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    proposal_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)",
        proposal_id, "create_task", "S1", '{"title": "A real task"}', "approve", "approved_unchanged",
        f"trace-{proposal_id}", uuid.UUID(internal_user_id), datetime.now(timezone.utc),
    )
    try:
        with TestClient(app) as client:
            response = client.post(f"/actions/{proposal_id}/reject", headers=headers)
        assert response.status_code == 409
    finally:
        await pool.execute("DELETE FROM action_events WHERE proposal_id = $1", proposal_id)


async def _seed_real_task(pool, *, user_id: str, status: str = "open") -> uuid.UUID:
    task_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) "
        "VALUES ($1, $2, $3, $4, $5, $6)",
        task_id, uuid.UUID(user_id), "A real end-to-end task", 1.0, None, status,
    )
    return task_id


def test_complete_task_endpoint_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.post(f"/tasks/{uuid.uuid4()}/complete")
    assert response.status_code == 401


def test_complete_task_endpoint_a_real_syntactically_invalid_id_is_a_real_404_not_a_500():
    with TestClient(app) as client:
        response = client.post("/tasks/not-a-real-uuid/complete", headers=_auth_header())
    assert response.status_code == 404


async def test_complete_task_endpoint_returns_404_for_a_real_nonexistent_task(pool, provisioned_users):
    headers, _internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    with TestClient(app) as client:
        response = client.post(f"/tasks/{uuid.uuid4()}/complete", headers=headers)
    assert response.status_code == 404


async def test_complete_task_endpoint_marks_a_real_open_task_done_end_to_end(pool, provisioned_users):
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    task_id = await _seed_real_task(pool, user_id=internal_user_id)
    try:
        with TestClient(app) as client:
            response = client.post(f"/tasks/{task_id}/complete", headers=headers)
        assert response.status_code == 200
        assert response.json() == {"status": "done"}
        row = await pool.fetchrow("SELECT status FROM tasks WHERE task_id = $1", task_id)
        assert row["status"] == "done"
    finally:
        await pool.execute("DELETE FROM tasks WHERE task_id = $1", task_id)


async def test_complete_task_endpoint_returns_409_when_already_done(pool, provisioned_users):
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    task_id = await _seed_real_task(pool, user_id=internal_user_id, status="done")
    try:
        with TestClient(app) as client:
            response = client.post(f"/tasks/{task_id}/complete", headers=headers)
        assert response.status_code == 409
    finally:
        await pool.execute("DELETE FROM tasks WHERE task_id = $1", task_id)


async def test_complete_task_endpoint_never_lets_one_real_user_complete_anothers_task(pool, provisioned_users):
    headers_a, _user_a = await _provisioned_auth_header(pool, provisioned_users)
    _headers_b, user_b = await _provisioned_auth_header(pool, provisioned_users)
    task_id = await _seed_real_task(pool, user_id=user_b)
    try:
        with TestClient(app) as client:
            response = client.post(f"/tasks/{task_id}/complete", headers=headers_a)
        assert response.status_code == 404
        row = await pool.fetchrow("SELECT status FROM tasks WHERE task_id = $1", task_id)
        assert row["status"] == "open"
    finally:
        await pool.execute("DELETE FROM tasks WHERE task_id = $1", task_id)


def test_cancel_task_endpoint_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.post(f"/tasks/{uuid.uuid4()}/cancel")
    assert response.status_code == 401


async def test_cancel_task_endpoint_returns_404_for_a_real_nonexistent_task(pool, provisioned_users):
    headers, _internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    with TestClient(app) as client:
        response = client.post(f"/tasks/{uuid.uuid4()}/cancel", headers=headers)
    assert response.status_code == 404


async def test_cancel_task_endpoint_marks_a_real_open_task_cancelled_end_to_end(pool, provisioned_users):
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    task_id = await _seed_real_task(pool, user_id=internal_user_id)
    try:
        with TestClient(app) as client:
            response = client.post(f"/tasks/{task_id}/cancel", headers=headers)
        assert response.status_code == 200
        assert response.json() == {"status": "cancelled"}
        row = await pool.fetchrow("SELECT status FROM tasks WHERE task_id = $1", task_id)
        assert row["status"] == "cancelled"
    finally:
        await pool.execute("DELETE FROM tasks WHERE task_id = $1", task_id)


async def test_cancel_task_endpoint_returns_409_when_already_cancelled(pool, provisioned_users):
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    task_id = await _seed_real_task(pool, user_id=internal_user_id, status="cancelled")
    try:
        with TestClient(app) as client:
            response = client.post(f"/tasks/{task_id}/cancel", headers=headers)
        assert response.status_code == 409
    finally:
        await pool.execute("DELETE FROM tasks WHERE task_id = $1", task_id)


_CHOOSE_TEST_OPTIONS = [
    {"option_id": "option_a", "description": "halt spending", "source_domains": ["finance"]},
    {"option_id": "do_nothing", "description": "do nothing", "source_domains": []},
]


async def test_choose_negotiation_option_endpoint_is_real_and_live_202_and_enqueues_a_real_job(pool, provisioned_users):
    """Real, end-to-end: real-provisions a real user, inserts a real
    negotiation with real, persisted options, confirms `POST /negotiations/
    {id}/choose` genuinely resolves it and enqueues a real `retry_queue`
    row, with a real, valid access token."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    negotiation_id = uuid.uuid4()

    await pool.execute(
        "INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at, options) VALUES ($1, $2, $3, $4, $5::jsonb)",
        negotiation_id, uuid.UUID(internal_user_id), ["finance"], datetime.now(timezone.utc), json.dumps(_CHOOSE_TEST_OPTIONS),
    )

    try:
        with TestClient(app) as client:
            response = client.post(f"/negotiations/{negotiation_id}/choose", json={"chosen_option": "option_a"}, headers=headers)

        assert response.status_code == 202
        row = await pool.fetchrow("SELECT resolved_at, chosen_option_id FROM negotiations WHERE negotiation_id = $1", negotiation_id)
        assert row["resolved_at"] is not None
        assert row["chosen_option_id"] == "option_a"
        job = await pool.fetchrow("SELECT job_type FROM retry_queue WHERE payload->>'negotiation_id' = $1", str(negotiation_id))
        assert job is not None
        assert job["job_type"] == "negotiation_downstream_action"
    finally:
        await pool.execute("DELETE FROM retry_queue WHERE payload->>'negotiation_id' = $1", str(negotiation_id))
        await pool.execute("DELETE FROM negotiations WHERE negotiation_id = $1", negotiation_id)


async def test_choose_negotiation_option_endpoint_rejects_an_ungrounded_option_with_a_real_400(pool, provisioned_users):
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    negotiation_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at, options) VALUES ($1, $2, $3, $4, $5::jsonb)",
        negotiation_id, uuid.UUID(internal_user_id), ["finance"], datetime.now(timezone.utc), json.dumps(_CHOOSE_TEST_OPTIONS),
    )
    try:
        with TestClient(app) as client:
            response = client.post(f"/negotiations/{negotiation_id}/choose", json={"chosen_option": "not_a_real_option"}, headers=headers)
        assert response.status_code == 400
    finally:
        await pool.execute("DELETE FROM negotiations WHERE negotiation_id = $1", negotiation_id)


async def test_choose_negotiation_option_endpoint_rejects_a_second_real_choice_with_a_real_409(pool, provisioned_users):
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    negotiation_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at, options) VALUES ($1, $2, $3, $4, $5::jsonb)",
        negotiation_id, uuid.UUID(internal_user_id), ["finance"], datetime.now(timezone.utc), json.dumps(_CHOOSE_TEST_OPTIONS),
    )
    try:
        with TestClient(app) as client:
            first = client.post(f"/negotiations/{negotiation_id}/choose", json={"chosen_option": "option_a"}, headers=headers)
            second = client.post(f"/negotiations/{negotiation_id}/choose", json={"chosen_option": "do_nothing"}, headers=headers)
        assert first.status_code == 202
        assert second.status_code == 409
    finally:
        await pool.execute("DELETE FROM retry_queue WHERE payload->>'negotiation_id' = $1", str(negotiation_id))
        await pool.execute("DELETE FROM negotiations WHERE negotiation_id = $1", negotiation_id)


async def test_choose_negotiation_option_endpoint_never_leaks_another_real_users_negotiation(pool, provisioned_users):
    headers_a, _user_a = await _provisioned_auth_header(pool, provisioned_users)
    _headers_b, user_b = await _provisioned_auth_header(pool, provisioned_users)
    negotiation_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at, options) VALUES ($1, $2, $3, $4, $5::jsonb)",
        negotiation_id, uuid.UUID(user_b), ["finance"], datetime.now(timezone.utc), json.dumps(_CHOOSE_TEST_OPTIONS),
    )
    try:
        with TestClient(app) as client:
            response = client.post(f"/negotiations/{negotiation_id}/choose", json={"chosen_option": "option_a"}, headers=headers_a)
        assert response.status_code == 404
    finally:
        await pool.execute("DELETE FROM negotiations WHERE negotiation_id = $1", negotiation_id)


def test_choose_negotiation_option_endpoint_a_real_syntactically_invalid_id_is_a_real_404_not_a_500():
    with TestClient(app) as client:
        response = client.post("/negotiations/not-a-real-uuid/choose", json={"chosen_option": "option_a"}, headers=_auth_header())
    assert response.status_code == 404


def test_choose_negotiation_option_endpoint_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.post(f"/negotiations/{uuid.uuid4()}/choose", json={"chosen_option": "option_a"})
    assert response.status_code == 401


def test_choose_negotiation_option_endpoint_returns_503_not_a_crash_when_the_real_pool_is_unavailable():
    with TestClient(app) as client:
        real_pool = app.state.db_pool
        app.state.db_pool = None
        try:
            response = client.post(f"/negotiations/{uuid.uuid4()}/choose", json={"chosen_option": "option_a"}, headers=_auth_header())
            health_response = client.get("/health")
            assert response.status_code == 503
            assert health_response.status_code == 200
        finally:
            app.state.db_pool = real_pool


@pytest.mark.skipif(get_settings().gemini_api_key is None, reason="no real GEMINI_API_KEY configured in this environment")
async def test_search_endpoint_is_real_and_live_not_mocked_with_a_real_valid_token(pool, provisioned_users):
    """Real, end-to-end: real-provisions a real user, inserts a real
    task, confirms `GET /search?q=...` genuinely round-trips through a
    real Gemini embedding call and a real pgvector similarity query
    with a real, valid access token, then cleans up."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    task_id = uuid.uuid4()

    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours) VALUES ($1, $2, $3, $4)",
        task_id, uuid.UUID(internal_user_id), "A real, distinctive end-to-end search test task", 1.0,
    )

    try:
        with TestClient(app) as client:
            response = client.get("/search", params={"q": "end-to-end search test"}, headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        match = next(item for item in body if item["item_id"] == str(task_id))
        assert match["item_type"] == "task"
        assert match["text"] == "A real, distinctive end-to-end search test task"
        assert set(match.keys()) == {"item_id", "item_type", "text", "timestamp"}
    finally:
        await pool.execute("DELETE FROM tasks WHERE task_id = $1", task_id)
        await pool.execute("DELETE FROM note_embeddings WHERE user_id = $1", uuid.UUID(internal_user_id))


@pytest.mark.skipif(get_settings().gemini_api_key is None, reason="no real GEMINI_API_KEY configured in this environment")
async def test_search_endpoint_never_leaks_another_real_users_rows(pool, provisioned_users):
    headers_a, user_a = await _provisioned_auth_header(pool, provisioned_users)
    _headers_b, user_b = await _provisioned_auth_header(pool, provisioned_users)
    task_a, task_b = uuid.uuid4(), uuid.uuid4()

    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours) VALUES ($1, $2, $3, $4)",
        task_a, uuid.UUID(user_a), "A real cross-user isolation search test task", 1.0,
    )
    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours) VALUES ($1, $2, $3, $4)",
        task_b, uuid.UUID(user_b), "A real cross-user isolation search test task", 1.0,
    )

    try:
        with TestClient(app) as client:
            response = client.get("/search", params={"q": "cross-user isolation search test"}, headers=headers_a)

        body = response.json()
        returned_ids = {item["item_id"] for item in body}
        assert str(task_a) in returned_ids
        assert str(task_b) not in returned_ids
    finally:
        await pool.execute("DELETE FROM tasks WHERE task_id = ANY($1::uuid[])", [task_a, task_b])
        await pool.execute("DELETE FROM note_embeddings WHERE user_id = ANY($1::uuid[])", [uuid.UUID(user_a), uuid.UUID(user_b)])


def test_search_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.get("/search", params={"q": "anything"})
    assert response.status_code == 401


def test_search_requires_a_real_nonempty_query_missing_q_is_422():
    with TestClient(app) as client:
        response = client.get("/search", headers=_auth_header())
    assert response.status_code == 422


def test_search_returns_503_not_a_crash_when_the_real_pool_is_unavailable():
    with TestClient(app) as client:
        real_pool = app.state.db_pool
        app.state.db_pool = None
        try:
            search_response = client.get("/search", params={"q": "anything"}, headers=_auth_header())
            health_response = client.get("/health")
            assert search_response.status_code == 503
            assert health_response.status_code == 200
        finally:
            app.state.db_pool = real_pool


async def test_search_502_body_never_leaks_the_real_api_key_or_upstream_internals(pool, provisioned_users, monkeypatch):
    """A real, permanent security regression test, added because
    `DEC-120`'s CRITICAL-tier review specifically probed this path.

    The concern was concrete, not theoretical: an earlier version of
    the `/search` route interpolated `EmbeddingError`'s own message --
    which then carried Gemini's raw `response.text` -- straight into
    the 502 response body. The key itself was never actually in there
    (the review confirmed that live against real Gemini error bodies),
    but the shape of that code was one refactor away from leaking, and
    it echoed the upstream's internals to any authenticated caller for
    no good reason. This test pins the fixed behavior down: whatever
    goes wrong upstream, the caller sees a generic message."""
    from quorum_backend import main as main_module

    headers, _internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    sentinel_key = "SENTINEL-FAKE-KEY-abc123-must-never-appear-in-any-response"

    async def _exploding_search(*args, **kwargs):
        from quorum_backend.core.embeddings import EmbeddingError

        # Deliberately stuffs the key into the error, the worst case.
        raise EmbeddingError(f"upstream blew up, url=https://x/?key={sentinel_key}")

    fake_settings = get_settings().model_copy(update={"gemini_api_key": sentinel_key})
    monkeypatch.setattr(main_module, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(main_module, "run_search", _exploding_search)

    with TestClient(app) as client:
        response = client.get("/search", params={"q": "anything"}, headers=headers)

    assert response.status_code == 502
    assert sentinel_key not in response.text
    assert "url=" not in response.text


def test_search_returns_503_when_the_embedding_provider_is_not_configured(monkeypatch):
    """A fresh clone/CI environment with no real GEMINI_API_KEY must
    fail loud and honest, never crash with a raw exception reaching the
    embedding call with `api_key=None`.

    A real, disclosed test-authoring gotcha, found running this test
    for real rather than assumed to work, twice over: (1) `GEMINI_API_
    KEY` lives in `backend/.env` as a *file* entry, not an exported OS
    environment variable in this shell -- `monkeypatch.delenv` only
    touches `os.environ` and had no effect at all, since pydantic-
    settings' `env_file=".env"` reads the file directly; (2) a
    hand-rolled fake settings object with only `gemini_api_key`/
    `jwt_signing_key` broke the app's own real startup lifespan (`main.
    py`'s `_lifespan` also calls `get_settings()`, and needs the real
    `is_using_insecure_default_jwt_signing_key` property). Fixed with
    `model_copy()` on the real settings instead -- every real field and
    computed property stays intact except the one being overridden."""
    from quorum_backend import main as main_module

    fake_settings = get_settings().model_copy(update={"gemini_api_key": None})
    monkeypatch.setattr(main_module, "get_settings", lambda: fake_settings)
    with TestClient(app) as client:
        response = client.get("/search", params={"q": "anything"}, headers=_auth_header())
    assert response.status_code == 503


def test_career_pipeline_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.get("/career_pipeline")
    assert response.status_code == 401


async def test_career_pipeline_endpoint_is_real_and_live_not_mocked_with_a_real_valid_token(pool, provisioned_users):
    """Real, end-to-end: real-provisions a real user (DEC-110), inserts
    a real row scoped to that exact user into the real, live
    `applications` table, confirms `GET /career_pipeline` genuinely
    round-trips through it with a real, valid access token for that
    same real identity, then cleans up. Includes a genuinely
    open-vocabulary status value -- proving this route never validates
    or rejects it, the deliberate opposite of `/tasks`'s closed-set
    contract."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    application_id = uuid.uuid4()
    await pool.execute(
        """
        INSERT INTO applications (application_id, user_id, company, role, status, deadline)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        application_id,
        uuid.UUID(internal_user_id),
        "A real end-to-end test company",
        "Backend Engineer",
        "a_genuinely_novel_open_status",
        None,
    )

    try:
        with TestClient(app) as client:
            response = client.get("/career_pipeline", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)

        match = next(a for a in body if a["application_id"] == str(application_id))
        assert set(match.keys()) == {"application_id", "company", "role", "status", "deadline"}
        assert match["company"] == "A real end-to-end test company"
        assert match["role"] == "Backend Engineer"
        assert match["status"] == "a_genuinely_novel_open_status"
        assert match["deadline"] is None
    finally:
        await pool.execute("DELETE FROM applications WHERE application_id = $1", application_id)


async def test_career_pipeline_endpoint_never_leaks_another_real_users_rows(pool, provisioned_users):
    """The real, load-bearing correctness property DEC-110 exists to
    guarantee, proven here for the genuinely open-vocabulary status
    field too: two distinct real users, two distinct real applications
    -- a request as user A must see only user A's application."""
    headers_a, user_a = await _provisioned_auth_header(pool, provisioned_users)
    _headers_b, user_b = await _provisioned_auth_header(pool, provisioned_users)
    app_a, app_b = uuid.uuid4(), uuid.uuid4()

    await pool.execute(
        "INSERT INTO applications (application_id, user_id, company, role, status, deadline) VALUES ($1, $2, $3, $4, $5, $6)",
        app_a,
        uuid.UUID(user_a),
        "User A's real, private company",
        None,
        "applied",
        None,
    )
    await pool.execute(
        "INSERT INTO applications (application_id, user_id, company, role, status, deadline) VALUES ($1, $2, $3, $4, $5, $6)",
        app_b,
        uuid.UUID(user_b),
        "User B's real, private company",
        None,
        "applied",
        None,
    )

    try:
        with TestClient(app) as client:
            response = client.get("/career_pipeline", headers=headers_a)

        body = response.json()
        ids_seen = {a["application_id"] for a in body}
        assert str(app_a) in ids_seen
        assert str(app_b) not in ids_seen
    finally:
        await pool.execute("DELETE FROM applications WHERE application_id = ANY($1::uuid[])", [app_a, app_b])


def test_career_pipeline_returns_503_not_a_crash_when_the_real_pool_is_unavailable():
    with TestClient(app) as client:
        real_pool = app.state.db_pool
        app.state.db_pool = None
        try:
            career_response = client.get("/career_pipeline", headers=_auth_header())
            health_response = client.get("/health")
            assert career_response.status_code == 503
            assert health_response.status_code == 200
        finally:
            app.state.db_pool = real_pool


def test_waiting_on_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.get("/waiting_on")
    assert response.status_code == 401


async def test_waiting_on_endpoint_is_real_and_live_not_mocked_with_a_real_valid_token(pool, provisioned_users):
    """Real, end-to-end: real-provisions a real user (DEC-110), inserts
    a real, genuinely stale row directly into `sent_messages` (Phase 4)
    scoped to that exact user, confirms `GET /waiting_on` genuinely
    round-trips through the real `fetch_stale_waiting_on()` query with
    a real, valid access token for that same real identity, then cleans
    up. A second, genuinely fresh row proves the real, server-side
    staleness filter (`find_stale_waiting_on()`) is actually applied,
    not just plumbing that returns everything unfiltered."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    stale_id, fresh_id = "stale-msg", "fresh-msg"
    now = datetime.now(timezone.utc)
    await pool.execute(
        "INSERT INTO sent_messages (user_id, message_id, thread_id, recipient, subject, sent_at) VALUES ($1, $2, $3, $4, $5, $6)",
        uuid.UUID(internal_user_id), stale_id, "thread-stale", "a@x.com", "A real end-to-end stale message", now - timedelta(days=10),
    )
    await pool.execute(
        "INSERT INTO sent_messages (user_id, message_id, thread_id, recipient, subject, sent_at) VALUES ($1, $2, $3, $4, $5, $6)",
        uuid.UUID(internal_user_id), fresh_id, "thread-fresh", "b@x.com", "A real end-to-end fresh message", now - timedelta(hours=1),
    )

    try:
        with TestClient(app) as client:
            response = client.get("/waiting_on", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        subjects_seen = {m["subject"] for m in body}
        assert "A real end-to-end stale message" in subjects_seen
        assert "A real end-to-end fresh message" not in subjects_seen  # too fresh to be genuinely "waiting on"
        match = next(m for m in body if m["subject"] == "A real end-to-end stale message")
        assert set(match.keys()) == {"recipient", "subject", "sent_at"}
        assert match["recipient"] == "a@x.com"
    finally:
        await pool.execute("DELETE FROM sent_messages WHERE user_id = $1", uuid.UUID(internal_user_id))


async def test_waiting_on_endpoint_never_leaks_another_real_users_rows(pool, provisioned_users):
    """The real, load-bearing correctness property DEC-110 exists to
    guarantee, proven here for `sent_messages` too: two distinct real
    users, two distinct real stale messages -- a request as user A must
    see only user A's message."""
    headers_a, user_a = await _provisioned_auth_header(pool, provisioned_users)
    _headers_b, user_b = await _provisioned_auth_header(pool, provisioned_users)
    now = datetime.now(timezone.utc)

    await pool.execute(
        "INSERT INTO sent_messages (user_id, message_id, thread_id, recipient, subject, sent_at) VALUES ($1, $2, $3, $4, $5, $6)",
        uuid.UUID(user_a), "msg-a", "thread-a", "a@x.com", "User A's real, private stale message", now - timedelta(days=10),
    )
    await pool.execute(
        "INSERT INTO sent_messages (user_id, message_id, thread_id, recipient, subject, sent_at) VALUES ($1, $2, $3, $4, $5, $6)",
        uuid.UUID(user_b), "msg-b", "thread-b", "b@x.com", "User B's real, private stale message", now - timedelta(days=10),
    )

    try:
        with TestClient(app) as client:
            response = client.get("/waiting_on", headers=headers_a)

        body = response.json()
        subjects_seen = {m["subject"] for m in body}
        assert "User A's real, private stale message" in subjects_seen
        assert "User B's real, private stale message" not in subjects_seen
    finally:
        await pool.execute("DELETE FROM sent_messages WHERE user_id = ANY($1::uuid[])", [uuid.UUID(user_a), uuid.UUID(user_b)])


def test_waiting_on_returns_503_not_a_crash_when_the_real_pool_is_unavailable():
    with TestClient(app) as client:
        real_pool = app.state.db_pool
        app.state.db_pool = None
        try:
            waiting_on_response = client.get("/waiting_on", headers=_auth_header())
            health_response = client.get("/health")
            assert waiting_on_response.status_code == 503
            assert health_response.status_code == 200
        finally:
            app.state.db_pool = real_pool


def test_honesty_log_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.get("/honesty_log")
    assert response.status_code == 401


async def test_honesty_log_endpoint_is_real_and_live_not_mocked_with_a_real_valid_token(pool, provisioned_users):
    """Real, end-to-end: real-provisions a real user (DEC-110), inserts
    real, distinctly-outcomed rows directly into the real, live
    `action_events` table scoped to that same exact real user, confirms
    `GET /honesty_log` genuinely round-trips through `fetch_honesty_
    feed()` with a real, valid access token, then cleans up."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    success_id, catch_id, uncertain_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    now = datetime.now(timezone.utc)
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)",
        success_id, "create_task", "S1", '{"title": "A real end-to-end task"}', "approve", "approved_unchanged",
        f"trace-{success_id}", uuid.UUID(internal_user_id), now,
    )
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)",
        catch_id, "send_email", "S3", '{"to": "a@x.com"}', "revise", "caught_by_gate",
        f"trace-{catch_id}", uuid.UUID(internal_user_id), now,
    )
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)",
        uncertain_id, "send_email", "S3", '{"to": "b@x.com"}', "approve", "uncertain_no_data",
        f"trace-{uncertain_id}", uuid.UUID(internal_user_id), now,
    )

    try:
        with TestClient(app) as client:
            response = client.get("/honesty_log", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2  # the uncertain row is excluded, per fetch_honesty_feed()'s own real rule
        assert body["success_rate"] == 0.5
        assert set(body.keys()) == {"total", "success_rate", "successes", "failures_and_catches", "genuinely_uncertain"}
        assert len(body["successes"]) == 1
        assert body["successes"][0]["description"] == "Created task: A real end-to-end task"
        assert len(body["failures_and_catches"]) == 1
        assert body["failures_and_catches"][0]["outcome"] == "caught_by_gate"
        assert len(body["genuinely_uncertain"]) == 1
    finally:
        await pool.execute(
            "DELETE FROM action_events WHERE proposal_id = ANY($1::uuid[])", [success_id, catch_id, uncertain_id]
        )


async def test_honesty_log_endpoint_never_leaks_another_real_users_rows(pool, provisioned_users):
    headers_a, user_a = await _provisioned_auth_header(pool, provisioned_users)
    _headers_b, user_b = await _provisioned_auth_header(pool, provisioned_users)
    proposal_a, proposal_b = uuid.uuid4(), uuid.uuid4()

    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)",
        proposal_a, "create_task", "S1", '{"title": "User A real task"}', "approve", "approved_unchanged",
        f"trace-{proposal_a}", uuid.UUID(user_a), datetime.now(timezone.utc),
    )
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)",
        proposal_b, "create_task", "S1", '{"title": "User B real task"}', "approve", "approved_unchanged",
        f"trace-{proposal_b}", uuid.UUID(user_b), datetime.now(timezone.utc),
    )

    try:
        with TestClient(app) as client:
            response = client.get("/honesty_log", headers=headers_a)

        body = response.json()
        ids_seen = {a["action_id"] for a in body["successes"]}
        assert str(proposal_a) in ids_seen
        assert str(proposal_b) not in ids_seen
    finally:
        await pool.execute("DELETE FROM action_events WHERE proposal_id = ANY($1::uuid[])", [proposal_a, proposal_b])


def test_honesty_log_returns_503_not_a_crash_when_the_real_pool_is_unavailable():
    with TestClient(app) as client:
        real_pool = app.state.db_pool
        app.state.db_pool = None
        try:
            honesty_log_response = client.get("/honesty_log", headers=_auth_header())
            health_response = client.get("/health")
            assert honesty_log_response.status_code == 503
            assert health_response.status_code == 200
        finally:
            app.state.db_pool = real_pool


def test_finance_subscriptions_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.get("/finance/subscriptions")
    assert response.status_code == 401


async def test_finance_subscriptions_endpoint_is_real_and_live_not_mocked_with_a_real_valid_token(pool, provisioned_users):
    """Real, end-to-end: real-provisions a real user (DEC-110), inserts
    three real, monthly-spaced charges to the same real payee (the
    real, specified minimum -- `DEC-112`), all scoped to that same
    exact real user, into the real, live `expenses` table, confirms
    `GET /finance/subscriptions` genuinely detects and round-trips the
    real pattern with a real, valid access token for that same real
    identity, then cleans up.

    A real, disclosed correction made while retrofitting this test for
    DEC-110: the original version inserted the charges under DIFFERENT
    random user_ids -- harmless before real per-user filtering existed,
    but would have silently broken this test once it did. Fixed to use
    one real, consistent user_id, matching what a real recurring charge
    actually looks like."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    payee = f"Real end-to-end test vendor {uuid.uuid4()}"
    ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    occurrences = [
        datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 31, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 2, 12, 0, tzinfo=timezone.utc),
    ]

    for expense_id, occurred_at in zip(ids, occurrences):
        await pool.execute(
            "INSERT INTO expenses (expense_id, user_id, payee, amount, occurred_at, source) VALUES ($1, $2, $3, $4, $5, $6)",
            expense_id,
            uuid.UUID(internal_user_id),
            payee,
            299.00,
            occurred_at,
            "manual",
        )

    try:
        with TestClient(app) as client:
            response = client.get("/finance/subscriptions", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)

        match = next(s for s in body if s["payee"] == payee)
        assert set(match.keys()) == {"payee", "average_amount", "occurrences", "average_interval_days"}
        assert match["average_amount"] == 299.0
        assert match["occurrences"] == 3
        assert match["average_interval_days"] == 30.0
    finally:
        await pool.execute("DELETE FROM expenses WHERE expense_id = ANY($1::uuid[])", ids)


async def test_finance_subscriptions_endpoint_never_leaks_another_real_users_rows(pool, provisioned_users):
    """The real, load-bearing correctness property DEC-110 exists to
    guarantee: two distinct real users, each with their own real
    recurring charge to the SAME real payee name -- a request as user A
    must only ever see user A's own real pattern, never user B's."""
    headers_a, user_a = await _provisioned_auth_header(pool, provisioned_users)
    _headers_b, user_b = await _provisioned_auth_header(pool, provisioned_users)
    payee = f"Shared real payee name {uuid.uuid4()}"
    ids_a = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    ids_b = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    occurrences = [
        datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 31, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 2, 12, 0, tzinfo=timezone.utc),
    ]

    for expense_id, occurred_at, user in (
        [(eid, at, user_a) for eid, at in zip(ids_a, occurrences)]
        + [(eid, at, user_b) for eid, at in zip(ids_b, occurrences)]
    ):
        await pool.execute(
            "INSERT INTO expenses (expense_id, user_id, payee, amount, occurred_at, source) VALUES ($1, $2, $3, $4, $5, $6)",
            expense_id,
            uuid.UUID(user),
            payee,
            50.00,
            occurred_at,
            "manual",
        )

    try:
        with TestClient(app) as client:
            response = client.get("/finance/subscriptions", headers=headers_a)

        body = response.json()
        matches = [s for s in body if s["payee"] == payee]
        # Exactly one real entry for this payee, from user A's own
        # three charges -- never user B's, and never merged into a
        # false occurrences=6 across both real users.
        assert len(matches) == 1
        assert matches[0]["occurrences"] == 3
    finally:
        await pool.execute("DELETE FROM expenses WHERE expense_id = ANY($1::uuid[])", ids_a + ids_b)


def test_finance_subscriptions_returns_503_not_a_crash_when_the_real_pool_is_unavailable():
    with TestClient(app) as client:
        real_pool = app.state.db_pool
        app.state.db_pool = None
        try:
            finance_response = client.get("/finance/subscriptions", headers=_auth_header())
            health_response = client.get("/health")
            assert finance_response.status_code == 503
            assert health_response.status_code == 200
        finally:
            app.state.db_pool = real_pool


def test_finance_expenses_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.get("/finance/expenses")
    assert response.status_code == 401


async def test_finance_expenses_endpoint_is_real_and_live_not_mocked_with_a_real_valid_token(pool, provisioned_users):
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    expense_id = uuid.uuid4()
    try:
        await pool.execute(
            "INSERT INTO expenses (expense_id, user_id, payee, amount, occurred_at, source) VALUES ($1, $2, $3, $4, now(), 'manual')",
            expense_id, uuid.UUID(internal_user_id), "A real end-to-end payee", 123.0,
        )

        with TestClient(app) as client:
            response = client.get("/finance/expenses", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert set(body[0].keys()) == {"expense_id", "payee", "amount", "occurred_at"}
        assert body[0]["expense_id"] == str(expense_id)
        assert body[0]["payee"] == "A real end-to-end payee"
        assert body[0]["amount"] == 123.0
    finally:
        await pool.execute("DELETE FROM expenses WHERE expense_id = $1", expense_id)


async def test_finance_expenses_never_leaks_another_real_users_rows(pool, provisioned_users):
    headers_a, _user_a = await _provisioned_auth_header(pool, provisioned_users)
    _headers_b, user_b = await _provisioned_auth_header(pool, provisioned_users)
    expense_id = uuid.uuid4()
    try:
        await pool.execute(
            "INSERT INTO expenses (expense_id, user_id, payee, amount, occurred_at, source) VALUES ($1, $2, $3, $4, now(), 'manual')",
            expense_id, uuid.UUID(user_b), "User B's real payee", 55.0,
        )

        with TestClient(app) as client:
            response = client.get("/finance/expenses", headers=headers_a)

        assert response.status_code == 200
        assert response.json() == []
    finally:
        await pool.execute("DELETE FROM expenses WHERE expense_id = $1", expense_id)


def test_finance_expenses_returns_503_not_a_crash_when_the_real_pool_is_unavailable():
    with TestClient(app) as client:
        real_pool = app.state.db_pool
        app.state.db_pool = None
        try:
            response = client.get("/finance/expenses", headers=_auth_header())
            assert response.status_code == 503
        finally:
            app.state.db_pool = real_pool


def test_auth_callback_bridges_a_real_google_redirect_to_the_real_mobile_scheme():
    # The real, necessary bridge (DEC-105): Google's own current rules
    # require a real https:// redirect for a "Web application"-type
    # OAuth client (confirmed live before building this -- custom
    # schemes are no longer accepted directly). This route's only real
    # job is forwarding Google's real query params onward to the
    # mobile app's own custom scheme.
    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/auth/callback", params={"code": "real-test-code", "state": "real-test-state"})
    assert response.status_code in (302, 307)
    location = response.headers["location"]
    assert location.startswith("com.quorum.quorummobile://oauth2redirect?")
    assert "code=real-test-code" in location
    assert "state=real-test-state" in location


def test_auth_callback_forwards_a_real_google_error_without_inventing_a_code():
    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/auth/callback", params={"error": "access_denied"})
    assert response.status_code in (302, 307)
    location = response.headers["location"]
    assert location.startswith("com.quorum.quorummobile://oauth2redirect?")
    assert "error=access_denied" in location
    assert "code=" not in location


def test_auth_callback_with_neither_code_nor_error_fails_loud_not_silently():
    # A genuine anomaly -- Google's real redirect always carries one or
    # the other. Surfaced as a real, honest error to the mobile app,
    # never silently forwarded as if a real code were present.
    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/auth/callback")
    assert response.status_code in (302, 307)
    location = response.headers["location"]
    assert "error=missing_code" in location


def test_auth_token_with_a_fake_code_fails_loud_with_a_real_400():
    # A full real round-trip needs a live browser completing Google's
    # real consent screen -- not available in this environment. This
    # proves the route's real, live path to Google (client credentials
    # genuinely wired through, per the invalid_grant-not-invalid_client
    # distinction already proven directly against google_oauth.py) and
    # its real error handling, the furthest this environment can verify
    # /auth/token without a human in a browser.
    with TestClient(app) as client:
        response = client.post(
            "/auth/token",
            json={
                "code": "deliberately-fake-code-for-a-real-test",
                "code_verifier": "deliberately-fake-verifier",
                "redirect_uri": "https://example.com/callback",
            },
        )
    assert response.status_code == 400
    assert "invalid_grant" in response.json()["detail"]


async def test_auth_token_a_real_sign_in_missing_a_refresh_token_never_500s(pool, monkeypatch):
    """Real regression test for this PR's own CRITICAL-tier review,
    BLOCKER 1: a real, live-proven 500 that made sign-in permanently
    impossible whenever Google's own token response omitted
    `refresh_token` -- reachable for every currently-signed-in real
    user's very first sign-in after `auth_controller.dart`'s own real
    `access_type=offline` change first ships, since before that no real
    authorization request ever carried it. Mocks only the two real
    network calls to Google this route can't complete without a live
    browser (`exchange_authorization_code`, `verify_google_id_token`);
    every other real code path -- user provisioning, the new branching
    logic, session issuance -- runs for real.

    `get_settings()` is monkeypatched via the same real, established
    `model_copy()` technique `test_search_returns_503_when_the_
    embedding_provider_is_not_configured` already uses -- CI's own real,
    disclosed environment (`DEC-115`) has no real `GOOGLE_OAUTH_CLIENT_
    ID`/`SECRET` configured at all, so this route's own real config
    check would otherwise 503 before ever reaching the two mocked
    functions above; every other real field (including CI's own real,
    configured `GOOGLE_TOKEN_ENCRYPTION_KEY`) stays intact."""
    from quorum_backend import main as main_module

    google_sub = f"test-auth-token-no-refresh-{uuid.uuid4()}"

    async def _fake_exchange(**kwargs):
        return {"access_token": "a-real-looking-access-token", "id_token": "irrelevant", "expires_in": 3600, "scope": "openid email"}

    def _fake_verify(id_token, client_id):
        return {"sub": google_sub, "email": "test@example.com"}

    fake_settings = get_settings().model_copy(
        update={"google_oauth_client_id": "fake-client-id-for-a-real-test", "google_oauth_client_secret": "fake-client-secret-for-a-real-test"}
    )
    monkeypatch.setattr(main_module, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(main_module, "exchange_authorization_code", _fake_exchange)
    monkeypatch.setattr(main_module, "verify_google_id_token", _fake_verify)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/auth/token",
                json={"code": "irrelevant", "code_verifier": "irrelevant", "redirect_uri": "https://example.com/callback"},
            )

        assert response.status_code == 200  # the real, load-bearing fix -- this used to be a real 500
        body = response.json()
        assert body["access_token"]
        assert body["refresh_token"]

        internal_user_id = await pool.fetchval("SELECT user_id FROM users WHERE google_sub = $1", google_sub)
        assert internal_user_id is not None  # the real user was still genuinely provisioned
        # No real Google token row was ever created -- genuinely nothing
        # to store, honestly skipped, not fabricated.
        assert await pool.fetchrow("SELECT 1 FROM google_oauth_tokens WHERE user_id = $1", internal_user_id) is None
    finally:
        await pool.execute("DELETE FROM users WHERE google_sub = $1", google_sub)


def test_auth_callback_real_url_encodes_special_characters_in_state():
    # A real, deliberate correctness check: state values can legitimately
    # contain characters (&, =, spaces) that manual string concatenation
    # would corrupt into a broken redirect URL.
    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/auth/callback", params={"code": "c1", "state": "a&b=c d"})
    location = response.headers["location"]
    from urllib.parse import parse_qs, urlsplit

    parsed = parse_qs(urlsplit(location).query)
    assert parsed["state"] == ["a&b=c d"]


async def test_auth_refresh_genuinely_rotates_a_real_token_against_the_real_database(pool):
    store = SupabaseRevocationStore(pool)
    user_id = f"test-user-{uuid.uuid4()}"
    raw_refresh = await issue_refresh_token(user_id, store)

    try:
        with TestClient(app) as client:
            response = client.post("/auth/refresh", json={"refresh_token": raw_refresh})

        assert response.status_code == 200
        body = response.json()
        assert body["refresh_token"] != raw_refresh
        assert body["token_type"] == "bearer"
        assert isinstance(body["access_token"], str)
        assert len(body["access_token"]) > 0

        # The real theft-detection property, exercised through the real
        # HTTP route: presenting the OLD, now-rotated-away token again
        # must fail as real reuse, not silently succeed a second time.
        with TestClient(app) as client:
            reuse_response = client.post("/auth/refresh", json={"refresh_token": raw_refresh})
        assert reuse_response.status_code == 401
    finally:
        await pool.execute("DELETE FROM refresh_tokens WHERE user_id = $1", user_id)


async def test_auth_refresh_with_an_unknown_token_is_a_real_401():
    with TestClient(app) as client:
        response = client.post("/auth/refresh", json={"refresh_token": "a-token-that-was-never-issued"})
    assert response.status_code == 401


async def test_auth_revoke_requires_real_auth():
    with TestClient(app) as client:
        response = client.post("/auth/revoke")
    assert response.status_code == 401


async def test_auth_revoke_genuinely_signs_out_every_real_session_for_that_user(pool):
    store = SupabaseRevocationStore(pool)
    user_id = f"test-user-{uuid.uuid4()}"
    raw_refresh = await issue_refresh_token(user_id, store)
    settings = get_settings()
    access_token = create_access_token(user_id, settings.jwt_signing_key)

    try:
        with TestClient(app) as client:
            response = client.post("/auth/revoke", headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 204

        # The real, live proof: the session issued before revocation no
        # longer rotates -- genuinely revoked in the real database, not
        # just a 204 returned without real effect.
        with pytest.raises(TokenRevoked):
            await rotate_refresh_token(raw_refresh, store)
    finally:
        await pool.execute("DELETE FROM refresh_tokens WHERE user_id = $1", user_id)


def test_delete_account_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.delete("/account")
    assert response.status_code == 401


async def test_delete_account_genuinely_purges_real_data_and_revokes_real_sessions(pool):
    """Real, end-to-end, irreversible: real-provisions a real user
    (mirroring what `/auth/token` does at real sign-in), issues a real
    refresh token for that same identity (mirroring a real, live
    session), inserts one real task PLUS one real `action_events` row
    and one real `negotiations` row (`DEC-124` -- the real gap this
    session closed; this test would have caught the original gap had
    it existed before this session), calls `DELETE /account` with a
    real, valid access token, then confirms -- against the real, live
    database, not just the response body -- that every real row is
    gone, the real `users` row is gone, and the real session can no
    longer rotate. Nothing left to clean up in `finally`: a correct
    real deletion IS the cleanup."""
    google_sub = f"test-deletion-e2e-{uuid.uuid4()}"
    internal_user_id = await get_or_create_user(pool, google_sub=google_sub, email=None)
    revocation_store = SupabaseRevocationStore(pool)
    raw_refresh = await issue_refresh_token(google_sub, revocation_store)
    settings = get_settings()
    access_token = create_access_token(google_sub, settings.jwt_signing_key)

    task_id = uuid.uuid4()
    proposal_id = uuid.uuid4()
    negotiation_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, $5, $6)",
        task_id,
        uuid.UUID(internal_user_id),
        "A real task, about to be really, permanently deleted",
        1.0,
        None,
        "open",
    )
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, trace_id, user_id) VALUES ($1, $2, $3, $4::jsonb, $5, $6)",
        proposal_id, "create_note", "S0", "{}", f"test-deletion-e2e-{proposal_id}", uuid.UUID(internal_user_id),
    )
    await pool.execute(
        "INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at) VALUES ($1, $2, $3, $4)",
        negotiation_id, uuid.UUID(internal_user_id), ["finance"], datetime.now(timezone.utc),
    )

    with TestClient(app) as client:
        response = client.delete("/account", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == internal_user_id
    assert body["sessions_revoked"] is True
    # 1 real task + 1 real action_event + 1 real negotiation + 1 real
    # users row -- the real, honest count, not a placeholder.
    assert body["postgres_rows_deleted"] == 4
    assert body["vector_embeddings_deleted"] == 0
    assert body["memories_deleted"] == 0
    assert body["oauth_tokens_revoked"] == 0

    # Real, live confirmation against the real database, not just a
    # trusted response body.
    assert await pool.fetchrow("SELECT 1 FROM tasks WHERE task_id = $1", task_id) is None
    assert await pool.fetchrow("SELECT 1 FROM action_events WHERE proposal_id = $1", proposal_id) is None
    assert await pool.fetchrow("SELECT 1 FROM negotiations WHERE negotiation_id = $1", negotiation_id) is None
    assert await pool.fetchrow("SELECT 1 FROM users WHERE user_id = $1", uuid.UUID(internal_user_id)) is None
    with pytest.raises(TokenRevoked):
        await rotate_refresh_token(raw_refresh, revocation_store)


async def test_delete_account_genuinely_revokes_real_google_oauth_tokens_too(pool):
    """Phase 3, `QUORUM_PRODUCTION_COMPLETION_PLAN.md`. Real, end-to-end,
    through the actual `DELETE /account` route: seeds a real, encrypted
    Google token row for this user (a real, deliberately-invalid token
    value, since no real, valid Google-issued one is available to this
    test suite -- see `test_google_token_refresh.py`'s own docstring),
    then confirms the real route reports a real, nonzero `oauth_tokens_
    revoked` count and the real row is genuinely gone -- not the honest
    `0` every prior version of this test asserted before Phase 3 closed
    this gap."""
    google_sub = f"test-deletion-oauth-{uuid.uuid4()}"
    internal_user_id = await get_or_create_user(pool, google_sub=google_sub, email=None)
    revocation_store = SupabaseRevocationStore(pool)
    await issue_refresh_token(google_sub, revocation_store)
    settings = get_settings()
    access_token = create_access_token(google_sub, settings.jwt_signing_key)

    from quorum_backend.auth.google_token_store import store_google_tokens

    assert settings.google_token_encryption_key is not None, (
        "This test needs a real GOOGLE_TOKEN_ENCRYPTION_KEY configured in backend/.env to mean anything."
    )
    await store_google_tokens(
        pool,
        internal_user_id=internal_user_id,
        access_token="deliberately-fake-access-token-for-a-real-test",
        refresh_token="deliberately-fake-refresh-token-for-a-real-test",
        access_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        granted_scopes="openid email",
        encryption_key=settings.google_token_encryption_key,
    )

    with TestClient(app) as client:
        response = client.delete("/account", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200
    assert response.json()["oauth_tokens_revoked"] == 1
    assert await pool.fetchrow("SELECT 1 FROM google_oauth_tokens WHERE user_id = $1", uuid.UUID(internal_user_id)) is None


async def test_delete_account_never_touches_a_different_real_users_data(pool):
    victim_sub = f"test-deletion-victim-{uuid.uuid4()}"
    bystander_sub = f"test-deletion-bystander-{uuid.uuid4()}"
    victim_id = await get_or_create_user(pool, google_sub=victim_sub, email=None)
    bystander_id = await get_or_create_user(pool, google_sub=bystander_sub, email=None)
    revocation_store = SupabaseRevocationStore(pool)
    bystander_refresh = await issue_refresh_token(bystander_sub, revocation_store)
    settings = get_settings()
    victim_access_token = create_access_token(victim_sub, settings.jwt_signing_key)

    bystander_task = uuid.uuid4()
    bystander_proposal = uuid.uuid4()
    bystander_negotiation = uuid.uuid4()
    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, $5, $6)",
        bystander_task,
        uuid.UUID(bystander_id),
        "Bystander's real, untouched task",
        1.0,
        None,
        "open",
    )
    # DEC-124: the same real cross-user proof, extended to
    # action_events/negotiations at the full HTTP layer too -- the
    # store-layer test already proved this property directly against
    # purge_postgres_rows(), but a CRITICAL-tier review correctly
    # flagged that this route-level test hadn't been extended to
    # match, an inconsistency in how thoroughly the two layers were
    # covered, not a real gap in confidence -- closed here anyway.
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, trace_id, user_id) VALUES ($1, $2, $3, $4::jsonb, $5, $6)",
        bystander_proposal, "create_note", "S0", "{}", f"test-deletion-{bystander_proposal}", uuid.UUID(bystander_id),
    )
    await pool.execute(
        "INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at) VALUES ($1, $2, $3, $4)",
        bystander_negotiation, uuid.UUID(bystander_id), ["finance"], datetime.now(timezone.utc),
    )

    try:
        with TestClient(app) as client:
            response = client.delete("/account", headers={"Authorization": f"Bearer {victim_access_token}"})
        assert response.status_code == 200
        # The real, deleted identity really is the victim's own internal
        # UUID -- never the bystander's, confirming the route resolved
        # and acted on the correct real account.
        assert response.json()["user_id"] == victim_id

        # The bystander's real task, action_event, negotiation, real
        # users row, and real session all survive completely untouched.
        assert await pool.fetchrow("SELECT 1 FROM tasks WHERE task_id = $1", bystander_task) is not None
        assert await pool.fetchrow("SELECT 1 FROM action_events WHERE proposal_id = $1", bystander_proposal) is not None
        assert await pool.fetchrow("SELECT 1 FROM negotiations WHERE negotiation_id = $1", bystander_negotiation) is not None
        assert await pool.fetchrow("SELECT 1 FROM users WHERE user_id = $1", uuid.UUID(bystander_id)) is not None
        # A real, live proof the bystander's own session still rotates
        # -- never revoked by someone else's account deletion.
        await rotate_refresh_token(bystander_refresh, revocation_store)
    finally:
        await pool.execute("DELETE FROM tasks WHERE task_id = $1", bystander_task)
        await pool.execute("DELETE FROM action_events WHERE proposal_id = $1", bystander_proposal)
        await pool.execute("DELETE FROM negotiations WHERE negotiation_id = $1", bystander_negotiation)
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(bystander_id))
        await pool.execute("DELETE FROM refresh_tokens WHERE user_id = $1", bystander_sub)


def test_delete_account_returns_503_not_a_crash_when_the_real_pool_is_unavailable():
    with TestClient(app) as client:
        real_pool = app.state.db_pool
        app.state.db_pool = None
        try:
            response = client.delete("/account", headers=_auth_header())
            health_response = client.get("/health")
            assert response.status_code == 503
            assert health_response.status_code == 200
        finally:
            app.state.db_pool = real_pool


# --- POST /internal/drain-retry-queue (DEC-127) ---


def test_drain_retry_queue_is_401_when_no_internal_secret_is_configured_at_all(monkeypatch):
    monkeypatch.delenv("INTERNAL_DRAIN_SECRET", raising=False)
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/drain-retry-queue")
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_drain_retry_queue_is_401_with_a_real_configured_secret_but_no_header(monkeypatch):
    monkeypatch.setenv("INTERNAL_DRAIN_SECRET", "a-real-configured-secret")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/drain-retry-queue")
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_drain_retry_queue_is_401_with_a_real_configured_secret_but_the_wrong_header_value(monkeypatch):
    monkeypatch.setenv("INTERNAL_DRAIN_SECRET", "a-real-configured-secret")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/drain-retry-queue", headers={"X-Internal-Secret": "not-the-real-secret"})
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_drain_retry_queue_real_secret_and_matching_header_reaches_the_real_drainer(monkeypatch):
    """A real, live proof the route's own auth genuinely passes through
    to the real drainer with an empty real `retry_queue` -- not a mocked
    success. `retry_queue_drainer.py`'s own real, deep integration
    (translate -> propose -> Stage A -> Stage B -> persist) is covered
    directly and thoroughly by `test_retry_queue_drainer.py`; this test
    proves only that this specific route's own real auth dependency and
    real wiring genuinely reach that module, using this real, live
    deployment's own real Gemini/Groq keys (skipped without them, the
    same discipline every other real-key-dependent test in this backend
    already follows)."""
    settings = get_settings()
    if settings.gemini_api_key is None or settings.groq_api_key is None:
        import pytest

        pytest.skip("no real GEMINI_API_KEY/GROQ_API_KEY configured in this environment")

    monkeypatch.setenv("INTERNAL_DRAIN_SECRET", "a-real-configured-secret")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/drain-retry-queue", headers={"X-Internal-Secret": "a-real-configured-secret"})
        assert response.status_code == 200
        body = response.json()
        assert set(body.keys()) == {
            "jobs_seen",
            "jobs_succeeded",
            "jobs_failed",
            "downstream_actions_produced",
            "downstream_actions_executed",
        }
    finally:
        get_settings.cache_clear()


# --- POST /internal/deadline-watch (Phase 2, DEC-13x) ---


def test_deadline_watch_is_401_when_no_internal_secret_is_configured_at_all(monkeypatch):
    monkeypatch.delenv("INTERNAL_DRAIN_SECRET", raising=False)
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/deadline-watch")
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_deadline_watch_is_401_with_a_real_configured_secret_but_no_header(monkeypatch):
    monkeypatch.setenv("INTERNAL_DRAIN_SECRET", "a-real-configured-secret")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/deadline-watch")
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_deadline_watch_is_401_with_a_real_configured_secret_but_the_wrong_header_value(monkeypatch):
    monkeypatch.setenv("INTERNAL_DRAIN_SECRET", "a-real-configured-secret")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/deadline-watch", headers={"X-Internal-Secret": "not-the-real-secret"})
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_deadline_watch_real_secret_and_matching_header_reaches_the_real_route_wiring(monkeypatch):
    """Proves this route's own real auth dependency and real response
    mapping, WITHOUT a real, unscoped call to `run_deadline_watch()` --
    that would iterate this deployment's ENTIRE real `users` table,
    including its one real, live, non-test account, a real risk
    `test_deadline_watch.py`'s own top-of-file docstring already
    discloses and avoids. `run_deadline_watch()`'s own real, deep logic
    (per-user scan, real trigger, real idempotency guard) is covered
    directly and safely there, scoped to real, test-owned user_ids only
    -- this test proves only that this route reaches that real function
    and maps its real result correctly, the same "prove the wiring, not
    re-prove the underlying logic" precedent `test_drain_retry_queue_
    real_secret_and_matching_header_reaches_the_real_drainer` above
    already established for `/internal/drain-retry-queue`."""
    from quorum_backend.features.deadline_watch import DeadlineWatchResult

    async def _fake_run_deadline_watch(pool):
        return DeadlineWatchResult(
            users_scanned=3, users_failed=0, negotiations_created=1,
            outcome_counts={"NO_CLAIM": 1, "NO_CONFLICT": 1, "ALREADY_NEGOTIATING": 0, "CREATED": 1},
        )

    monkeypatch.setattr("quorum_backend.main.run_deadline_watch", _fake_run_deadline_watch)
    monkeypatch.setenv("INTERNAL_DRAIN_SECRET", "a-real-configured-secret")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/deadline-watch", headers={"X-Internal-Secret": "a-real-configured-secret"})
        assert response.status_code == 200
        assert response.json() == {
            "users_scanned": 3,
            "users_failed": 0,
            "negotiations_created": 1,
            "outcome_counts": {"NO_CLAIM": 1, "NO_CONFLICT": 1, "ALREADY_NEGOTIATING": 0, "CREATED": 1},
        }
    finally:
        get_settings.cache_clear()


# --- POST /internal/spend-alert (Phase 2, DEC-13x) ---


def test_spend_alert_is_401_when_no_internal_secret_is_configured_at_all(monkeypatch):
    monkeypatch.delenv("INTERNAL_DRAIN_SECRET", raising=False)
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/spend-alert")
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_spend_alert_is_401_with_a_real_configured_secret_but_no_header(monkeypatch):
    monkeypatch.setenv("INTERNAL_DRAIN_SECRET", "a-real-configured-secret")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/spend-alert")
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_spend_alert_is_401_with_a_real_configured_secret_but_the_wrong_header_value(monkeypatch):
    monkeypatch.setenv("INTERNAL_DRAIN_SECRET", "a-real-configured-secret")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/spend-alert", headers={"X-Internal-Secret": "not-the-real-secret"})
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_spend_alert_real_secret_and_matching_header_reaches_the_real_route_wiring(monkeypatch):
    """Proves this route's own real auth dependency and real response
    mapping, WITHOUT a real, unscoped call to `run_spend_alert()` --
    the same real safety precedent `test_deadline_watch_real_secret_
    and_matching_header_reaches_the_real_route_wiring` above already
    established. `run_spend_alert()`'s own real, deep logic is covered
    directly and safely in `test_spend_alert.py`, scoped to real,
    test-owned user_ids only."""
    from quorum_backend.features.spend_alert import SpendAlertResult

    async def _fake_run_spend_alert(pool):
        return SpendAlertResult(
            users_scanned=3, users_failed=0, negotiations_created=1,
            outcome_counts={"NO_CLAIM": 1, "NO_CONFLICT": 1, "ALREADY_NEGOTIATING": 0, "CREATED": 1},
        )

    monkeypatch.setattr("quorum_backend.main.run_spend_alert", _fake_run_spend_alert)
    monkeypatch.setenv("INTERNAL_DRAIN_SECRET", "a-real-configured-secret")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/spend-alert", headers={"X-Internal-Secret": "a-real-configured-secret"})
        assert response.status_code == 200
        assert response.json() == {
            "users_scanned": 3,
            "users_failed": 0,
            "negotiations_created": 1,
            "outcome_counts": {"NO_CLAIM": 1, "NO_CONFLICT": 1, "ALREADY_NEGOTIATING": 0, "CREATED": 1},
        }
    finally:
        get_settings.cache_clear()


# --- POST /internal/backfill-negotiation-detail (Phase 2, DEC-134) ---


def test_backfill_negotiation_detail_is_401_when_no_internal_secret_is_configured_at_all(monkeypatch):
    monkeypatch.delenv("INTERNAL_DRAIN_SECRET", raising=False)
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/backfill-negotiation-detail")
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_backfill_negotiation_detail_is_401_with_a_real_configured_secret_but_no_header(monkeypatch):
    monkeypatch.setenv("INTERNAL_DRAIN_SECRET", "a-real-configured-secret")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/backfill-negotiation-detail")
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_backfill_negotiation_detail_is_401_with_a_real_configured_secret_but_the_wrong_header_value(monkeypatch):
    monkeypatch.setenv("INTERNAL_DRAIN_SECRET", "a-real-configured-secret")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/backfill-negotiation-detail", headers={"X-Internal-Secret": "not-the-real-secret"})
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_backfill_negotiation_detail_is_503_when_the_secret_is_real_but_groq_is_not_configured(monkeypatch):
    """Real, honest `503` when the Groq provider isn't configured
    (`DEC-166` -- this route's real position/synthesis calls moved off
    Gemini onto Groq) -- matching `GET /search`'s own already-established
    pattern for the same real dependency, checked BEFORE this route's
    own auth-passing logic ever reaches `run_negotiation_detail_
    backfill()`. Uses `GET /search`'s own real, disclosed `model_copy()`
    fix directly (see that test's own docstring): `monkeypatch.delenv
    ("GROQ_API_KEY")` alone has no effect since pydantic-settings reads
    `backend/.env` as a file, not this shell's own OS environment."""
    from quorum_backend import main as main_module

    fake_settings = get_settings().model_copy(update={"groq_api_key": None, "internal_drain_secret": "a-real-configured-secret"})
    monkeypatch.setattr(main_module, "get_settings", lambda: fake_settings)
    with TestClient(app) as client:
        response = client.post("/internal/backfill-negotiation-detail", headers={"X-Internal-Secret": "a-real-configured-secret"})
    assert response.status_code == 503


def test_backfill_negotiation_detail_real_secret_and_matching_header_reaches_the_real_route_wiring(monkeypatch):
    """Proves this route's own real auth dependency, real Groq-
    configured precondition, and real response mapping, WITHOUT a real,
    unscoped call to `run_negotiation_detail_backfill()` -- the same
    real safety precedent every other `/internal/*` route test in this
    file already established. That function's own real, deep logic is
    covered directly and safely in `test_negotiation_detail_backfill.py`,
    scoped to real, test-owned negotiation_ids only."""
    from quorum_backend.features.negotiation_detail_backfill import NegotiationDetailBackfillResult

    async def _fake_run_negotiation_detail_backfill(pool, *, api_key):
        return NegotiationDetailBackfillResult(
            negotiations_scanned=2, negotiations_failed=0, negotiations_detailed=1,
            outcome_counts={"UNKNOWN_TRIGGER_SOURCE": 0, "SITUATION_RESOLVED": 1, "ALREADY_DETAILED": 0, "DETAILED": 1},
        )

    monkeypatch.setattr("quorum_backend.main.run_negotiation_detail_backfill", _fake_run_negotiation_detail_backfill)
    monkeypatch.setenv("INTERNAL_DRAIN_SECRET", "a-real-configured-secret")
    monkeypatch.setenv("GROQ_API_KEY", "a-real-configured-groq-key")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/backfill-negotiation-detail", headers={"X-Internal-Secret": "a-real-configured-secret"})
        assert response.status_code == 200
        assert response.json() == {
            "negotiations_scanned": 2,
            "negotiations_failed": 0,
            "negotiations_detailed": 1,
            "outcome_counts": {"UNKNOWN_TRIGGER_SOURCE": 0, "SITUATION_RESOLVED": 1, "ALREADY_DETAILED": 0, "DETAILED": 1},
        }
    finally:
        get_settings.cache_clear()


def test_email_ingestion_is_401_when_no_internal_secret_is_configured_at_all(monkeypatch):
    monkeypatch.delenv("INTERNAL_DRAIN_SECRET", raising=False)
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/email-ingestion")
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_email_ingestion_is_401_with_a_real_configured_secret_but_no_header(monkeypatch):
    monkeypatch.setenv("INTERNAL_DRAIN_SECRET", "a-real-configured-secret")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/email-ingestion")
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_email_ingestion_is_401_with_a_real_configured_secret_but_the_wrong_header_value(monkeypatch):
    monkeypatch.setenv("INTERNAL_DRAIN_SECRET", "a-real-configured-secret")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/email-ingestion", headers={"X-Internal-Secret": "not-the-real-secret"})
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_email_ingestion_is_503_when_the_secret_is_real_but_google_oauth_is_not_fully_configured(monkeypatch):
    """Real, honest `503` when Google OAuth isn't fully configured on
    this deployment -- matching `/internal/backfill-negotiation-detail`'s
    own already-established pattern for its own real Gemini dependency,
    checked BEFORE this route's own auth-passing logic ever reaches
    `run_email_ingestion()`. Uses the same real, disclosed `model_copy()`
    fix (see that test's own docstring): `monkeypatch.delenv(...)` alone
    has no effect since pydantic-settings reads `backend/.env` as a
    file, not this shell's own OS environment."""
    from quorum_backend import main as main_module

    fake_settings = get_settings().model_copy(
        update={"google_oauth_client_id": None, "internal_drain_secret": "a-real-configured-secret"}
    )
    monkeypatch.setattr(main_module, "get_settings", lambda: fake_settings)
    with TestClient(app) as client:
        response = client.post("/internal/email-ingestion", headers={"X-Internal-Secret": "a-real-configured-secret"})
    assert response.status_code == 503


def test_email_ingestion_real_secret_and_matching_header_reaches_the_real_route_wiring(monkeypatch):
    """Proves this route's own real auth dependency, real Google-OAuth-
    configured precondition, and real response mapping, WITHOUT a real,
    unscoped call to `run_email_ingestion()` -- the same real safety
    precedent every other `/internal/*` route test in this file already
    established. That function's own real, deep logic (including the
    one real, live Gmail capstone test) is covered directly and safely
    in `test_email_ingestion.py`, scoped to real, test-owned users only."""
    from quorum_backend.features.email_ingestion import EmailIngestionResult

    async def _fake_run_email_ingestion(pool, *, client_id, client_secret, encryption_key, user_ids=None, interview_detection_call=None):
        return EmailIngestionResult(
            users_scanned=3, users_failed=0, users_skipped_no_token=1, users_token_refresh_failed=1,
            messages_failed=0, new_sent_messages=2, new_replies_detected=1, interviews_detected=0,
        )

    monkeypatch.setattr("quorum_backend.main.run_email_ingestion", _fake_run_email_ingestion)
    monkeypatch.setenv("INTERNAL_DRAIN_SECRET", "a-real-configured-secret")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "a-real-configured-client-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "a-real-configured-client-secret")
    monkeypatch.setenv("GOOGLE_TOKEN_ENCRYPTION_KEY", "a-real-configured-encryption-key")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/email-ingestion", headers={"X-Internal-Secret": "a-real-configured-secret"})
        assert response.status_code == 200
        assert response.json() == {
            "users_scanned": 3,
            "users_failed": 0,
            "users_skipped_no_token": 1,
            "users_token_refresh_failed": 1,
            "messages_failed": 0,
            "new_sent_messages": 2,
            "new_replies_detected": 1,
            "interviews_detected": 0,
            "already_running": False,
        }
    finally:
        get_settings.cache_clear()


def test_email_ingestion_route_wires_a_real_interview_detection_call_only_when_groq_is_configured(monkeypatch):
    """RESOLVED, `DEC-169`: this route's own real, conditional wiring
    (`make_groq_interview_detection_call(...) if settings.groq_api_key
    else None`) is proven directly here, both ways -- never assumed
    correct just because the individual pieces (`interview_detection.py`,
    `email_ingestion.py`'s own optional param) are each tested in
    isolation elsewhere. Uses the same real, established `model_copy()`
    fix every other test in this file already relies on for this exact
    kind of check: `monkeypatch.setenv`/`delenv` alone has no effect on
    `GROQ_API_KEY` here, since pydantic-settings reads `backend/.env` as
    a file, not this shell's own OS environment."""
    from quorum_backend import main as main_module
    from quorum_backend.features.email_ingestion import EmailIngestionResult

    captured: dict = {}

    async def _capturing_fake_run_email_ingestion(pool, *, client_id, client_secret, encryption_key, user_ids=None, interview_detection_call=None):
        captured["interview_detection_call"] = interview_detection_call
        return EmailIngestionResult(
            users_scanned=0, users_failed=0, users_skipped_no_token=0, users_token_refresh_failed=0,
            messages_failed=0, new_sent_messages=0, new_replies_detected=0, interviews_detected=0,
        )

    monkeypatch.setattr(main_module, "run_email_ingestion", _capturing_fake_run_email_ingestion)

    configured_settings = get_settings().model_copy(
        update={
            "groq_api_key": "a-real-configured-groq-key",
            "google_oauth_client_id": "a-real-configured-client-id",
            "google_oauth_client_secret": "a-real-configured-client-secret",
            "google_token_encryption_key": "a-real-configured-encryption-key",
            "internal_drain_secret": "a-real-configured-secret",
        }
    )
    monkeypatch.setattr(main_module, "get_settings", lambda: configured_settings)
    with TestClient(app) as client:
        response = client.post("/internal/email-ingestion", headers={"X-Internal-Secret": "a-real-configured-secret"})
    assert response.status_code == 200
    assert captured["interview_detection_call"] is not None

    unconfigured_settings = configured_settings.model_copy(update={"groq_api_key": None})
    monkeypatch.setattr(main_module, "get_settings", lambda: unconfigured_settings)
    with TestClient(app) as client:
        response = client.post("/internal/email-ingestion", headers={"X-Internal-Secret": "a-real-configured-secret"})
    assert response.status_code == 200
    assert captured["interview_detection_call"] is None


# --- GET /career_pipeline/{application_id}/digest (Phase 6, DEC-147) ---


async def test_career_digest_endpoint_is_real_and_live_not_mocked_with_a_real_valid_token(pool, provisioned_users):
    """Real, end-to-end: real-provisions a real user (DEC-110), inserts
    a real `applications` row with a real, compiled digest scoped to
    that exact user, confirms `GET /career_pipeline/{application_id}/
    digest` genuinely round-trips through `fetch_company_digest()` with
    a real, valid access token, then cleans up."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    application_id = uuid.uuid4()
    digest_json = json.dumps({"summary_points": ["A real, live-tested summary point."], "source_count": 2})
    await pool.execute(
        "INSERT INTO applications (application_id, user_id, company, status, digest) VALUES ($1, $2, $3, $4, $5::jsonb)",
        application_id, uuid.UUID(internal_user_id), "Real Test Company", "interview_scheduled", digest_json,
    )

    try:
        with TestClient(app) as client:
            response = client.get(f"/career_pipeline/{application_id}/digest", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert body == {"company": "Real Test Company", "summary_points": ["A real, live-tested summary point."], "source_count": 2}
    finally:
        await pool.execute("DELETE FROM applications WHERE application_id = $1", application_id)


async def test_career_digest_endpoint_returns_404_when_the_real_digest_has_not_been_compiled_yet(pool, provisioned_users):
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    application_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO applications (application_id, user_id, company, status) VALUES ($1, $2, $3, $4)",
        application_id, uuid.UUID(internal_user_id), "Real Test Company", "interview_scheduled",
    )

    try:
        with TestClient(app) as client:
            response = client.get(f"/career_pipeline/{application_id}/digest", headers=headers)
        assert response.status_code == 404
    finally:
        await pool.execute("DELETE FROM applications WHERE application_id = $1", application_id)


async def test_career_digest_endpoint_returns_404_for_a_real_application_belonging_to_another_real_user(pool, provisioned_users):
    headers_a, _user_a = await _provisioned_auth_header(pool, provisioned_users)
    _headers_b, user_b = await _provisioned_auth_header(pool, provisioned_users)
    application_id = uuid.uuid4()
    digest_json = json.dumps({"summary_points": ["a point"], "source_count": 1})
    await pool.execute(
        "INSERT INTO applications (application_id, user_id, company, status, digest) VALUES ($1, $2, $3, $4, $5::jsonb)",
        application_id, uuid.UUID(user_b), "Real Test Company", "interview_scheduled", digest_json,
    )

    try:
        with TestClient(app) as client:
            response = client.get(f"/career_pipeline/{application_id}/digest", headers=headers_a)
        assert response.status_code == 404
    finally:
        await pool.execute("DELETE FROM applications WHERE application_id = $1", application_id)


def test_career_digest_endpoint_a_real_syntactically_invalid_id_is_a_real_404_not_a_500():
    with TestClient(app) as client:
        response = client.get("/career_pipeline/not-a-real-uuid/digest", headers=_auth_header())
    assert response.status_code == 404


def test_career_digest_endpoint_requires_real_auth_missing_header_is_401():
    with TestClient(app) as client:
        response = client.get(f"/career_pipeline/{uuid.uuid4()}/digest")
    assert response.status_code == 401


def test_career_digest_endpoint_returns_503_not_a_crash_when_the_real_pool_is_unavailable():
    with TestClient(app) as client:
        real_pool = app.state.db_pool
        app.state.db_pool = None
        try:
            response = client.get(f"/career_pipeline/{uuid.uuid4()}/digest", headers=_auth_header())
            health_response = client.get("/health")
            assert response.status_code == 503
            assert health_response.status_code == 200
        finally:
            app.state.db_pool = real_pool


# --- POST /internal/career-digest (Phase 6, DEC-147) ---


def test_career_digest_route_is_401_when_no_internal_secret_is_configured_at_all(monkeypatch):
    monkeypatch.delenv("INTERNAL_DRAIN_SECRET", raising=False)
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/career-digest")
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_career_digest_route_is_401_with_a_real_configured_secret_but_the_wrong_header_value(monkeypatch):
    monkeypatch.setenv("INTERNAL_DRAIN_SECRET", "a-real-configured-secret")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/career-digest", headers={"X-Internal-Secret": "not-the-real-secret"})
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_career_digest_route_is_503_when_the_secret_is_real_but_tavily_is_not_configured(monkeypatch):
    """Real, honest `503` when either real provider isn't configured --
    checked BEFORE this route's own auth-passing logic ever reaches
    `run_career_digest()`. Uses the same real, established `model_copy()`
    fix `/internal/backfill-negotiation-detail`'s own test already
    documents: `monkeypatch.delenv(...)` alone has no effect since
    pydantic-settings reads `backend/.env` as a file, not this shell's
    own OS environment."""
    from quorum_backend import main as main_module

    fake_settings = get_settings().model_copy(
        update={"tavily_api_key": None, "internal_drain_secret": "a-real-configured-secret"}
    )
    monkeypatch.setattr(main_module, "get_settings", lambda: fake_settings)
    with TestClient(app) as client:
        response = client.post("/internal/career-digest", headers={"X-Internal-Secret": "a-real-configured-secret"})
    assert response.status_code == 503


def test_career_digest_route_is_503_when_the_secret_is_real_but_groq_is_not_configured(monkeypatch):
    """Groq, not Gemini, since `DEC-166` -- this route's real
    summarization call moved off Gemini onto Groq."""
    from quorum_backend import main as main_module

    fake_settings = get_settings().model_copy(
        update={"groq_api_key": None, "internal_drain_secret": "a-real-configured-secret"}
    )
    monkeypatch.setattr(main_module, "get_settings", lambda: fake_settings)
    with TestClient(app) as client:
        response = client.post("/internal/career-digest", headers={"X-Internal-Secret": "a-real-configured-secret"})
    assert response.status_code == 503


def test_career_digest_route_real_secret_and_matching_header_reaches_the_real_route_wiring(monkeypatch):
    """Proves this route's own real auth dependency, real provider-
    configured precondition, and real response mapping, WITHOUT a real,
    unscoped call to `run_career_digest()` -- the same real safety
    precedent every other `/internal/*` route test in this file already
    established. That function's own real, deep logic is covered
    directly and safely in `test_career_digest.py`, scoped to real,
    test-owned application_ids only."""
    from quorum_backend.features.career_digest import CareerDigestRunResult

    async def _fake_run_career_digest(pool, *, tavily_api_key, compile_digest_call):
        return CareerDigestRunResult(
            applications_scanned=1, applications_failed=0, digests_compiled=1,
            outcome_counts={"ALREADY_DIGESTED": 0, "DIGESTED": 1},
        )

    monkeypatch.setattr("quorum_backend.main.run_career_digest", _fake_run_career_digest)
    monkeypatch.setenv("INTERNAL_DRAIN_SECRET", "a-real-configured-secret")
    monkeypatch.setenv("TAVILY_API_KEY", "a-real-configured-tavily-key")
    monkeypatch.setenv("GROQ_API_KEY", "a-real-configured-groq-key")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/career-digest", headers={"X-Internal-Secret": "a-real-configured-secret"})
        assert response.status_code == 200
        assert response.json() == {
            "applications_scanned": 1,
            "applications_failed": 0,
            "digests_compiled": 1,
            "outcome_counts": {"ALREADY_DIGESTED": 0, "DIGESTED": 1},
        }
    finally:
        get_settings.cache_clear()


# --- POST /internal/briefing (Phase 2, DEC-163) ---


def test_briefing_route_is_401_when_no_internal_secret_is_configured_at_all(monkeypatch):
    monkeypatch.delenv("INTERNAL_DRAIN_SECRET", raising=False)
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/briefing")
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_briefing_route_is_401_with_a_real_configured_secret_but_the_wrong_header_value(monkeypatch):
    monkeypatch.setenv("INTERNAL_DRAIN_SECRET", "a-real-configured-secret")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/briefing", headers={"X-Internal-Secret": "not-the-real-secret"})
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_briefing_route_real_secret_and_matching_header_reaches_the_real_route_wiring(monkeypatch):
    """Proves this route's own real auth dependency and real response
    mapping, WITHOUT a real, unscoped call to `run_briefing()` -- the
    same real safety precedent every other `/internal/*` route test in
    this file already established. That function's own real, deep
    composition logic is covered directly and safely in `test_briefing.
    py`, scoped to real, test-owned user_ids only."""
    from quorum_backend.features.briefing import BriefingResult

    # REAL, DISCLOSED, `QUORUM_FINAL_COMPLETION_PLAN.md` SESSION 9
    # (`DEC-176`): `_fake_run_briefing` now accepts (and ignores) the
    # real `firebase_project_id`/`firebase_service_account_json` kwargs
    # `main.py`'s own real route now passes through -- this test's own
    # real point is the route's auth/response-mapping wiring, never a
    # real assertion about what it passes to `run_briefing()` itself
    # (that real wiring is covered directly in `test_briefing.py`).
    async def _fake_run_briefing(pool, **_kwargs):
        return BriefingResult(
            users_scanned=3, users_failed=0, users_with_pending_actions=1, users_with_active_negotiations=1, users_notified=0,
        )

    monkeypatch.setattr("quorum_backend.main.run_briefing", _fake_run_briefing)
    monkeypatch.setenv("INTERNAL_DRAIN_SECRET", "a-real-configured-secret")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/briefing", headers={"X-Internal-Secret": "a-real-configured-secret"})
        assert response.status_code == 200
        assert response.json() == {
            "users_scanned": 3,
            "users_failed": 0,
            "users_with_pending_actions": 1,
            "users_with_active_negotiations": 1,
            "users_notified": 0,
        }
    finally:
        get_settings.cache_clear()


# --- POST /internal/follow-up (Phase 2, DEC-163) ---


def test_follow_up_route_is_401_when_no_internal_secret_is_configured_at_all(monkeypatch):
    monkeypatch.delenv("INTERNAL_DRAIN_SECRET", raising=False)
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/follow-up")
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_follow_up_route_is_401_with_a_real_configured_secret_but_the_wrong_header_value(monkeypatch):
    monkeypatch.setenv("INTERNAL_DRAIN_SECRET", "a-real-configured-secret")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/follow-up", headers={"X-Internal-Secret": "not-the-real-secret"})
        assert response.status_code == 401
    finally:
        get_settings.cache_clear()


def test_follow_up_route_real_secret_and_matching_header_reaches_the_real_route_wiring(monkeypatch):
    """Proves this route's own real auth dependency and real response
    mapping, WITHOUT a real, unscoped call to `run_follow_up()` -- the
    same real safety precedent every other `/internal/*` route test in
    this file already established. That function's own real, deep
    detection logic is covered directly and safely in `test_follow_up.
    py`, scoped to real, test-owned user_ids only. `action_taken` is
    asserted `False` here too -- see `features/follow_up.py`'s own
    top-of-file docstring for why this route deliberately takes no real
    action on what it finds, this phase."""
    from quorum_backend.features.follow_up import FollowUpResult

    async def _fake_run_follow_up(pool):
        return FollowUpResult(
            users_scanned=3, users_failed=0, users_with_stale_messages=1, stale_messages_detected=2,
        )

    monkeypatch.setattr("quorum_backend.main.run_follow_up", _fake_run_follow_up)
    monkeypatch.setenv("INTERNAL_DRAIN_SECRET", "a-real-configured-secret")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/internal/follow-up", headers={"X-Internal-Secret": "a-real-configured-secret"})
        assert response.status_code == 200
        assert response.json() == {
            "users_scanned": 3,
            "users_failed": 0,
            "users_with_stale_messages": 1,
            "stale_messages_detected": 2,
            "action_taken": False,
        }
    finally:
        get_settings.cache_clear()


# --- _quick_capture_result_to_dict: pure, no live model needed ---


def test_quick_capture_result_to_dict_serializes_every_field_on_the_dataclass():
    """THE REAL REGRESSION GUARD for the `DEC-189` bug, and the reason
    it is structural rather than a list of expected keys.

    `_quick_capture_result_to_dict()` silently omitted `email_recipient`
    and `email_action` while serializing all 16 of their siblings. The
    backend genuinely computed both. Every real email-domain capture
    therefore reached the client as `domain: "email"` with every email
    field null -- a confirmed direct cause of the real user-reported
    symptom "I never saw the app do real-time Gmail drafting."

    It survived because the ONLY tests exercising this function were
    live end-to-end ones that depend on a real Gemini extraction call,
    so they skip or fail for unrelated external reasons and nobody
    noticed the shape was wrong. This test needs no model, no network
    and no database.

    Asserting against `dataclasses.fields()` rather than a hardcoded
    key list is deliberate: it means ADDING a field to
    `QuickCaptureResult` and forgetting the serializer fails here
    immediately, which is exactly the mistake that was made. A
    hardcoded list would have to be updated by the same person making
    the same omission, and would not have caught this."""
    import dataclasses

    from quorum_backend.features.quick_capture import QuickCaptureResult
    from quorum_backend.main import _quick_capture_result_to_dict

    result = QuickCaptureResult(
        executed=False,
        decision="approve",
        stakes="S3",
        domain="email",
        operation="create",
        email_recipient="someone@example.com",
        email_action="send_email",
    )

    serialized = _quick_capture_result_to_dict(result)
    declared = {f.name for f in dataclasses.fields(QuickCaptureResult)}

    missing = declared - set(serialized)
    assert not missing, f"fields computed by the backend but dropped at the HTTP boundary: {sorted(missing)}"

    extra = set(serialized) - declared
    assert not extra, f"serializer invents keys with no backing field: {sorted(extra)}"


def test_quick_capture_result_to_dict_carries_the_real_email_fields_through():
    """The specific values, not just the key presence -- a serializer
    that emitted the keys as hardcoded `None` would pass the
    exhaustiveness test above while reproducing the original defect
    exactly."""
    from quorum_backend.features.quick_capture import QuickCaptureResult
    from quorum_backend.main import _quick_capture_result_to_dict

    serialized = _quick_capture_result_to_dict(
        QuickCaptureResult(
            executed=False,
            decision="approve",
            stakes="S3",
            domain="email",
            operation="create",
            email_recipient="sarah@example.com",
            email_action="send_email",
        )
    )

    assert serialized["email_recipient"] == "sarah@example.com"
    assert serialized["email_action"] == "send_email"
    assert serialized["domain"] == "email"


def test_quick_capture_result_to_dict_returns_json_serializable_output():
    """`findings`/`objections` are real Pydantic models and must already
    be dumped to plain JSON types by the time they leave this function
    -- FastAPI returns this dict directly."""
    from quorum_backend.features.quick_capture import QuickCaptureResult
    from quorum_backend.main import _quick_capture_result_to_dict

    serialized = _quick_capture_result_to_dict(
        QuickCaptureResult(executed=True, decision="approve", stakes="S0", domain="tasks", operation="create")
    )
    json.dumps(serialized)  # must not raise


# --- GET /agents (`DEC-192`, product rebuild Block D) ---


def test_agents_endpoint_requires_real_auth():
    with TestClient(app) as client:
        response = client.get("/agents")
    assert response.status_code == 401


async def test_agents_endpoint_returns_all_five_real_domain_agents_even_with_zero_activity(pool, provisioned_users):
    headers, _ = await _provisioned_auth_header(pool, provisioned_users)
    with TestClient(app) as client:
        response = client.get("/agents", headers=headers)

    assert response.status_code == 200
    body = response.json()
    domains = {agent["domain"] for agent in body["agents"]}
    assert domains == {"email", "calendar", "tasks", "finance", "career"}
    # A genuinely inactive agent renders as an honest zero, never absent.
    for agent in body["agents"]:
        assert agent["lifetime_actions"] == 0
        assert agent["last_activity"] is None
        assert agent["success_rate"] is None


async def test_agents_endpoint_reflects_a_real_resolved_action(pool, provisioned_users):
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    proposal_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)",
        proposal_id, "create_task", "S1", "{}", "approve", "approved_unchanged",
        str(proposal_id), uuid.UUID(internal_user_id), datetime.now(timezone.utc),
    )

    with TestClient(app) as client:
        response = client.get("/agents", headers=headers)

    body = response.json()
    tasks = next(a for a in body["agents"] if a["domain"] == "tasks")
    assert tasks["lifetime_actions"] == 1
    assert tasks["success_count"] == 1
    assert tasks["success_rate"] == 1.0
    assert tasks["last_activity"] is not None


# --- GET /email/overview (`DEC-199`, product rebuild) ---


def test_email_overview_endpoint_requires_real_auth():
    with TestClient(app) as client:
        response = client.get("/email/overview")
    assert response.status_code == 401


async def test_email_overview_endpoint_is_honestly_empty_for_a_real_user_with_no_email_activity(pool, provisioned_users):
    headers, _ = await _provisioned_auth_header(pool, provisioned_users)
    with TestClient(app) as client:
        response = client.get("/email/overview", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["drafts"] == []
    assert body["sent_history"] == []
    assert body["known_recipients"] == []


async def test_email_overview_endpoint_reflects_a_real_approved_draft_and_a_real_sent_message(pool, provisioned_users):
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    proposal_id = uuid.uuid4()
    payload = {"to": "sarah@example.com", "subject": "Re: proposal", "body": "a real body"}
    artifact = {"draft_id": "draft-xyz"}
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at, artifact) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9, $10::jsonb)",
        proposal_id, "create_email_draft", "S1", json.dumps(payload), "approve", "approved_unchanged",
        str(proposal_id), uuid.UUID(internal_user_id), datetime.now(timezone.utc), json.dumps(artifact),
    )
    from quorum_backend.features.waiting_on import record_sent_message
    await record_sent_message(
        pool, user_id=internal_user_id, message_id="m1", thread_id="t1", recipient="bob@example.com",
        subject="a real sent subject", sent_at=datetime.now(timezone.utc),
    )

    with TestClient(app) as client:
        response = client.get("/email/overview", headers=headers)

    body = response.json()
    assert len(body["drafts"]) == 1
    assert body["drafts"][0]["recipient"] == "sarah@example.com"
    assert body["drafts"][0]["draft_id"] == "draft-xyz"
    assert len(body["sent_history"]) == 1
    assert body["sent_history"][0]["recipient"] == "bob@example.com"
    assert body["sent_history"][0]["replied_at"] is None
    assert len(body["known_recipients"]) == 1
    assert body["known_recipients"][0]["recipient"] == "bob@example.com"
    assert body["known_recipients"][0]["message_count"] == 1


# --- PUT /finance/budget (`DEC-200`, product rebuild) ---


def test_update_budget_endpoint_requires_real_auth():
    with TestClient(app) as client:
        response = client.put("/finance/budget", json={"amount": 60000.0})
    assert response.status_code == 401


async def test_update_budget_endpoint_rejects_a_non_positive_amount_with_a_real_502_not_a_500(pool, provisioned_users):
    headers, _ = await _provisioned_auth_header(pool, provisioned_users)
    with TestClient(app) as client:
        response = client.put("/finance/budget", json={"amount": 0}, headers=headers)
    assert response.status_code == 502


async def test_update_budget_endpoint_is_real_and_live_sets_a_real_new_budget_ceiling_end_to_end(pool, provisioned_users):
    """`UPDATE_BUDGET` is real `Stakes.S2` -- unlike `POST /applications`/
    `POST /interviews`'s own `S1` precedent, the real Judge genuinely
    runs here, which needs a real, live, configured `GEMINI_API_KEY`
    and spends real, shared daily quota (the same real, disclosed cost
    `test_capture_action_from_text_a_real_live_update_budget_reaches_
    the_real_gemini_judge_and_never_the_critic` already accepts for
    the identical real action type reached through free text)."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    new_limit = 72345.0

    try:
        with TestClient(app) as client:
            response = client.put(
                "/finance/budget",
                json={"amount": new_limit, "category": "Groceries and rent"},
                headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["stakes"] == "S2"
        assert body["domain"] == "finance"
        assert body["executed"] is True

        row = await pool.fetchrow("SELECT monthly_budget_limit FROM users WHERE user_id = $1", uuid.UUID(internal_user_id))
        assert row["monthly_budget_limit"] == new_limit
    finally:
        await pool.execute("UPDATE users SET monthly_budget_limit = 50000.0 WHERE user_id = $1", uuid.UUID(internal_user_id))
        await pool.execute("DELETE FROM action_events WHERE user_id = $1", uuid.UUID(internal_user_id))


async def test_update_budget_endpoint_a_real_default_category_is_used_when_none_is_supplied(pool, provisioned_users):
    """`category` is genuinely optional on this real, structured route
    -- a direct "set the budget" control has no real spending category
    of its own, unlike free-text capture. Confirms the real, honest
    default (`"Monthly budget"`, never a fabricated spend category)
    satisfies `validate_and_build_finance_proposal()`'s own real,
    non-empty-string requirement without the caller supplying one."""
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)

    try:
        with TestClient(app) as client:
            response = client.put("/finance/budget", json={"amount": 61000.0}, headers=headers)

        assert response.status_code == 200
        assert response.json()["executed"] is True
    finally:
        await pool.execute("UPDATE users SET monthly_budget_limit = 50000.0 WHERE user_id = $1", uuid.UUID(internal_user_id))
        await pool.execute("DELETE FROM action_events WHERE user_id = $1", uuid.UUID(internal_user_id))


# --- GET /gate/validators (`DEC-193`, product rebuild Block E) ---


def test_gate_validators_endpoint_requires_real_auth():
    with TestClient(app) as client:
        response = client.get("/gate/validators")
    assert response.status_code == 401


def test_gate_validators_endpoint_returns_all_nine_real_validators():
    with TestClient(app) as client:
        response = client.get("/gate/validators", headers=_auth_header())
    assert response.status_code == 200
    body = response.json()
    assert len(body["validators"]) == 9
    names = {v["name"] for v in body["validators"]}
    assert "ProvenanceCheck" in names
    assert "DeadlineConflictCheck" in names
    wired = {v["name"] for v in body["validators"] if v["wired"]}
    assert wired == {"ProvenanceCheck", "DeadlineConflictCheck", "RecipientCheck"}


# --- GET /gate/stats (`DEC-193`, product rebuild Block E) ---


def test_gate_stats_endpoint_requires_real_auth():
    with TestClient(app) as client:
        response = client.get("/gate/stats")
    assert response.status_code == 401


async def test_gate_stats_endpoint_returns_honest_zeros_for_a_real_user_with_no_activity(pool, provisioned_users):
    headers, _ = await _provisioned_auth_header(pool, provisioned_users)
    with TestClient(app) as client:
        response = client.get("/gate/stats", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total_resolved"] == 0
    assert body["stakes_counts"] == {}
    assert body["catch_rate"] is None
    # REAL, DISCLOSED FIX (`DEC-194`): this assertion used to also
    # require `quota_used <= quota_limit` -- wrong, found live by this
    # exact test under real load (a long, multi-hour full-suite day
    # with many real Gemini calls genuinely pushed the shared counter
    # to 21 against a limit of 20). `reserve_gemini_quota_slot()`'s own
    # docstring already discloses why this is possible and accepted:
    # a rejected reservation's own real DECR-on-reject can itself fail
    # (a transient real Upstash call), leaving the counter inflated
    # until the next real Pacific-time reset -- "still correctly
    # rejecting every further real attempt either way," per that
    # function's own words, just not bounded at exactly `daily_limit`
    # for display. Only non-negativity is a genuine invariant here.
    if body["quota_used"] is not None:
        assert body["quota_used"] >= 0


async def test_gate_stats_endpoint_reflects_a_real_resolved_action(pool, provisioned_users):
    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    proposal_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id, resolved_at) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)",
        proposal_id, "create_task", "S1", "{}", "approve", "approved_unchanged",
        str(proposal_id), uuid.UUID(internal_user_id), datetime.now(timezone.utc),
    )

    with TestClient(app) as client:
        response = client.get("/gate/stats", headers=headers)

    body = response.json()
    assert body["total_resolved"] == 1
    assert body["stakes_counts"] == {"S1": 1}
    assert body["success_count"] == 1
    assert body["catch_rate"] == 0.0


# --- GET /connections (`DEC-198`, product rebuild) ---


def test_connections_endpoint_requires_real_auth():
    with TestClient(app) as client:
        response = client.get("/connections")
    assert response.status_code == 401


async def test_connections_endpoint_is_honestly_not_connected_for_a_real_user_who_never_granted_google_access(
    pool, provisioned_users
):
    headers, _ = await _provisioned_auth_header(pool, provisioned_users)
    with TestClient(app) as client:
        response = client.get("/connections", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is False
    assert body["granted_scopes"] == []
    assert body["last_updated_at"] is None
    assert body["token_refreshable"] is None


async def test_connections_endpoint_reflects_a_real_stored_grant_and_its_real_scopes(pool, provisioned_users):
    from cryptography.fernet import Fernet

    from quorum_backend.auth.google_token_store import store_google_tokens
    from quorum_backend.core.config import get_settings

    headers, internal_user_id = await _provisioned_auth_header(pool, provisioned_users)
    settings = get_settings()
    key = settings.google_token_encryption_key or Fernet.generate_key().decode()
    # Deliberately EXPIRED -- this endpoint checks refreshability live,
    # never from the stored expiry alone (see `connection_health.py`'s
    # own top-of-file docstring); a far-from-expiry token here would
    # return the stored access_token with no real refresh attempt at
    # all, proving nothing about this endpoint's own honest `False`
    # path below.
    await store_google_tokens(
        pool, internal_user_id=internal_user_id, access_token="a-real-access-token",
        refresh_token="a-real-refresh-token", access_token_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        granted_scopes="openid email https://www.googleapis.com/auth/gmail.readonly", encryption_key=key,
    )

    with TestClient(app) as client:
        response = client.get("/connections", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is True
    assert body["granted_scopes"] == ["openid", "email", "https://www.googleapis.com/auth/gmail.readonly"]
    assert body["last_updated_at"] is not None
    # client_id/client_secret in this deployment's real `.env` are real,
    # live Google credentials, but this grant's own real refresh_token
    # is fabricated by this test -- a genuine live refresh attempt
    # against Google's real endpoint correctly fails, confirming the
    # endpoint's own honest `False` path, not a 500.
    assert body["token_refreshable"] is False
