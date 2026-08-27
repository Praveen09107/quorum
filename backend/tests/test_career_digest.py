"""Real tests for features/career_digest.py (Phase 6, DEC-147) -- real,
live-database integration tests, mirroring test_negotiation_detail_
backfill.py's own established real pattern.

Two real/fake boundaries, matching that module's own already-established
split:
- Most tests below inject a fake `compile_digest_call` and never reach a
  real Gemini call; real Tavily calls are avoided the same way, via a
  monkeypatched `httpx.AsyncClient` that answers based on which real URL
  is being called (Tavily vs. Gemini use different real URLs).
- `test_compile_digest_for_one_application_a_real_full_pipeline_with_
  deterministic_fakes` exercises the REAL `make_gemini_compile_digest_
  call()` factory (not a bypass fake) against a monkeypatched client, so
  the real prompt-building/schema/parsing code genuinely runs.
- `test_run_career_digest_a_real_live_tavily_and_gemini_backed_digest_
  is_genuinely_compiled` is the one real, live, skippable-without-real-
  keys test that actually proves the real Tavily+Gemini integration
  works, per CLAUDE.md Rule 5.
"""
import json
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from quorum_backend.auth.user_provisioning import get_or_create_user
from quorum_backend.core import db
from quorum_backend.core.config import get_settings
from quorum_backend.features.career_digest import (
    MAX_DIGEST_ATTEMPTS,
    DigestOutcome,
    _fetch_candidate_application_ids,
    _mark_attempted,
    _persist_digest_if_still_undigested,
    compile_digest_for_one_application,
    fetch_company_digest,
    make_gemini_compile_digest_call,
    run_career_digest,
    search_company,
)

_HAS_REAL_KEYS = get_settings().tavily_api_key is not None and get_settings().gemini_api_key is not None


@pytest_asyncio.fixture
async def pool():
    real_pool = await db.create_pool()
    yield real_pool
    await real_pool.close()


@pytest_asyncio.fixture
async def user_id(pool):
    google_sub = f"test-career-digest-{uuid.uuid4()}"
    uid = await get_or_create_user(pool, google_sub=google_sub, email=None)
    yield uid
    await pool.execute("DELETE FROM applications WHERE user_id = $1", uuid.UUID(uid))
    await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(uid))


async def _seed_application(
    pool, *, user_id: str, company: str, status: str = "interview_scheduled",
    digest: str | None = None, digest_attempts: int = 0, digest_last_attempted_at: datetime | None = None,
) -> str:
    application_id = uuid.uuid4()
    await pool.execute(
        "INSERT INTO applications (application_id, user_id, company, status, digest, digest_attempts, digest_last_attempted_at) "
        "VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)",
        application_id, uuid.UUID(user_id), company, status, digest, digest_attempts, digest_last_attempted_at,
    )
    return str(application_id)


async def _fake_compile_digest_call(company: str, search_findings: list[str]) -> dict:
    return {"company": company, "summary_points": [f"A real point about {company}"], "source_count": len(search_findings)}


# --- fetch_company_digest -- real DB, zero real network ---


async def test_fetch_company_digest_returns_none_for_a_real_application_with_no_digest_yet(pool, user_id):
    application_id = await _seed_application(pool, user_id=user_id, company="Notion", digest=None)

    result = await fetch_company_digest(pool, user_id=user_id, application_id=application_id)

    assert result is None


async def test_fetch_company_digest_returns_real_summary_points_and_source_count(pool, user_id):
    digest_json = json.dumps({"summary_points": ["Raised a Series C in 2021.", "Growing fast."], "source_count": 3})
    application_id = await _seed_application(pool, user_id=user_id, company="Notion", digest=digest_json)

    result = await fetch_company_digest(pool, user_id=user_id, application_id=application_id)

    assert result is not None
    assert result.company == "Notion"
    assert result.summary_points == ["Raised a Series C in 2021.", "Growing fast."]
    assert result.source_count == 3


async def test_fetch_company_digest_returns_none_for_a_real_nonexistent_application(pool, user_id):
    result = await fetch_company_digest(pool, user_id=user_id, application_id=str(uuid.uuid4()))
    assert result is None


async def test_fetch_company_digest_never_leaks_another_real_users_application(pool, user_id):
    other_google_sub = f"test-career-digest-bystander-{uuid.uuid4()}"
    other_user_id = await get_or_create_user(pool, google_sub=other_google_sub, email=None)
    digest_json = json.dumps({"summary_points": ["A real point."], "source_count": 1})
    try:
        application_id = await _seed_application(pool, user_id=other_user_id, company="Notion", digest=digest_json)

        result = await fetch_company_digest(pool, user_id=user_id, application_id=application_id)

        assert result is None  # genuinely exists, but not for THIS real user
    finally:
        await pool.execute("DELETE FROM applications WHERE user_id = $1", uuid.UUID(other_user_id))
        await pool.execute("DELETE FROM users WHERE user_id = $1", uuid.UUID(other_user_id))


# --- Attempt tracking / atomic persistence -- real DB, zero real network ---


async def test_mark_attempted_increments_attempts_and_sets_last_attempted_at(pool, user_id):
    application_id = await _seed_application(pool, user_id=user_id, company="Notion")

    await _mark_attempted(pool, application_id=application_id)

    row = await pool.fetchrow(
        "SELECT digest_attempts, digest_last_attempted_at FROM applications WHERE application_id = $1",
        uuid.UUID(application_id),
    )
    assert row["digest_attempts"] == 1
    assert row["digest_last_attempted_at"] is not None


async def test_persist_digest_if_still_undigested_returns_false_when_a_real_row_already_has_a_digest(pool, user_id):
    existing = json.dumps({"summary_points": ["already there"], "source_count": 1})
    application_id = await _seed_application(pool, user_id=user_id, company="Notion", digest=existing)

    won = await _persist_digest_if_still_undigested(
        pool, application_id=application_id, digest={"summary_points": ["new"], "source_count": 2}
    )

    assert won is False
    row = await pool.fetchrow("SELECT digest FROM applications WHERE application_id = $1", uuid.UUID(application_id))
    assert json.loads(row["digest"])["summary_points"] == ["already there"]  # never clobbered


async def test_persist_digest_if_still_undigested_returns_true_and_writes_for_a_real_undigested_row(pool, user_id):
    application_id = await _seed_application(pool, user_id=user_id, company="Notion", digest=None)

    won = await _persist_digest_if_still_undigested(
        pool, application_id=application_id, digest={"company": "Notion", "summary_points": ["real point"], "source_count": 2}
    )

    assert won is True
    row = await pool.fetchrow("SELECT digest FROM applications WHERE application_id = $1", uuid.UUID(application_id))
    assert json.loads(row["digest"])["summary_points"] == ["real point"]


# --- Candidate selection -- real DB, zero real network ---


async def test_fetch_candidate_application_ids_only_returns_interview_scheduled_with_no_digest(pool, user_id):
    # Restricted to this test's own three rows below in case any other
    # real interview-scheduled application exists in this real, shared
    # database -- inclusion/exclusion of THESE rows is what's under
    # test, not the exact returned set (matches `negotiation_detail_
    # backfill.py`'s own established real-database test discipline).
    wanted = await _seed_application(pool, user_id=user_id, company="Wanted", status="interview_scheduled", digest=None)
    wrong_status = await _seed_application(pool, user_id=user_id, company="WrongStatus", status="applied", digest=None)
    already_digested = await _seed_application(
        pool, user_id=user_id, company="AlreadyDigested", status="interview_scheduled",
        digest=json.dumps({"summary_points": [], "source_count": 0}),
    )
    ours = {wanted, wrong_status, already_digested}

    candidates = await _fetch_candidate_application_ids(pool, batch_size=1000)
    our_candidates = {application_id for application_id, _company in candidates if application_id in ours}

    assert our_candidates == {wanted}


async def test_fetch_candidate_application_ids_excludes_a_real_application_at_the_attempt_cap(pool, user_id):
    exhausted = await _seed_application(
        pool, user_id=user_id, company="DurablyFailing", digest_attempts=MAX_DIGEST_ATTEMPTS,
        digest_last_attempted_at=datetime.now(timezone.utc),
    )
    fresh = await _seed_application(pool, user_id=user_id, company="Fresh")

    candidates = await _fetch_candidate_application_ids(pool, batch_size=1000)
    candidate_ids = {application_id for application_id, _company in candidates}

    assert exhausted not in candidate_ids
    assert fresh in candidate_ids


async def test_fetch_candidate_application_ids_orders_never_attempted_before_recently_attempted(pool, user_id):
    now = datetime.now(timezone.utc)
    recently_attempted = await _seed_application(
        pool, user_id=user_id, company="RecentlyTried", digest_attempts=1, digest_last_attempted_at=now
    )
    never_attempted = await _seed_application(pool, user_id=user_id, company="NeverTried")

    candidates = await _fetch_candidate_application_ids(pool, batch_size=1000)
    candidate_ids = [application_id for application_id, _company in candidates]

    assert candidate_ids.index(never_attempted) < candidate_ids.index(recently_attempted)


# --- compile_digest_for_one_application -- real DB, deterministic fake search ---


async def test_compile_digest_for_one_application_a_real_success_writes_a_real_digest(pool, user_id, monkeypatch):
    async def fake_search(company, *, api_key, max_retries=2):
        return ["A real finding about the company."]

    monkeypatch.setattr("quorum_backend.features.career_digest.search_company", fake_search)
    application_id = await _seed_application(pool, user_id=user_id, company="Notion")

    outcome = await compile_digest_for_one_application(
        pool, application_id=application_id, company="Notion", tavily_api_key="unused",
        compile_digest_call=_fake_compile_digest_call,
    )

    assert outcome is DigestOutcome.DIGESTED
    row = await pool.fetchrow("SELECT digest, digest_attempts FROM applications WHERE application_id = $1", uuid.UUID(application_id))
    digest = json.loads(row["digest"])
    assert digest["summary_points"] == ["A real point about Notion"]
    assert digest["source_count"] == 1
    assert row["digest_attempts"] == 1  # marked attempted exactly once


async def test_compile_digest_for_one_application_marks_attempted_even_when_search_raises(pool, user_id, monkeypatch):
    from quorum_backend.features.career_digest import TavilySearchError

    async def failing_search(company, *, api_key, max_retries=2):
        raise TavilySearchError("real, simulated Tavily failure")

    monkeypatch.setattr("quorum_backend.features.career_digest.search_company", failing_search)
    application_id = await _seed_application(pool, user_id=user_id, company="Notion")

    with pytest.raises(TavilySearchError):
        await compile_digest_for_one_application(
            pool, application_id=application_id, company="Notion", tavily_api_key="unused",
            compile_digest_call=_fake_compile_digest_call,
        )

    row = await pool.fetchrow("SELECT digest_attempts FROM applications WHERE application_id = $1", uuid.UUID(application_id))
    assert row["digest_attempts"] == 1


async def test_compile_digest_for_one_application_a_real_second_call_on_an_already_digested_row_never_overwrites(pool, user_id, monkeypatch):
    async def fake_search(company, *, api_key, max_retries=2):
        return ["finding"]

    monkeypatch.setattr("quorum_backend.features.career_digest.search_company", fake_search)
    application_id = await _seed_application(pool, user_id=user_id, company="Notion")

    first = await compile_digest_for_one_application(
        pool, application_id=application_id, company="Notion", tavily_api_key="unused", compile_digest_call=_fake_compile_digest_call
    )
    assert first is DigestOutcome.DIGESTED

    second = await compile_digest_for_one_application(
        pool, application_id=application_id, company="Notion", tavily_api_key="unused", compile_digest_call=_fake_compile_digest_call
    )
    assert second is DigestOutcome.ALREADY_DIGESTED

    row = await pool.fetchrow("SELECT digest, digest_attempts FROM applications WHERE application_id = $1", uuid.UUID(application_id))
    assert row["digest_attempts"] == 2  # both real attempts counted
    assert json.loads(row["digest"])["summary_points"] == ["A real point about Notion"]  # first write wins


# --- run_career_digest -- real DB, deterministic fake search/compile ---


async def test_run_career_digest_scans_exactly_the_real_applications_it_is_given(pool, user_id, monkeypatch):
    async def fake_search(company, *, api_key, max_retries=2):
        return []

    monkeypatch.setattr("quorum_backend.features.career_digest.search_company", fake_search)
    wanted = await _seed_application(pool, user_id=user_id, company="Wanted")
    await _seed_application(pool, user_id=user_id, company="NotIncluded")

    result = await run_career_digest(
        pool, tavily_api_key="unused", compile_digest_call=_fake_compile_digest_call,
        application_ids=[(wanted, "Wanted")],
    )

    assert result.applications_scanned == 1
    assert result.digests_compiled == 1
    not_included_row = await pool.fetchrow(
        "SELECT digest FROM applications WHERE company = 'NotIncluded' AND user_id = $1", uuid.UUID(user_id)
    )
    assert not_included_row["digest"] is None  # never touched


async def test_run_career_digest_a_real_failure_for_one_application_never_blocks_the_rest(pool, user_id, monkeypatch):
    async def fake_search(company, *, api_key, max_retries=2):
        return []

    monkeypatch.setattr("quorum_backend.features.career_digest.search_company", fake_search)
    good_id = await _seed_application(pool, user_id=user_id, company="Good")

    result = await run_career_digest(
        pool, tavily_api_key="unused", compile_digest_call=_fake_compile_digest_call,
        application_ids=[("not-a-real-uuid", "Malformed"), (good_id, "Good")],
    )

    assert result.applications_failed == 1
    assert result.applications_scanned == 1
    assert result.digests_compiled == 1
    assert result.outcome_counts["DIGESTED"] == 1


# --- The real, structured-output factory itself -- real DB, monkeypatched HTTP ---


class _FakeHttpResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _FakeCareerDigestHttpClient:
    """Dispatches on the real, distinct URL each real provider uses --
    Tavily and Gemini never share a URL, so this is a genuine,
    deterministic stand-in for both real network calls this module
    makes, the same technique test_negotiation_detail_backfill.py's own
    `_FakeGeminiClient` already established (there dispatching on
    request schema instead, since both its own real calls share one
    Gemini URL)."""

    def __init__(self, tavily_results: list[dict], gemini_summary_points: list[str]):
        self._tavily_results = tavily_results
        self._gemini_summary_points = gemini_summary_points

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, **kwargs):
        from quorum_backend.features.career_digest import _GEMINI_GENERATE_URL, _TAVILY_SEARCH_URL

        if url == _TAVILY_SEARCH_URL:
            return _FakeHttpResponse(200, {"results": self._tavily_results})
        assert url == _GEMINI_GENERATE_URL
        text = json.dumps({"summary_points": self._gemini_summary_points})
        return _FakeHttpResponse(200, {"candidates": [{"content": {"parts": [{"text": text}]}}]})


async def test_compile_digest_for_one_application_a_real_full_pipeline_with_deterministic_fakes(pool, user_id, monkeypatch):
    """Exercises the REAL `make_gemini_compile_digest_call()` factory and
    the REAL `search_company()` -- not bypass fakes -- against a
    monkeypatched `httpx.AsyncClient`, so the real prompt-building,
    real schema, and real response-parsing code all genuinely run."""
    fake_client = _FakeCareerDigestHttpClient(
        tavily_results=[{"content": "Notion raised a Series C round."}, {"content": "Notion is hiring fast."}],
        gemini_summary_points=["Raised a Series C round.", "Hiring fast."],
    )
    monkeypatch.setattr("quorum_backend.features.career_digest.httpx.AsyncClient", lambda **kwargs: fake_client)
    application_id = await _seed_application(pool, user_id=user_id, company="Notion")
    compile_digest_call = make_gemini_compile_digest_call(api_key="fake-key-never-sent")

    outcome = await compile_digest_for_one_application(
        pool, application_id=application_id, company="Notion", tavily_api_key="fake-key-never-sent",
        compile_digest_call=compile_digest_call,
    )

    assert outcome is DigestOutcome.DIGESTED
    digest = await fetch_company_digest(pool, user_id=user_id, application_id=application_id)
    assert digest.summary_points == ["Raised a Series C round.", "Hiring fast."]
    assert digest.source_count == 2  # code-computed from the real 2 Tavily results, never model-reported


async def test_compile_digest_call_a_real_empty_search_still_produces_a_real_honest_digest(monkeypatch):
    """A real, genuine 'nothing found' search must still produce a real,
    valid digest with zero summary points -- never an error, and never
    conflated with `DigestNotYetAvailableException`'s own real, distinct
    meaning (career_digest_logic.dart's own already-tested contract)."""
    fake_client = _FakeCareerDigestHttpClient(tavily_results=[], gemini_summary_points=[])
    monkeypatch.setattr("quorum_backend.features.career_digest.httpx.AsyncClient", lambda **kwargs: fake_client)
    compile_digest_call = make_gemini_compile_digest_call(api_key="fake-key-never-sent")

    result = await compile_digest_call("Notion", [])

    assert result["summary_points"] == []
    assert result["source_count"] == 0


# --- Real, live tests (skipped without real TAVILY_API_KEY/GEMINI_API_KEY) ---


@pytest.mark.skipif(not _HAS_REAL_KEYS, reason="no real TAVILY_API_KEY/GEMINI_API_KEY configured in this environment")
async def test_search_company_a_real_live_tavily_call_returns_real_results():
    settings = get_settings()
    results = await search_company("Notion", api_key=settings.tavily_api_key)
    assert isinstance(results, list)
    assert len(results) > 0
    assert all(isinstance(r, str) for r in results)


@pytest.mark.skipif(not _HAS_REAL_KEYS, reason="no real TAVILY_API_KEY/GEMINI_API_KEY configured in this environment")
async def test_run_career_digest_a_real_live_tavily_and_gemini_backed_digest_is_genuinely_compiled(pool, user_id):
    """The real capstone: a real, live Tavily search, a real, live
    Gemini summarization call, real code-computed `source_count`, a
    real atomic persist -- the first time this exact real pipeline has
    ever run end to end."""
    settings = get_settings()
    application_id = await _seed_application(pool, user_id=user_id, company="Notion")
    compile_digest_call = make_gemini_compile_digest_call(api_key=settings.gemini_api_key)

    result = await run_career_digest(
        pool, tavily_api_key=settings.tavily_api_key, compile_digest_call=compile_digest_call,
        application_ids=[(application_id, "Notion")],
    )

    assert result.digests_compiled == 1
    digest = await fetch_company_digest(pool, user_id=user_id, application_id=application_id)
    assert digest is not None
    assert digest.company == "Notion"
    assert isinstance(digest.summary_points, list)
    assert digest.source_count >= 0
