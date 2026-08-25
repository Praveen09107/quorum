"""Real tests for features/negotiation_detail_backfill.py (Phase 2,
DEC-134) -- real, live-database integration tests, mirroring test_
deadline_watch.py/test_spend_alert.py's own established real pattern.

Two real/fake boundaries, matching test_negotiation_gemini_calls.py's
own already-established split:
- Most tests below never reach a real Gemini call at all -- every path
  that returns UNKNOWN_TRIGGER_SOURCE or SITUATION_RESOLVED short-
  circuits inside `negotiation/subgraph.py`'s own `scan` node, before
  `generate_positions_node` is ever reached, so these are real, live-
  database tests with zero real network dependency.
- `test_generate_detail_..._a_real_genuine_conflict_produces_real_
  detailed_output` uses a monkeypatched httpx client (deterministic,
  network-independent, same technique test_negotiation_gemini_calls.py
  already established) to exercise the full real pipeline -- state
  rebuild, subgraph, atomic persist -- without spending real Gemini
  quota on every CI run.
- `test_generate_detail_for_one_negotiation_a_real_live_gemini_backed_
  conflict_is_genuinely_detailed` is the one real, live, skippable-
  without-a-key test that actually proves the real Gemini integration
  works, per CLAUDE.md Rule 5.
"""
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.core.config import get_settings
from quorum_backend.features.negotiation_detail_backfill import (
    BackfillOutcome,
    _persist_detail_if_still_bare,
    generate_detail_for_one_negotiation,
    run_negotiation_detail_backfill,
)

_HAS_REAL_KEY = get_settings().gemini_api_key is not None


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-negotiation-detail-backfill-{uuid.uuid4()}"
    uid = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield uid
    await pool.execute("DELETE FROM negotiations WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM tasks WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM expenses WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(uid))


async def _seed_bare_negotiation(pool, *, user_id: str, trigger_source: str | None) -> str:
    negotiation_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO negotiations (negotiation_id, user_id, conflicted_domains, started_at, trigger_source) "
        "VALUES ($1, $2, $3, $4, $5)",
        negotiation_id, uuid.UUID(user_id), ["finance", "tasks"], datetime.now(timezone.utc), trigger_source,
    )
    return str(negotiation_id)


async def _seed_task(pool, *, user_id: str, hours: float, deadline_offset_days: int) -> None:
    now = datetime.now(timezone.utc)
    await pool.execute(
        "INSERT INTO tasks (task_id, user_id, title, estimated_hours, deadline, status) VALUES ($1, $2, $3, $4, $5, $6)",
        uuid.uuid4(), uuid.UUID(user_id), "real test task", hours, now + timedelta(days=deadline_offset_days), "open",
    )


async def _seed_expense(pool, *, user_id: str, payee: str, amount: float, occurred_days_ago: int) -> None:
    now = datetime.now(timezone.utc)
    await pool.execute(
        "INSERT INTO expenses (expense_id, user_id, payee, amount, occurred_at, source) VALUES ($1, $2, $3, $4, $5, $6)",
        uuid.uuid4(), uuid.UUID(user_id), payee, amount, now - timedelta(days=occurred_days_ago), "manual",
    )


async def _seed_real_recurring_subscription(pool, *, user_id: str, payee: str, amount: float) -> None:
    for offset in (60, 30, 0):
        await _seed_expense(pool, user_id=user_id, payee=payee, amount=amount, occurred_days_ago=offset)


# --- Dispatch/skip paths -- zero real Gemini calls, real database only ---


async def test_generate_detail_for_one_negotiation_returns_unknown_trigger_source_for_an_unrecognized_source(pool, user_id):
    negotiation_id = await _seed_bare_negotiation(pool, user_id=user_id, trigger_source=None)

    outcome = await generate_detail_for_one_negotiation(
        pool, negotiation_id=negotiation_id, user_id=user_id, trigger_source=None, api_key="unused"
    )

    assert outcome is BackfillOutcome.UNKNOWN_TRIGGER_SOURCE
    row = await pool.fetchrow("SELECT options FROM negotiations WHERE negotiation_id = $1", uuid.UUID(negotiation_id))
    assert row["options"] is None  # never touched


async def test_generate_detail_for_one_negotiation_a_real_deadline_watch_source_with_no_open_task_is_resolved(pool, user_id):
    # No real open task with a future deadline -- the exact precondition
    # deadline_watch.py's own NO_CLAIM outcome encodes.
    negotiation_id = await _seed_bare_negotiation(pool, user_id=user_id, trigger_source="deadline_watch")

    outcome = await generate_detail_for_one_negotiation(
        pool, negotiation_id=negotiation_id, user_id=user_id, trigger_source="deadline_watch", api_key="unused"
    )

    assert outcome is BackfillOutcome.SITUATION_RESOLVED


async def test_generate_detail_for_one_negotiation_a_real_spend_alert_source_with_no_subscription_is_resolved(pool, user_id):
    negotiation_id = await _seed_bare_negotiation(pool, user_id=user_id, trigger_source="spend_alert")

    outcome = await generate_detail_for_one_negotiation(
        pool, negotiation_id=negotiation_id, user_id=user_id, trigger_source="spend_alert", api_key="unused"
    )

    assert outcome is BackfillOutcome.SITUATION_RESOLVED


async def test_generate_detail_for_one_negotiation_a_real_deadline_watch_situation_that_has_since_resolved_itself(pool, user_id):
    """Real regression proof of this module's own re-derive-don't-
    snapshot design: real, current data no longer conflicts (light task,
    light spend), so a fresh re-scan inside the real subgraph's own
    `scan` node short-circuits before any real Gemini call -- proven
    here by passing an `api_key` that would raise if it were ever
    actually used for a real network call."""
    negotiation_id = await _seed_bare_negotiation(pool, user_id=user_id, trigger_source="deadline_watch")
    await _seed_task(pool, user_id=user_id, hours=1.0, deadline_offset_days=5)
    await _seed_expense(pool, user_id=user_id, payee="light", amount=100.0, occurred_days_ago=0)

    outcome = await generate_detail_for_one_negotiation(
        pool, negotiation_id=negotiation_id, user_id=user_id, trigger_source="deadline_watch",
        api_key="never-actually-sent-anywhere",
    )

    assert outcome is BackfillOutcome.SITUATION_RESOLVED
    row = await pool.fetchrow("SELECT options FROM negotiations WHERE negotiation_id = $1", uuid.UUID(negotiation_id))
    assert row["options"] is None


# --- Atomic race guard -- direct, real database proof ---


async def test_persist_detail_if_still_bare_returns_false_when_a_real_row_already_has_options(pool, user_id):
    negotiation_id = await _seed_bare_negotiation(pool, user_id=user_id, trigger_source="deadline_watch")
    await pool.execute(
        "UPDATE negotiations SET options = $1::jsonb WHERE negotiation_id = $2",
        '[{"option_id": "do_nothing", "description": "Do nothing.", "source_domains": []}]',
        uuid.UUID(negotiation_id),
    )

    async with pool.acquire() as conn:
        won = await _persist_detail_if_still_bare(
            conn, negotiation_id=negotiation_id, positions=[], options=[], impact={}
        )

    assert won is False  # a real, already-detailed row is never clobbered


async def test_persist_detail_if_still_bare_returns_true_and_writes_for_a_real_bare_row(pool, user_id):
    from quorum_backend.gate.schemas import NegotiationOption, Position

    negotiation_id = await _seed_bare_negotiation(pool, user_id=user_id, trigger_source="deadline_watch")
    positions = [Position(domain="finance", concern="c", severity_claim="s", proposed_resolution="p")]
    options = [NegotiationOption(option_id="do_nothing", description="Do nothing.", source_domains=[])]

    async with pool.acquire() as conn:
        won = await _persist_detail_if_still_bare(
            conn, negotiation_id=negotiation_id, positions=positions, options=options, impact={}
        )

    assert won is True
    row = await pool.fetchrow("SELECT positions, options FROM negotiations WHERE negotiation_id = $1", uuid.UUID(negotiation_id))
    assert json.loads(row["positions"])[0]["domain"] == "finance"
    assert json.loads(row["options"])[0]["option_id"] == "do_nothing"


# --- Batch entry point -- real database, real per-negotiation isolation ---


async def test_run_negotiation_detail_backfill_scans_exactly_the_real_negotiations_it_is_given(pool, user_id):
    unknown_source_id = await _seed_bare_negotiation(pool, user_id=user_id, trigger_source=None)
    resolved_id = await _seed_bare_negotiation(pool, user_id=user_id, trigger_source="spend_alert")

    result = await run_negotiation_detail_backfill(
        pool, api_key="unused", negotiation_ids=[unknown_source_id, resolved_id]
    )

    assert result.negotiations_scanned == 2
    assert result.negotiations_failed == 0
    assert result.negotiations_detailed == 0
    assert result.outcome_counts["UNKNOWN_TRIGGER_SOURCE"] == 1
    assert result.outcome_counts["SITUATION_RESOLVED"] == 1


async def test_run_negotiation_detail_backfill_a_real_failure_for_one_negotiation_never_blocks_the_rest(pool, user_id):
    """Real regression test for the real bug this session's own test-
    writing found: an earlier version resolved every real
    `negotiation_ids` entry to a `uuid.UUID` in one up-front batch query,
    so a single syntactically-malformed id crashed the WHOLE batch,
    never reaching this loop's own per-item failure isolation at all --
    see `run_negotiation_detail_backfill`'s own docstring for the full
    real account. A genuinely malformed id (`"not-a-real-uuid"`, the
    same real literal `test_deadline_watch.py`'s own equivalent test
    uses) must be tallied as one real failure, never abort the real,
    well-formed negotiation alongside it."""
    good_id = await _seed_bare_negotiation(pool, user_id=user_id, trigger_source=None)

    result = await run_negotiation_detail_backfill(pool, api_key="unused", negotiation_ids=["not-a-real-uuid", good_id])

    assert result.negotiations_failed == 1
    assert result.negotiations_scanned == 1  # only the real, valid negotiation_id counts as genuinely scanned
    assert result.outcome_counts["UNKNOWN_TRIGGER_SOURCE"] == 1


async def test_run_negotiation_detail_backfill_a_real_nonexistent_negotiation_id_is_a_real_tallied_failure(pool, user_id):
    ghost_negotiation_id = str(uuid.uuid4())  # syntactically real, genuinely no real negotiations row
    good_id = await _seed_bare_negotiation(pool, user_id=user_id, trigger_source=None)

    result = await run_negotiation_detail_backfill(
        pool, api_key="unused", negotiation_ids=[ghost_negotiation_id, good_id]
    )

    assert result.negotiations_failed == 1
    assert result.negotiations_scanned == 1


# --- Full pipeline, deterministic (monkeypatched httpx, no real network) ---


class _FakeGeminiResponse:
    def __init__(self, payload: dict):
        self.status_code = 200
        self._payload = payload

    def json(self):
        return {"candidates": [{"content": {"parts": [{"text": json.dumps(self._payload)}]}}]}


class _FakeGeminiClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, *args, **kwargs):
        schema = kwargs["json"]["generationConfig"]["responseSchema"]
        if "concern" in schema["required"]:
            return _FakeGeminiResponse(
                {"concern": "real test concern", "severity_claim": "real test severity", "proposed_resolution": "real test resolution"}
            )
        return _FakeGeminiResponse(
            {
                "options": [
                    {"description": "real option one", "source_domains": ["finance"]},
                    {"description": "real option two", "source_domains": ["tasks"]},
                ]
            }
        )


async def test_generate_detail_for_one_negotiation_a_real_genuine_conflict_produces_real_detailed_output(pool, user_id, monkeypatch):
    monkeypatch.setattr(
        "quorum_backend.negotiation.gemini_calls.httpx.AsyncClient", lambda **kwargs: _FakeGeminiClient()
    )
    negotiation_id = await _seed_bare_negotiation(pool, user_id=user_id, trigger_source="deadline_watch")
    await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)
    await _seed_expense(pool, user_id=user_id, payee="real test payee", amount=30000.0, occurred_days_ago=0)

    outcome = await generate_detail_for_one_negotiation(
        pool, negotiation_id=negotiation_id, user_id=user_id, trigger_source="deadline_watch", api_key="fake-key-never-sent"
    )

    assert outcome is BackfillOutcome.DETAILED
    row = await pool.fetchrow(
        "SELECT positions, options FROM negotiations WHERE negotiation_id = $1", uuid.UUID(negotiation_id)
    )
    positions = json.loads(row["positions"])
    options = json.loads(row["options"])
    assert {p["domain"] for p in positions} == {"finance", "tasks"}
    assert len(options) == 3  # 2 real synthesized + do_nothing
    do_nothing = next(o for o in options if o["option_id"] == "do_nothing")
    assert do_nothing["impact"]  # real, code-computed impact deltas present on every real option

    # A second real call against the now-already-detailed row must never
    # re-detail or crash -- SITUATION_RESOLVED or ALREADY_DETAILED are
    # both real, honest outcomes depending on current data; the row's
    # own real options must never be overwritten either way.
    second_outcome = await generate_detail_for_one_negotiation(
        pool, negotiation_id=negotiation_id, user_id=user_id, trigger_source="deadline_watch", api_key="fake-key-never-sent"
    )
    assert second_outcome in (BackfillOutcome.ALREADY_DETAILED, BackfillOutcome.SITUATION_RESOLVED)
    unchanged_row = await pool.fetchrow(
        "SELECT positions FROM negotiations WHERE negotiation_id = $1", uuid.UUID(negotiation_id)
    )
    assert unchanged_row["positions"] == row["positions"]  # never clobbered


# --- Real, live tests (skipped without a real GEMINI_API_KEY) ---


@pytest.mark.skipif(not _HAS_REAL_KEY, reason="no real GEMINI_API_KEY configured in this environment")
async def test_generate_detail_for_one_negotiation_a_real_live_gemini_backed_conflict_is_genuinely_detailed(pool, user_id):
    """The real capstone: a genuine tasks/finance conflict, real current
    data, a real live Gemini call for positions and synthesis, real
    code-computed impact -- the first time this exact real pipeline has
    ever run against data an autonomous job (not a hand-written seed
    script) could have produced."""
    settings = get_settings()
    negotiation_id = await _seed_bare_negotiation(pool, user_id=user_id, trigger_source="spend_alert")
    await _seed_real_recurring_subscription(pool, user_id=user_id, payee="Coworking", amount=5000.0)
    await _seed_expense(pool, user_id=user_id, payee="BigOneOff", amount=46000.0, occurred_days_ago=0)
    await _seed_task(pool, user_id=user_id, hours=12.0, deadline_offset_days=1)

    outcome = await generate_detail_for_one_negotiation(
        pool, negotiation_id=negotiation_id, user_id=user_id, trigger_source="spend_alert", api_key=settings.gemini_api_key
    )

    assert outcome is BackfillOutcome.DETAILED
    row = await pool.fetchrow(
        "SELECT positions, options FROM negotiations WHERE negotiation_id = $1", uuid.UUID(negotiation_id)
    )
    positions = json.loads(row["positions"])
    options = json.loads(row["options"])
    assert {p["domain"] for p in positions} == {"finance", "tasks"}
    assert len(options) == 3
