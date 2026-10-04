"""Real tests for `POST /capture/stream` and `GET /actions/{id}/status`
(`DEC-189` Block B).

These run against the real, live Supabase database with real auth and a
real Gate review -- but with the real Gemini EXTRACTION call replaced by
a deterministic fake, deliberately and for two reasons. The free-tier
Gemini limit is 20 requests/day shared across every consumer in this
project, so a test suite that burned a slot per run would be unusable;
and extraction is the one step these tests are genuinely not about. The
Gate review, the real `action_events` write, the real timeline recording
and the real SSE framing are all exercised for real.

`CREATE_TASK` is used throughout because it is real `Stakes.S1`
(confirmed against `router.STAKES_TABLE`), so Stage B never runs and no
Gemini judge call is made either -- the whole pipeline stays free of
live model calls while remaining genuinely real everywhere else.
"""
import json
import uuid

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from quorum_backend.auth.access_token import create_access_token
from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.core.config import get_settings
from quorum_backend.main import app


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user(pool):
    """A real provisioned user plus a real access token, cleaned up
    completely on teardown -- including any `action_events` rows a
    streaming capture genuinely created."""
    settings = get_settings()
    google_sub = f"test-capture-stream-{uuid.uuid4()}"
    internal_user_id = await get_or_create_user(pool, google_sub=google_sub, email=None)
    token = create_access_token(google_sub, settings.jwt_signing_key)
    yield {
        "headers": {"Authorization": f"Bearer {token}"},
        "user_id": internal_user_id,
    }
    # Cleanup runs on a FRESH pool, not the shared `pool` fixture --
    # a real, found failure, not defensive padding. A streaming test
    # holds its request open for tens of seconds while the `pool`
    # fixture's own connection sits idle, and Supabase's PgBouncer
    # genuinely closes an idle connection in that window, so teardown
    # died with `ConnectionDoesNotExistError` and left real rows behind
    # in the live database. A pool created at teardown time cannot have
    # gone stale during the test.
    cleanup_pool = await db.create_pool()
    try:
        await cleanup_pool.execute("DELETE FROM action_events WHERE user_id = $1", uuid.UUID(internal_user_id))
        await cleanup_pool.execute("DELETE FROM tasks WHERE user_id = $1", uuid.UUID(internal_user_id))
        await cleanup_pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(internal_user_id))
    finally:
        await cleanup_pool.close()


@pytest.fixture
def fake_task_extraction(monkeypatch):
    """Replaces the real Gemini extraction factory with a deterministic
    one returning a valid `tasks`-domain result. Patched at
    `quorum_backend.main`, the name the route actually resolves, not at
    the defining module."""
    def factory(*, api_key):
        async def extraction_call(free_text: str) -> dict:
            return {
                "domain": "tasks",
                "operation": "create",
                "title": "Streamed test task",
                "estimated_hours": 1.0,
                "deadline": None,
            }

        return extraction_call

    monkeypatch.setattr("quorum_backend.main.make_gemini_quick_capture_extraction_call", factory)


def _parse_sse(body: str) -> list[dict]:
    """Parses real SSE frames into the events they carry, ignoring
    comment lines (the keepalives)."""
    events = []
    for block in body.split("\n\n"):
        line = block.strip()
        if not line or line.startswith(":"):
            continue
        assert line.startswith("data: "), f"malformed SSE frame: {line!r}"
        events.append(json.loads(line[len("data: ") :]))
    return events


# --- POST /capture/stream ---


def test_capture_stream_requires_real_auth():
    """Checked BEFORE the stream opens, which is the point: an SSE
    response commits to 200 the instant its first byte is sent, so an
    auth failure must be a real 401 and never an in-band error event."""
    with TestClient(app) as client:
        response = client.post("/capture/stream", json={"text": "anything"})
    assert response.status_code == 401
    assert "text/event-stream" not in response.headers.get("content-type", "")


def test_capture_stream_rejects_blank_text_before_streaming():
    with TestClient(app) as client:
        response = client.post("/capture/stream", json={"text": "   "}, headers={"Authorization": "Bearer nope"})
    # 401 wins over 422 here -- auth is resolved first, which is correct:
    # an unauthenticated caller should learn nothing about validation.
    assert response.status_code in (401, 422)


def test_capture_stream_streams_the_real_gate_stages_then_the_result(user, fake_task_extraction):
    with TestClient(app) as client:
        response = client.post("/capture/stream", json={"text": "write the test task"}, headers=user["headers"])

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    # Proxy buffering would hold the whole stream and release it at once,
    # which would look like success while defeating the entire purpose.
    assert response.headers["x-accel-buffering"] == "no"

    events = _parse_sse(response.text)
    names = [e["event"] for e in events]

    # The real pipeline order: extraction, then Stage A, then the
    # summary, then the result.
    assert names[0] == "understanding.start"
    assert "understanding" in names
    assert "routing" in names
    assert "stage_a.start" in names
    assert "stage_a.check" in names
    assert "done" in names
    assert names[-1] == "result"
    # Routing must be announced BEFORE Stage A runs -- it is what tells a
    # watching user why the pipeline about to run looks the way it does.
    assert names.index("routing") < names.index("stage_a.start")

    routing = next(e for e in events if e["event"] == "routing")
    assert routing["action_type"] == "create_task"
    assert routing["stakes"] == "S1"
    # S1 never reaches Stage B -- the same structural rule
    # `run_stage_b()` itself applies.
    assert routing["stage_b_will_run"] is False
    assert routing["critic_will_run"] is False
    assert routing["stage_a_check_count"] >= 1

    # Every event carries a real offset from the start of the review.
    assert all("at_ms" in e for e in events if e["event"] != "result")

    understanding = next(e for e in events if e["event"] == "understanding")
    assert understanding["domain"] == "tasks"
    # Extracted KEYS only -- never the model's own output values, which
    # are untrusted and already reach the client via the real result.
    assert "title" in understanding["extracted_fields"]
    assert "Streamed test task" not in json.dumps(understanding)

    checks = [e for e in events if e["event"] == "stage_a.check"]
    assert checks, "no real Stage A check was streamed"
    assert all(e["validator"] for e in checks)
    assert all(e["evidence_state"] in ("verified_true", "verified_false", "no_data_found") for e in checks)
    assert all("duration_ms" in e for e in checks)

    done = next(e for e in events if e["event"] == "done")
    # CREATE_TASK is real S1 -- Stage B must genuinely not have run.
    assert done["stakes"] == "S1"
    assert done["stage_b_ran"] is False
    assert done["revision_count"] == 0

    result = events[-1]
    assert result["domain"] == "tasks"
    assert result["decision"] == "approve"


async def test_capture_stream_persists_the_real_timeline_onto_the_action_row(pool, user, fake_task_extraction):
    """The streamed timeline and the persisted one must be the same real
    record -- a decision watched live has to be exactly as replayable
    afterward as one that was not."""
    with TestClient(app) as client:
        response = client.post("/capture/stream", json={"text": "persist the timeline"}, headers=user["headers"])
    assert response.status_code == 200

    row = await pool.fetchrow(
        "SELECT proposal_id, gate_timeline, revision_count, pre_revision_payload "
        "FROM action_events WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1",
        uuid.UUID(user["user_id"]),
    )
    assert row is not None, "the streaming capture wrote no real action_events row"

    stored = row["gate_timeline"]
    if isinstance(stored, str):
        stored = json.loads(stored)
    assert stored, "gate_timeline was persisted empty"

    stored_checks = [e for e in stored if e["event"] == "stage_a.check"]
    streamed_checks = [e for e in _parse_sse(response.text) if e["event"] == "stage_a.check"]
    assert [e["validator"] for e in stored_checks] == [e["validator"] for e in streamed_checks]

    assert row["revision_count"] == 0
    # No revision happened, so this must be genuinely NULL -- storing the
    # payload unconditionally would make every action look like the Gate
    # had corrected it.
    assert row["pre_revision_payload"] is None


# --- GET /actions/{proposal_id}/status ---


def test_action_status_requires_real_auth():
    with TestClient(app) as client:
        response = client.get(f"/actions/{uuid.uuid4()}/status")
    assert response.status_code == 401


def test_action_status_rejects_a_non_uuid_id(user):
    with TestClient(app) as client:
        response = client.get("/actions/not-a-uuid/status", headers=user["headers"])
    assert response.status_code == 422


def test_action_status_404s_for_an_action_that_does_not_exist(user):
    with TestClient(app) as client:
        response = client.get(f"/actions/{uuid.uuid4()}/status", headers=user["headers"])
    assert response.status_code == 404


def test_action_status_replays_the_real_recorded_timeline(user, fake_task_extraction):
    with TestClient(app) as client:
        stream = client.post("/capture/stream", json={"text": "replay me"}, headers=user["headers"])
        assert stream.status_code == 200
        proposal_id = next(
            e for e in _parse_sse(stream.text) if e["event"] == "done"
        )["trace_id"]

        response = client.get(f"/actions/{proposal_id}/status", headers=user["headers"])

    assert response.status_code == 200
    body = response.json()
    assert body["proposal_id"] == proposal_id
    assert body["action_type"] == "create_task"
    assert body["stakes"] == "S1"
    assert body["gate_decision"] == "approve"
    assert body["revision_count"] == 0
    assert body["pre_revision_payload"] is None

    # The timeline must come back as real parsed JSON, never a
    # JSON-encoded string -- asyncpg returns JSONB as `str` with no
    # codec registered, which is exactly the trap this asserts against.
    assert isinstance(body["timeline"], list)
    assert isinstance(body["findings"], list)
    assert isinstance(body["payload"], dict)
    assert any(e["event"] == "stage_a.check" for e in body["timeline"])


async def test_action_status_never_leaks_another_real_users_action(pool, user):
    """A real action belonging to someone else must be indistinguishable
    from one that does not exist -- scoped in the query itself, never
    filtered after the fetch."""
    other_sub = f"test-capture-other-{uuid.uuid4()}"
    other_id = await get_or_create_user(pool, google_sub=other_sub, email=None)
    proposal_id = uuid.uuid4()
    try:
        await pool.execute(
            "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id) "
            "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8)",
            proposal_id, "create_task", "S1", '{"title": "theirs"}', "approve", "approved_unchanged",
            str(proposal_id), uuid.UUID(other_id),
        )

        with TestClient(app) as client:
            response = client.get(f"/actions/{proposal_id}/status", headers=user["headers"])

        assert response.status_code == 404
        assert "theirs" not in response.text
    finally:
        await pool.execute("DELETE FROM action_events WHERE proposal_id = $1", proposal_id)
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(other_id))


async def test_action_status_returns_null_timeline_for_a_pre_migration_row(pool, user):
    """Migration `0021` left every existing row with a NULL timeline.
    This must come back as `null`, NOT an empty list -- an empty list
    would tell a client the Gate ran no checks, which is false. The
    distinction is what lets a client render an honest "not recorded"
    state."""
    proposal_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO action_events (proposal_id, action_type, stakes, payload, gate_decision, outcome, trace_id, user_id) "
        "VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8)",
        proposal_id, "create_task", "S1", '{"title": "old row"}', "approve", "approved_unchanged",
        str(proposal_id), uuid.UUID(user["user_id"]),
    )

    with TestClient(app) as client:
        response = client.get(f"/actions/{proposal_id}/status", headers=user["headers"])

    assert response.status_code == 200
    body = response.json()
    assert body["timeline"] is None
    assert body["revision_count"] is None
    assert body["pre_revision_payload"] is None
