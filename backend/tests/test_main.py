"""Real tests for main.py -- confirms core/config.py is genuinely
consumed at real app startup, not just an unreferenced file, and (Batch
10 Phase 3) that the real auth routes and the real Bearer-auth gate on
/trust_digest genuinely work end to end against the real, live database.
"""
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
        assert set(result.keys()) == {"scenario_id", "expected", "actual", "passed"}
        assert result["passed"] is True
        assert result["expected"] == result["actual"]

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


def test_trust_digest_endpoint_is_real_and_live_not_mocked_with_a_real_valid_token():
    """Real, end-to-end: the real lifespan creates a real DB pool
    against the real, live Supabase database (DEC-098), and this
    request genuinely round-trips through it once a real, valid access
    token is presented. Asserts shape and types only, never specific
    counts -- real production data changes as this project actually
    gets used, and a value-based assertion here would be exactly the
    stale-restated-number drift pattern CLAUDE.md warns against."""
    with TestClient(app) as client:
        response = client.get("/trust_digest", headers=_auth_header())

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
    assert location.startswith("com.quorum.quorum_mobile://oauth2redirect?")
    assert "code=real-test-code" in location
    assert "state=real-test-state" in location


def test_auth_callback_forwards_a_real_google_error_without_inventing_a_code():
    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/auth/callback", params={"error": "access_denied"})
    assert response.status_code in (302, 307)
    location = response.headers["location"]
    assert location.startswith("com.quorum.quorum_mobile://oauth2redirect?")
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
    session), inserts one real task, calls `DELETE /account` with a
    real, valid access token, then confirms -- against the real, live
    database, not just the response body -- that the real task is
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
    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, $5, $6)",
        task_id,
        uuid.UUID(internal_user_id),
        "A real task, about to be really, permanently deleted",
        1.0,
        None,
        "open",
    )

    with TestClient(app) as client:
        response = client.delete("/account", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == internal_user_id
    assert body["sessions_revoked"] is True
    # 1 real task + 1 real users row -- the real, honest count, not a
    # placeholder.
    assert body["postgres_rows_deleted"] == 2
    assert body["vector_embeddings_deleted"] == 0
    assert body["memories_deleted"] == 0
    assert body["oauth_tokens_revoked"] == 0

    # Real, live confirmation against the real database, not just a
    # trusted response body.
    assert await pool.fetchrow("SELECT 1 FROM tasks WHERE task_id = $1", task_id) is None
    assert await pool.fetchrow("SELECT 1 FROM users WHERE user_id = $1", uuid.UUID(internal_user_id)) is None
    with pytest.raises(TokenRevoked):
        await rotate_refresh_token(raw_refresh, revocation_store)


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
    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, $5, $6)",
        bystander_task,
        uuid.UUID(bystander_id),
        "Bystander's real, untouched task",
        1.0,
        None,
        "open",
    )

    try:
        with TestClient(app) as client:
            response = client.delete("/account", headers={"Authorization": f"Bearer {victim_access_token}"})
        assert response.status_code == 200
        # The real, deleted identity really is the victim's own internal
        # UUID -- never the bystander's, confirming the route resolved
        # and acted on the correct real account.
        assert response.json()["user_id"] == victim_id

        # The bystander's real task, real users row, and real session
        # all survive completely untouched.
        assert await pool.fetchrow("SELECT 1 FROM tasks WHERE task_id = $1", bystander_task) is not None
        assert await pool.fetchrow("SELECT 1 FROM users WHERE user_id = $1", uuid.UUID(bystander_id)) is not None
        # A real, live proof the bystander's own session still rotates
        # -- never revoked by someone else's account deletion.
        await rotate_refresh_token(bystander_refresh, revocation_store)
    finally:
        await pool.execute("DELETE FROM tasks WHERE task_id = $1", bystander_task)
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
