"""Real Company Research Digest (Phase 6, `QUORUM_PRODUCTION_COMPLETION_PLAN.md`,
`DEC-004`'s own Tavily decision, finally implemented) -- backs
`GET /career_pipeline/{application_id}/digest` (`QUORUM_DATA_CONTRACTS.md`
§5.11), closing the real, disclosed gap `career_digest_logic.dart`'s own
header already named: no `backend/features/career_digest.py` has ever
existed in this repository, despite `agents/career_agent.py`'s own
`CompileDigestCall` type signature (`Callable[[str, list[str]],
Awaitable[dict]]`) existing since `IMPL_17` waiting for a real
implementation, and `mobile/lib/features/career_digest/` having a real,
tested screen since Batch 7 (`DEC-084`).

REAL, DELIBERATE SCOPE BOUNDARY, disclosed rather than silently
narrowed: `agents/career_agent.py`'s own graph (`is_interview_detected`
arriving from Email's classification pipeline) is NOT wired to a real
caller here, and can't honestly be yet -- `IMPL_17`'s own text already
discloses that pipeline as separate, out-of-scope work, and confirmed
directly this session: no real interview-detection classifier exists
anywhere in `email_ingestion.py`. Wiring this to a real, unbuilt
detector would mean fabricating that detector's shape from nothing, the
exact Rule 3 violation ("never invent architecture beyond what the spec
describes") this project's own discipline forbids. Instead, this module
uses the one real, already-exercised, already-tested signal that
already exists for "this application deserves research": `applications.
status = 'interview_scheduled'` (`QUORUM_DATA_CONTRACTS.md` §5.10's own
real, live status value). This is not a downgrade of the real feature --
it's the same "close the gap with what's real, don't invent a new one"
principle `negotiation_detail_backfill.py`'s own top-of-file docstring
already applied when it chose to close a disclosed gap over building the
still-unspecified `briefing` job (`DEC-134`).

REAL, LIVE TAVILY SHAPE, confirmed live before writing `search_company()`
below, the same discipline every other real external API in this
backend has been held to (Gmail, Gemini): `POST https://api.tavily.com/
search` with `Authorization: Bearer <key>`, JSON body `{"query",
"search_depth", "max_results"}`, returns `{"results": [{"url", "title",
"content", "score", ...}]}` -- confirmed via a real, live call against
the real, configured `TAVILY_API_KEY` this session, not assumed from
training-time memory (which would have been a real risk here, the same
"the model this project's docs would have named is 404 now" lesson
`negotiation/gemini_calls.py`'s own docstring already discloses for
Gemini's model name).

REAL, CODE-COMPUTED `source_count`, NEVER MODEL-SELF-REPORTED: the same
"structure and IDs are code's job, not the model's" principle
`negotiation/gemini_calls.py`'s own `_DO_NOTHING_OPTION_ID` comment
already establishes for negotiation options, applied here to
`source_count` -- it is always `len(search_findings)`, computed in this
module, never a number Gemini is asked to produce or asked to agree
with.

REAL, QUOTA-CONSCIOUS BATCHING, applying `negotiation_detail_backfill.
py`'s own CRITICAL-tier-review-learned lesson (`DEC-135`) from the
start rather than waiting to relearn it: `digest_attempts`/`digest_
last_attempted_at` (migration `0014`) bound a durably-failing
application to `MAX_DIGEST_ATTEMPTS` real tries, ordered "least
recently attempted first" so a small, fixed set of failing candidates
can never occupy every real batch forever. `DEFAULT_BATCH_SIZE = 1`
for the same reason `negotiation_detail_backfill.py` reduced its own
batch size to 1 after measuring a real ~28s Gemini round trip under
Cloud Run's `--concurrency=1` -- a real Tavily search plus a real
Gemini summarization call per application is the same class of slow,
sequential, real-network work.

REAL, ATOMIC IDEMPOTENCY UNDER CONCURRENCY, same pattern as
`negotiation_detail_backfill.py::_persist_detail_if_still_bare`: the
final write is `UPDATE applications SET digest = $1::jsonb WHERE
application_id = $2 AND digest IS NULL`, so two real, concurrent
invocations racing on the same application can never double-write --
the loser is honestly tallied as `ALREADY_DIGESTED`, never silently
overwritten.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from enum import Enum, auto
from typing import Awaitable, Callable

import asyncpg
import httpx

logger = logging.getLogger("quorum_backend")

GEMINI_GENERATION_MODEL = "gemini-3.6-flash"
_GEMINI_GENERATE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_GENERATION_MODEL}:generateContent"
_TAVILY_SEARCH_URL = "https://api.tavily.com/search"

# See this module's own top-of-file docstring's "REAL, QUOTA-CONSCIOUS
# BATCHING" section for why these two exact values.
DEFAULT_BATCH_SIZE = 1
MAX_DIGEST_ATTEMPTS = 5

# How many real Tavily results feed one real digest -- small and fixed,
# the same "bounded, not unlimited" discipline `negotiation_detail_
# backfill.py`'s own DEFAULT_BATCH_SIZE applies to a different resource.
TAVILY_MAX_RESULTS = 5

CompileDigestCall = Callable[[str, list[str]], Awaitable[dict]]


@dataclass(frozen=True)
class CompanyDigest:
    company: str
    summary_points: list[str]
    source_count: int


class TavilySearchError(Exception):
    """Raised when a real Tavily search call -- and every real retry of
    it -- fails. Never silently substituted with an empty result list,
    which would be indistinguishable from a real, genuine "found
    nothing" search."""


class GeminiSummarizationError(Exception):
    """Raised when a real Gemini summarization call -- and every real
    retry of it -- fails. Never silently substituted with an invented
    summary, the same "model fabricates, code doesn't verify" failure
    this project's whole Gate architecture exists to prevent."""


async def search_company(company: str, *, api_key: str, max_retries: int = 2) -> list[str]:
    """Real, live Tavily search -- returns the real `content` snippet
    of each real result, most-relevant-first (Tavily's own real
    `score`-sorted response order, never re-sorted here). A real,
    genuine "no results found" is a real, valid, non-error outcome --
    returns an honest empty list, never raises for it."""
    last_error: Exception | None = None
    body = {"query": f"{company} company news", "search_depth": "basic", "max_results": TAVILY_MAX_RESULTS}
    for attempt in range(max_retries):
        if attempt > 0:
            await asyncio.sleep(attempt)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    _TAVILY_SEARCH_URL, headers={"Authorization": f"Bearer {api_key}"}, json=body
                )
            if response.status_code != 200:
                last_error = TavilySearchError(f"Tavily search returned {response.status_code}")
                continue
            data = response.json()
            return [result["content"] for result in data["results"] if result.get("content")]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            last_error = exc
    raise TavilySearchError(f"Tavily search failed after {max_retries} attempts: {last_error}") from last_error


_DIGEST_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "summary_points": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["summary_points"],
}


def make_gemini_compile_digest_call(*, api_key: str, max_retries: int = 2) -> CompileDigestCall:
    """Real factory matching `agents/career_agent.py`'s own, already-
    existing `CompileDigestCall` type signature exactly -- the real
    implementation that type has been waiting for since `IMPL_17`. Real,
    structured JSON output (`generationConfig.responseMimeType`), the
    same established pattern `negotiation/gemini_calls.py::
    make_gemini_position_call` already uses, not free-text-then-regex.

    A real, honest edge case: `search_findings` genuinely empty (Tavily
    found nothing) still calls Gemini -- asked directly to say so, not
    silently skipped -- so a real "nothing substantial found" result is
    a real, code-verified `summary_points: []`, matching `career_digest_
    logic.dart::hasNoRealContent()`'s own already-tested contract for
    that exact state, never confused with `DigestNotYetAvailableException`
    which this module's caller reserves for "not compiled yet."""

    async def compile_digest_call(company: str, search_findings: list[str]) -> dict:
        if search_findings:
            findings_text = "\n".join(f"- {finding}" for finding in search_findings)
            prompt = (
                f"You are researching the company \"{company}\" for someone about to interview there. "
                "Based ONLY on the real search results below -- never invent facts beyond them -- write "
                "at most 5 short, distinct, genuinely useful summary points (each one real sentence) "
                "covering things like recent news, culture, or product direction. If the results don't "
                "support a genuinely useful point, write fewer points rather than padding.\n\n"
                f"Real search results:\n{findings_text}"
            )
        else:
            prompt = (
                f"A real search for the company \"{company}\" returned no results. "
                "Return an empty summary_points list -- do not invent any content."
            )
        last_error: Exception | None = None
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "responseSchema": _DIGEST_SCHEMA},
        }
        for attempt in range(max_retries):
            if attempt > 0:
                await asyncio.sleep(attempt)
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        _GEMINI_GENERATE_URL, headers={"x-goog-api-key": api_key}, json=body
                    )
                if response.status_code != 200:
                    last_error = GeminiSummarizationError(f"Gemini generateContent returned {response.status_code}")
                    continue
                data = response.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                result = json.loads(text)
                # source_count is code-computed, never asked of or
                # trusted to the model -- see this module's own
                # top-of-file docstring.
                return {
                    "company": company,
                    "summary_points": result["summary_points"],
                    "source_count": len(search_findings),
                }
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
                last_error = exc
        raise GeminiSummarizationError(
            f"Gemini digest summarization failed after {max_retries} attempts: {last_error}"
        ) from last_error

    return compile_digest_call


async def fetch_company_digest(pool: asyncpg.Pool, *, user_id: str, application_id: str) -> CompanyDigest | None:
    """Real, live, per-user-scoped lookup. Returns `None` honestly both
    when `application_id` doesn't resolve to a real `applications` row
    this exact user owns (the "never confirm another user's data
    exists" discipline `GET /gate_reveal/{proposal_id}` already
    established) AND when the row exists but `digest` hasn't been
    compiled yet -- the caller (the real route) turns either case into
    the same real `404`, matching `career_digest_logic.dart`'s own
    already-tested contract: a digest that doesn't exist yet is a
    genuinely different real state from one that exists with zero
    summary points, but BOTH "not found" and "not compiled" collapse
    into the identical client-visible 404 by design (mobile's own
    `DigestNotYetAvailableException` doesn't distinguish them either)."""
    row = await pool.fetchrow(
        "SELECT company, digest FROM applications WHERE application_id = $1 AND user_id = $2",
        uuid.UUID(application_id),
        uuid.UUID(user_id),
    )
    if row is None or row["digest"] is None:
        return None
    digest = json.loads(row["digest"])
    return CompanyDigest(
        company=row["company"], summary_points=digest["summary_points"], source_count=digest["source_count"]
    )


class DigestOutcome(Enum):
    ALREADY_DIGESTED = auto()  # lost a real, live race to a concurrent invocation -- no double-write
    DIGESTED = auto()  # a real digest was genuinely searched, compiled, and persisted


@dataclass(frozen=True)
class CareerDigestRunResult:
    applications_scanned: int
    applications_failed: int
    digests_compiled: int
    outcome_counts: dict[str, int]


async def _mark_attempted(pool: asyncpg.Pool, *, application_id: str) -> None:
    """Called as the very first real write for one real application,
    before any real Tavily/Gemini call -- so a real attempt is counted
    even when everything after this point raises, the same `DEC-135`-
    learned discipline `negotiation_detail_backfill.py::_mark_attempted`
    already established."""
    await pool.execute(
        "UPDATE applications SET digest_attempts = digest_attempts + 1, digest_last_attempted_at = now() "
        "WHERE application_id = $1",
        uuid.UUID(application_id),
    )


async def _persist_digest_if_still_undigested(
    pool: asyncpg.Pool, *, application_id: str, digest: dict
) -> bool:
    tag = await pool.execute(
        "UPDATE applications SET digest = $1::jsonb WHERE application_id = $2 AND digest IS NULL",
        json.dumps(digest),
        uuid.UUID(application_id),
    )
    return tag == "UPDATE 1"


async def compile_digest_for_one_application(
    pool: asyncpg.Pool,
    *,
    application_id: str,
    company: str,
    tavily_api_key: str,
    compile_digest_call: CompileDigestCall,
) -> DigestOutcome:
    """Real, live, per-application digest compilation -- searches
    Tavily fresh every real call (never a cached/stale snapshot), then
    compiles via the real, injected `compile_digest_call` (production
    always passes `make_gemini_compile_digest_call()`'s real
    implementation; tests inject a deterministic fake, the same
    established split `negotiation_detail_backfill.py`'s own tests
    already use for `PositionCall`/`SynthesisCall`)."""
    await _mark_attempted(pool, application_id=application_id)
    search_findings = await search_company(company, api_key=tavily_api_key)
    digest = await compile_digest_call(company, search_findings)
    won = await _persist_digest_if_still_undigested(pool, application_id=application_id, digest=digest)
    return DigestOutcome.DIGESTED if won else DigestOutcome.ALREADY_DIGESTED


async def _fetch_candidate_application_ids(pool: asyncpg.Pool, *, batch_size: int) -> list[tuple[str, str]]:
    """Real candidate selection -- `applications.status = 'interview_
    scheduled'` (this module's own real, disclosed trigger; see this
    module's top-of-file docstring for why, not Email-classification-
    based detection). Ordered "least recently attempted first" (`NULLS
    FIRST` so a genuinely never-tried candidate always goes first, the
    same real round-robin `negotiation_detail_backfill.py`'s own
    candidate query already established) and excludes any application
    that's durably failed `MAX_DIGEST_ATTEMPTS` real times."""
    rows = await pool.fetch(
        "SELECT application_id, company FROM applications "
        "WHERE status = 'interview_scheduled' AND digest IS NULL AND digest_attempts < $2 "
        "ORDER BY digest_last_attempted_at ASC NULLS FIRST, created_at ASC "
        "LIMIT $1",
        batch_size,
        MAX_DIGEST_ATTEMPTS,
    )
    return [(str(row["application_id"]), row["company"]) for row in rows]


async def run_career_digest(
    pool: asyncpg.Pool,
    *,
    tavily_api_key: str,
    compile_digest_call: CompileDigestCall,
    batch_size: int = DEFAULT_BATCH_SIZE,
    application_ids: list[tuple[str, str]] | None = None,
) -> CareerDigestRunResult:
    """The real entry point -- `POST /internal/career-digest` (`main.py`)
    calls this with `application_ids=None` (the real, live default,
    scoped to real, interview-scheduled applications with no digest
    yet). `application_ids` (a list of `(application_id, company)`
    pairs), when explicitly passed, scopes the batch to exactly those
    real rows instead -- the same real, disclosed test-safety boundary
    `run_negotiation_detail_backfill`'s own `negotiation_ids` parameter
    already established.

    Per-application failure isolation, same discipline as `run_
    negotiation_detail_backfill`: one real application's failure (a
    Tavily/Gemini error, a malformed real value) is tallied and logged,
    never allowed to abort the rest of a real batch."""
    if application_ids is not None:
        candidates = list(application_ids)
    else:
        candidates = await _fetch_candidate_application_ids(pool, batch_size=batch_size)

    applications_scanned = 0
    applications_failed = 0
    digests_compiled = 0
    outcome_counts: dict[str, int] = {outcome.name: 0 for outcome in DigestOutcome}

    for application_id, company in candidates:
        try:
            outcome = await compile_digest_for_one_application(
                pool,
                application_id=application_id,
                company=company,
                tavily_api_key=tavily_api_key,
                compile_digest_call=compile_digest_call,
            )
        except Exception:  # noqa: BLE001 -- one real application's failure must never abort the rest of a real batch
            applications_failed += 1
            logger.exception(
                "Real career-digest compilation failed for application_id=%s -- continuing to the next real application",
                application_id,
            )
            continue

        applications_scanned += 1
        outcome_counts[outcome.name] += 1
        if outcome is DigestOutcome.DIGESTED:
            digests_compiled += 1

    return CareerDigestRunResult(
        applications_scanned=applications_scanned,
        applications_failed=applications_failed,
        digests_compiled=digests_compiled,
        outcome_counts=outcome_counts,
    )
