"""Quorum backend — FastAPI application entry point.

Originally deliberately minimal (/health only) per Phase 0's own
kickoff-guide finding -- no import of gate/, router.py, agents/, or
auth/. That was real, disclosed, deliberately-later work
(QUORUM_IMPLEMENTATION_STRATEGY.md Phase 3), and Phase 3 is where it
lands: a real, live `GET /trust_digest` backed by a real Postgres pool
(`core/db.py`, Part B), and now real `POST /auth/token`, `/auth/refresh`,
`/auth/revoke` (Part C prerequisite) -- wiring IMPL_12's already-built,
CRITICAL-tier-reviewed session-management modules into real routes for
the first time, and requiring a real, valid access token on every
endpoint that touches real user data (`/trust_digest` included, as of
this session).

Real, minimal integration of `core/config.py` (Phase 0's own settings
module), added the same session it was built: a real startup-time check,
not just an unreferenced file. If a real deployment ever boots with the
known, public, insecure default JWT signing key still in place, that's
loudly logged now -- a real safety net for exactly the "someone forgot
to set a real secret" failure mode.
"""
import logging
import secrets
import uuid
from urllib.parse import urlencode
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator

import asyncpg
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, field_validator

from quorum_backend.auth.access_token import (
    ACCESS_TOKEN_TTL_MINUTES,
    AccessTokenExpired,
    AccessTokenInvalid,
    create_access_token,
    decode_access_token,
)
from quorum_backend.auth.google_oauth import GoogleIdTokenInvalid, GoogleOAuthExchangeFailed, exchange_authorization_code, verify_google_id_token
from quorum_backend.auth.google_token_store import fetch_google_tokens, store_google_tokens, update_access_token_after_refresh
from quorum_backend.auth.refresh_token import (
    TokenExpired,
    TokenInvalid,
    TokenRevoked,
    TokenReuseDetected,
    hash_token,
    issue_refresh_token,
    revoke_all_for_user,
    rotate_refresh_token,
)
from quorum_backend.auth.revocation_store import SupabaseRevocationStore
from quorum_backend.auth.user_provisioning import get_or_create_user, resolve_internal_user_id
from quorum_backend.core import db
from quorum_backend.core.config import get_settings
from quorum_backend.core.embeddings import EmbeddingError
from quorum_backend.features.career_digest import (
    fetch_company_digest,
    make_gemini_compile_digest_call,
    run_career_digest,
)
from quorum_backend.features.career_pipeline import fetch_career_pipeline
from quorum_backend.features.deadline_watch import run_deadline_watch
from quorum_backend.features.email_ingestion import run_email_ingestion
from quorum_backend.features.gate_reveal import fetch_gate_reveal
from quorum_backend.features.honesty_log import fetch_honesty_feed
from quorum_backend.features.negotiation_choice import (
    InvalidChosenOption,
    NegotiationAlreadyResolved,
    NegotiationNotFound,
    NegotiationNotReadyToChoose,
    choose_negotiation_option,
)
from quorum_backend.features.negotiation_detail import fetch_negotiation_detail
from quorum_backend.features.negotiation_detail_backfill import run_negotiation_detail_backfill
from quorum_backend.features.predictive_risk import fetch_risk_assessment
from quorum_backend.features.retry_queue_drainer import drain_due_jobs
from quorum_backend.features.search import search as run_search
from quorum_backend.features.self_test_harness import ScenarioResult, run_self_test, summarize
from quorum_backend.features.spend_alert import run_spend_alert
from quorum_backend.features.subscription_detective import fetch_detected_subscriptions
from quorum_backend.features.tasks import fetch_tasks
from quorum_backend.features.waiting_on import fetch_stale_waiting_on
from quorum_backend.features.today import (
    fetch_active_negotiations,
    fetch_pending_actions,
    fetch_today_budget,
    fetch_today_capacity,
)
from quorum_backend.features.quick_capture import QuickCaptureError, capture_task_from_text, make_gemini_task_extraction_call
from quorum_backend.features.trust_digest import fetch_trust_digest
from quorum_backend.gate.llm_calls import make_gemini_judge_call, make_groq_critic_call
from quorum_backend.negotiation.downstream_translation import make_gemini_downstream_translation_call
from quorum_backend.security.account_deletion import delete_account
from quorum_backend.security.supabase_deletion_store import SupabaseDeletionStore

logger = logging.getLogger("quorum_backend")


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.is_using_insecure_default_jwt_signing_key:
        logger.warning(
            "JWT_SIGNING_KEY is still the real, public, insecure default "
            '("change-me-in-real-deployment") -- set a real secret via '
            "the environment or .env before this deployment issues any "
            "real access token."
        )
    # A real, live pool -- created once per container instance (Cloud
    # Run's own --concurrency=1 means this instance serves one request
    # at a time for its whole life, so one pool for the whole lifespan is
    # correct, not a shortcut), closed cleanly on shutdown.
    #
    # Deliberately NOT allowed to crash the whole app on failure: /health
    # is a liveness check (is this process alive?), not a readiness check
    # (are all its downstream dependencies reachable?). If Supabase is
    # briefly unreachable at cold-start, the container should still come
    # up and answer /health -- only endpoints that genuinely need the
    # database (like /trust_digest below) should fail, and only those
    # ones, with a clear, real error rather than the whole service being
    # unable to start. app.state.db_pool is None in that case; every
    # consumer must check for that explicitly, never assume it's set.
    try:
        app.state.db_pool = await db.create_pool()
    except Exception:
        logger.exception("Real database pool creation failed at startup -- /health will still work; endpoints that need the database will return 503 until this recovers.")
        app.state.db_pool = None
    try:
        yield
    finally:
        if app.state.db_pool is not None:
            await app.state.db_pool.close()


app = FastAPI(title="Quorum Backend", lifespan=_lifespan)

# Shared across GET /negotiations/{id} and POST /negotiations/{id}/choose --
# both real 404 cases (a real nonexistent id, or one owned by another
# real user) are deliberately indistinguishable, so both routes use the
# exact same real detail text, not two independently-drifting copies.
_NEGOTIATION_NOT_FOUND_DETAIL = "No negotiation found with that id."
_GATE_REVEAL_NOT_FOUND_DETAIL = "No action found with that id."
# Deliberately the same real detail text for "no such application" and
# "a real application exists but its digest hasn't been compiled yet" --
# see `features/career_digest.py::fetch_company_digest`'s own docstring
# for why these two real, different states share one client-visible 404.
_CAREER_DIGEST_NOT_FOUND_DETAIL = "No digest found for that application."


def _get_db_pool(request: Request) -> asyncpg.Pool:
    # Sync on purpose -- plain attribute access, nothing to await. FastAPI
    # supports sync dependency callables directly; an async def here with
    # no real await inside it would be decorative, not genuine.
    pool = request.app.state.db_pool
    if pool is None:
        raise HTTPException(status_code=503, detail="Database is not currently reachable -- try again shortly.")
    return pool


def _get_revocation_store(pool: asyncpg.Pool = Depends(_get_db_pool)) -> SupabaseRevocationStore:
    return SupabaseRevocationStore(pool)


def _require_auth(authorization: str | None = Header(default=None)) -> str:
    """Real Bearer-token auth -- this is the actual security boundary
    real requests are protected by (see `main.py`'s own top-of-file
    docstring and `DECISIONS_LOG.md` for why the Cloud Run network-level
    gate was deliberately relaxed in favor of this). Returns the real,
    verified `user_id` on success. Every non-success path is a real,
    distinct 401 -- never a silent pass-through."""
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header -- expected 'Bearer <access_token>'.")
    raw_token = authorization.removeprefix("Bearer ")
    settings = get_settings()
    try:
        return decode_access_token(raw_token, settings.jwt_signing_key)
    except AccessTokenExpired as exc:
        raise HTTPException(status_code=401, detail="Access token has expired -- use /auth/refresh to get a new one.") from exc
    except AccessTokenInvalid as exc:
        raise HTTPException(status_code=401, detail="Access token is invalid.") from exc


def _require_internal_secret(x_internal_secret: str | None = Header(default=None)) -> None:
    """Real, deliberately DIFFERENT auth from `_require_auth` above --
    `POST /internal/drain-retry-queue` is called by `pg_net` (once
    genuinely enabled, `DEC-127`'s own disclosed open item) or a real,
    trusted operator, never by a real end-user session, so there is no
    real Bearer access token to check here. A real, static shared secret
    instead, read once from `core/config.py`'s own real `internal_drain_
    secret` field. Fails closed on every real failure path: the secret
    is unset (never provisioned, or a real deployment simply hasn't set
    one), the header is missing, or it doesn't match -- all three are
    the same real 401, no path silently proceeds. `secrets.compare_digest`
    is used deliberately, not `==` -- a real, if narrow, timing-attack
    hardening for a value that genuinely gates a real, live database
    write path.

    A REAL, DISCLOSED FIX, found by this session's own CRITICAL-tier
    review: `secrets.compare_digest` raises `TypeError` on a non-ASCII
    `str` -- and Starlette latin-1-decodes request headers, so a single
    stray non-ASCII byte in a real, unauthenticated caller's header
    reached it, live-proven to turn what should be a clean 401 into a
    500 with a stack trace in this deployment's own real logs (still
    fails CLOSED -- no scan ever ran, no write ever happened -- so this
    was availability/log-noise, not an auth bypass). Compared as raw
    UTF-8 bytes now, which `compare_digest` accepts for any real input,
    ASCII or not."""
    settings = get_settings()
    if settings.internal_drain_secret is None:
        raise HTTPException(status_code=401, detail="Internal drain endpoint is not configured on this deployment.")
    if x_internal_secret is None or not secrets.compare_digest(
        x_internal_secret.encode("utf-8"), settings.internal_drain_secret.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Missing or invalid X-Internal-Secret header.")


async def _resolve_internal_user_id_or_404(pool: asyncpg.Pool, google_sub: str) -> str:
    """Real, shared helper for every per-user-scoped route -- resolves
    `_require_auth`'s real Google `sub` into the real, internal UUID
    `auth/user_provisioning.py` provisions at `/auth/token` time
    (`DEC-110`). In practice this should always succeed (provisioning
    happens before any access token exists to reach here with), but a
    genuinely unprovisioned identity is a real, honest 404 -- never
    silently treated as "show every user's data.\""""
    internal_user_id = await resolve_internal_user_id(pool, google_sub=google_sub)
    if internal_user_id is None:
        raise HTTPException(status_code=404, detail="No account found for this session -- sign in again.")
    return internal_user_id


class TokenExchangeRequest(BaseModel):
    """Real request shape for `POST /auth/token` -- a reasoned
    construction against standard OAuth 2.0 Authorization Code + PKCE
    practice (see `auth/google_oauth.py`'s own top-of-file docstring for
    why no literal spec shape exists to copy instead)."""

    code: str
    code_verifier: str
    redirect_uri: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ChooseNegotiationOptionRequest(BaseModel):
    """Real request shape, `QUORUM_DATA_CONTRACTS.md` §5.6's own literal
    example (`{"chosen_option": "option_a" | "option_b" | "do_nothing"}`)
    -- the one real request shape in this file with a literal spec
    example to match exactly, not a reasoned construction."""

    chosen_option: str


class QuickCaptureRequest(BaseModel):
    """Real request shape, `DEC-153` -- a real user's own free text,
    genuinely untrusted (see `features/quick_capture.py`'s own top-of-
    file docstring for why this route is CRITICAL-tier, not standard).
    A real, minimum length check refuses an empty/whitespace-only
    submission before it ever reaches a real, billed Gemini call."""

    text: str = Field(min_length=1, max_length=2000)

    @field_validator("text")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_TTL_MINUTES * 60


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _serialize_scenario_result(result: ScenarioResult) -> dict:
    # Deliberately excludes the real `verdict` field (a full GateVerdict)
    # -- QUORUM_DATA_CONTRACTS.md §5.14's own example shows exactly four
    # fields per scenario, never the full verdict. Serializing it would
    # be extra, unspecified surface no client here asks for.
    return {
        "scenario_id": result.scenario_id,
        "expected": result.expected,
        "actual": result.actual,
        "passed": result.passed,
    }


@app.get("/trust")
async def trust(
    _user_id: str = Depends(_require_auth),
) -> dict:
    """Real, live -- runs the real adversarial scenario suite directly
    against the real `gate.review()` (`self_test_harness.py`, `DEC-099`),
    never a stub (this repository never built one -- see `CLAUDE.md`'s
    own corrected note on this). Response shape matches
    `QUORUM_DATA_CONTRACTS.md` §5.14 exactly, including the real,
    load-bearing `target` field, always `"real_gate"` here.
    """
    results = await run_self_test()
    summary = summarize(results, target="real_gate")
    return {
        "total": summary.total,
        "caught": summary.caught,
        "missed": [_serialize_scenario_result(r) for r in summary.missed],
        "results": [_serialize_scenario_result(r) for r in summary.results],
        "target": summary.target,
    }


@app.get("/trust_digest")
async def trust_digest(
    pool: asyncpg.Pool = Depends(_get_db_pool),
    google_sub: str = Depends(_require_auth),
) -> dict:
    """Real, live -- queries the real `action_events` table via
    `fetch_trust_digest()`, never mocked or pre-computed data. Response
    shape matches `QUORUM_DATA_CONTRACTS.md` §5.15 exactly.

    RESOLVED, `DEC-150`: this docstring previously said `action_events`
    had no `user_id` column and that this route was only a "you must be
    signed in" gate, not a real per-user filter -- true when first
    written, false since migration `0004`/`DEC-119`, and never corrected
    here even after `DEC-145` found and disclosed the live consequence
    (this route genuinely aggregated every real user's data together).
    Real per-user scoped now, matching every other per-user-scoped route
    in this backend (`_resolve_internal_user_id_or_404`, `DEC-110`).
    """
    internal_user_id = await _resolve_internal_user_id_or_404(pool, google_sub)
    result = await fetch_trust_digest(pool, user_id=internal_user_id)
    return {
        "current_week": asdict(result.current_week),
        "previous_week": asdict(result.previous_week) if result.previous_week is not None else None,
        "trend": result.trend,
        "delta": result.delta,
    }


@app.get("/tasks")
async def tasks(
    pool: asyncpg.Pool = Depends(_get_db_pool),
    google_sub: str = Depends(_require_auth),
) -> list[dict]:
    """Real, live -- queries the real `tasks` table via `fetch_tasks()`,
    never mocked or pre-computed data. Response shape matches
    `QUORUM_DATA_CONTRACTS.md` §5.17 exactly: `status` is a genuinely
    closed set (`open`/`done`/`cancelled`, a real database `CHECK`
    constraint), so this route never needs to defend against an
    unrecognized value the way an open-vocabulary field would.

    Requires a real, valid access token (`_require_auth`) and, as of
    `DEC-110`, is real per-user scoped -- `_resolve_internal_user_id_
    or_404` maps the real Google identity onto the real internal UUID
    `tasks.user_id` actually expects.
    """
    internal_user_id = await _resolve_internal_user_id_or_404(pool, google_sub)
    records = await fetch_tasks(pool, user_id=internal_user_id)
    return [
        {
            "task_id": record.task_id,
            "title": record.title,
            "estimated_hours": record.estimated_hours,
            "deadline": record.deadline,
            "status": record.status,
        }
        for record in records
    ]


@app.post("/quick_capture")
async def quick_capture_endpoint(
    body: QuickCaptureRequest,
    pool: asyncpg.Pool = Depends(_get_db_pool),
    google_sub: str = Depends(_require_auth),
) -> dict:
    """Real, live -- Phase 7, `QUORUM_PRODUCTION_COMPLETION_PLAN.md`,
    `DEC-153`. The first real write path in this backend that isn't
    negotiation-choice or account deletion: a real user's own free
    text, extracted into a real `CREATE_TASK` proposal, reviewed by the
    real Gate, and -- for a genuine approve -- written as a real `tasks`
    row, all synchronously in this one request (`CREATE_TASK` is real
    `Stakes.S1`; Stage B never runs, so this stays fast). Real per-user
    scoped from this route's first line. See `features/quick_capture.py`
    for the full account of this session's own real scope decisions.

    A real, honest `503` if the extraction provider isn't configured
    (matching `GET /search`'s own established convention for the
    identical real reason -- no `GEMINI_API_KEY` in this environment).
    A real, honest `502` if a live extraction call itself fails after
    retries -- never a fabricated task standing in for a genuine
    failure."""
    settings = get_settings()
    if settings.gemini_api_key is None:
        raise HTTPException(status_code=503, detail="Quick capture is not currently available -- the extraction provider isn't configured.")
    internal_user_id = await _resolve_internal_user_id_or_404(pool, google_sub)

    extraction_call = make_gemini_task_extraction_call(api_key=settings.gemini_api_key)
    critic_call = make_groq_critic_call(api_key=settings.groq_api_key)
    judge_call = make_gemini_judge_call(api_key=settings.gemini_api_key)

    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                result = await capture_task_from_text(
                    conn,
                    user_id=internal_user_id,
                    free_text=body.text,
                    extraction_call=extraction_call,
                    critic_call=critic_call,
                    judge_call=judge_call,
                )
    except QuickCaptureError as exc:
        raise HTTPException(status_code=502, detail=f"Couldn't turn that into a real task: {exc}") from exc

    return {
        "executed": result.executed,
        "decision": result.decision,
        "stakes": result.stakes,
        "title": result.title,
        "findings": [finding.model_dump(mode="json") for finding in result.findings],
        "objections": [objection.model_dump(mode="json") for objection in result.objections],
    }


@app.get("/predictive_risk")
async def predictive_risk_endpoint(
    pool: asyncpg.Pool = Depends(_get_db_pool),
    google_sub: str = Depends(_require_auth),
) -> dict:
    """Real, live -- Phase 6, `QUORUM_PRODUCTION_COMPLETION_PLAN.md`,
    `DEC-149`. Real, per-user scoped assessment of whether next real
    calendar week's own real task-deadline density matches a
    historically risky pattern in this exact user's own real task
    history. See `features/predictive_risk.py`'s own top-of-file
    docstring for the real, disclosed design decisions this module made
    where no prior spec contract existed (this feature's real JSON
    shape, and its real "correction" proxy).

    Requires a real, valid access token (`_require_auth`) and is real
    per-user scoped from this route's first line."""
    internal_user_id = await _resolve_internal_user_id_or_404(pool, google_sub)
    assessment = await fetch_risk_assessment(pool, user_id=internal_user_id)
    return {
        "week_start": assessment.week_start,
        "deadline_density": assessment.deadline_density,
        "matching_historical_weeks": assessment.matching_historical_weeks,
        "pooled_correction_rate": assessment.pooled_correction_rate,
        "is_at_risk": assessment.is_at_risk,
    }


@app.get("/today")
async def today(
    pool: asyncpg.Pool = Depends(_get_db_pool),
    google_sub: str = Depends(_require_auth),
) -> dict:
    """Real, live -- `QUORUM_DATA_CONTRACTS.md` §5.4's full response
    shape, specified since `DEC-026`/`DEC-028`, implemented here for the
    first time (`DEC-119`). Real per-user scoped from this route's first
    line, unlike `/tasks`/`/career_pipeline`/`/finance/subscriptions`,
    which needed a later retrofit (`DEC-110`).

    A real, disclosed, honest fact, not a bug: `needs_you_now` and
    `in_motion` will genuinely, correctly return empty arrays in real
    production use right now -- nothing in this backend yet invokes the
    Gate against a real, live user action to ever produce a row into
    `action_events` or `negotiations` in the first place. `capacity` and
    `budget` are real, live-computed numbers regardless, from this
    user's actual `tasks`/`expenses` rows."""
    internal_user_id = await _resolve_internal_user_id_or_404(pool, google_sub)
    capacity = await fetch_today_capacity(pool, user_id=internal_user_id)
    budget = await fetch_today_budget(pool, user_id=internal_user_id)
    pending_actions = await fetch_pending_actions(pool, user_id=internal_user_id)
    active_negotiations = await fetch_active_negotiations(pool, user_id=internal_user_id)
    return {
        "capacity": {
            "hours_remaining_today": capacity.hours_remaining_today,
            "remaining_fraction": capacity.remaining_fraction,
            "source": capacity.source,
        },
        "budget": {
            "amount_remaining": budget.amount_remaining,
            "remaining_fraction": budget.remaining_fraction,
            "source": budget.source,
        },
        "needs_you_now": [
            {
                "proposal_id": record.proposal_id,
                "action_type": record.action_type,
                "stakes": record.stakes,
                "payload": record.payload,
                "created_at": record.created_at,
            }
            for record in pending_actions
        ],
        "in_motion": [
            {
                "negotiation_id": record.negotiation_id,
                "conflicted_domains": record.conflicted_domains,
                "started_at": record.started_at,
            }
            for record in active_negotiations
        ],
    }


@app.get("/negotiations/{negotiation_id}")
async def negotiation_detail_endpoint(
    negotiation_id: str,
    pool: asyncpg.Pool = Depends(_get_db_pool),
    google_sub: str = Depends(_require_auth),
) -> dict:
    """Real, live -- `QUORUM_DATA_CONTRACTS.md` §5.5a, a real gap found
    and closed this session: `mobile/lib/shell/main_shell.dart`'s
    `NegotiationBundle` has needed this since `MOBILE_09`, but no real
    REST contract for it ever existed. Real per-user scoped from this
    route's first line.

    A real, honest `404` if `negotiation_id` isn't a real, syntactically
    valid UUID, or doesn't resolve to a negotiation this caller owns --
    the two cases are deliberately indistinguishable in the response,
    the same "never confirm another user's data exists" discipline
    every other real per-user route in this backend already holds
    itself to."""
    try:
        negotiation_uuid = uuid.UUID(negotiation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=_NEGOTIATION_NOT_FOUND_DETAIL) from exc
    internal_user_id = await _resolve_internal_user_id_or_404(pool, google_sub)
    detail = await fetch_negotiation_detail(pool, user_id=internal_user_id, negotiation_id=str(negotiation_uuid))
    if detail is None:
        raise HTTPException(status_code=404, detail=_NEGOTIATION_NOT_FOUND_DETAIL)
    return {"positions": detail.positions, "options": detail.options}


@app.get("/gate_reveal/{proposal_id}")
async def gate_reveal_endpoint(
    proposal_id: str,
    pool: asyncpg.Pool = Depends(_get_db_pool),
    google_sub: str = Depends(_require_auth),
) -> dict:
    """Real, live -- Phase 6, `QUORUM_PRODUCTION_COMPLETION_PLAN.md`,
    closing the real, disclosed gap `DEC-126` found: no `findings`/
    `objections` persistence or backend route ever existed for this,
    despite `mobile/lib/shell/main_shell.dart`'s own real, already-
    built tap-through from a "Needs you now" card. Real per-user scoped
    from this route's first line.

    A real, honest `404` if `proposal_id` isn't a real, syntactically
    valid UUID, or doesn't resolve to an `action_events` row this
    caller owns -- the two cases are deliberately indistinguishable in
    the response, the same "never confirm another user's data exists"
    discipline `GET /negotiations/{negotiation_id}` already
    established."""
    try:
        proposal_uuid = uuid.UUID(proposal_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=_GATE_REVEAL_NOT_FOUND_DETAIL) from exc
    internal_user_id = await _resolve_internal_user_id_or_404(pool, google_sub)
    bundle = await fetch_gate_reveal(pool, user_id=internal_user_id, proposal_id=str(proposal_uuid))
    if bundle is None:
        raise HTTPException(status_code=404, detail=_GATE_REVEAL_NOT_FOUND_DETAIL)
    return {"stakes": bundle.stakes, "findings": bundle.findings, "objections": bundle.objections}


@app.post("/negotiations/{negotiation_id}/choose", status_code=202)
async def choose_negotiation_option_endpoint(
    negotiation_id: str,
    body: ChooseNegotiationOptionRequest,
    pool: asyncpg.Pool = Depends(_get_db_pool),
    google_sub: str = Depends(_require_auth),
) -> dict:
    """Real, live -- `QUORUM_DATA_CONTRACTS.md` §5.6, genuinely unbuilt
    since it was first specified, closing the gap `DEC-104`/`DEC-121`
    both disclosed: a person could see a real negotiation's real
    positions/options but never act on one. Real per-user scoped from
    this route's first line.

    A real, disclosed, honest scope boundary, not silently glossed
    over: this endpoint enqueues a real row in `retry_queue` describing
    the real chosen option -- it does NOT itself call the Gate again.
    No drainer that reads `retry_queue` and calls `gate.review()`
    exists anywhere in this backend yet (`features/negotiation_choice.py`'s
    own docstring has the full account). `202 Accepted` reflects that
    honestly: the choice is real and durably recorded, the downstream
    action is real and genuinely queued, but not yet processed."""
    try:
        negotiation_uuid = uuid.UUID(negotiation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=_NEGOTIATION_NOT_FOUND_DETAIL) from exc
    internal_user_id = await _resolve_internal_user_id_or_404(pool, google_sub)
    try:
        await choose_negotiation_option(
            pool, user_id=internal_user_id, negotiation_id=str(negotiation_uuid), chosen_option=body.chosen_option
        )
    except NegotiationNotFound as exc:
        raise HTTPException(status_code=404, detail=_NEGOTIATION_NOT_FOUND_DETAIL) from exc
    except NegotiationNotReadyToChoose as exc:
        raise HTTPException(status_code=409, detail="This negotiation's options haven't been computed yet -- nothing to choose from.") from exc
    except NegotiationAlreadyResolved as exc:
        raise HTTPException(status_code=409, detail="This negotiation already has a chosen option -- it cannot be chosen again.") from exc
    except InvalidChosenOption as exc:
        raise HTTPException(status_code=400, detail=f"'{body.chosen_option}' is not one of this negotiation's real options.") from exc
    return {"status": "accepted"}


@app.get("/search")
async def search_endpoint(
    q: str = Query(..., min_length=1),
    pool: asyncpg.Pool = Depends(_get_db_pool),
    google_sub: str = Depends(_require_auth),
) -> list[dict]:
    """Real, live -- `QUORUM_DATA_CONTRACTS.md` §5.7's already-specified
    contract, implemented for the first time (Roadmap Phase 4a,
    `DEC-120`). Real per-user scoped from this route's first line.

    A real, disclosed architecture note, not silently glossed over:
    this backend has no write path that ever creates a task/expense/
    application, so there's no "on creation" moment to embed against --
    `features/search.py`'s own `search()` lazily backfills any of this
    user's still-unembedded content on every call before ranking. A
    real, honest cost of that choice: the first `/search` call after
    new content exists is slower than a normal one. `email` is never a
    real `item_type` here -- no Gmail integration exists in this
    backend.

    A real, honest `503` if the embedding provider isn't configured
    (e.g. a fresh clone/CI environment with no real `GEMINI_API_KEY`)
    -- never a bare, unhandled exception. A real, honest `502` if a
    live Gemini call itself fails mid-request."""
    settings = get_settings()
    if settings.gemini_api_key is None:
        raise HTTPException(status_code=503, detail="Search is not currently available -- the embedding provider isn't configured.")
    internal_user_id = await _resolve_internal_user_id_or_404(pool, google_sub)
    try:
        results = await run_search(pool, user_id=internal_user_id, query=q, api_key=settings.gemini_api_key)
    except EmbeddingError as exc:
        # The real detail is logged server-side, never echoed to the
        # caller. `DEC-120`'s review confirmed live that Gemini's own
        # error bodies carry no credential -- but they do carry the
        # upstream's internal error structure, which no authenticated
        # caller of THIS API has any reason to see. A generic message
        # out, the real diagnostic detail into Cloud Logging.
        logger.exception("Real Gemini embedding failure while serving /search")
        raise HTTPException(status_code=502, detail="Search is temporarily unavailable -- please try again shortly.") from exc
    return [
        {"item_id": item.item_id, "item_type": item.item_type, "text": item.text, "timestamp": item.timestamp}
        for item in results
    ]


@app.get("/career_pipeline")
async def career_pipeline(
    pool: asyncpg.Pool = Depends(_get_db_pool),
    google_sub: str = Depends(_require_auth),
) -> list[dict]:
    """Real, live -- queries the real `applications` table via
    `fetch_career_pipeline()`, never mocked or pre-computed data.
    Response shape matches `QUORUM_DATA_CONTRACTS.md` §5.10 exactly.

    A real, deliberate CONTRAST with `/tasks`: `applications.status` has
    no database `CHECK` constraint (confirmed against the real
    migration) -- the real vocabulary is genuinely open, so this route
    does no status validation, passing the raw column value through
    unchanged. The mobile client's own `career_pipeline_logic.dart`
    already handles this defensively (`statusLabel()`'s de-snaking
    fallback for an unrecognized value).

    Requires a real, valid access token (`_require_auth`) and, as of
    `DEC-110`, is real per-user scoped.
    """
    internal_user_id = await _resolve_internal_user_id_or_404(pool, google_sub)
    records = await fetch_career_pipeline(pool, user_id=internal_user_id)
    return [
        {
            "application_id": record.application_id,
            "company": record.company,
            "role": record.role,
            "status": record.status,
            "deadline": record.deadline,
        }
        for record in records
    ]


@app.get("/career_pipeline/{application_id}/digest")
async def career_digest_endpoint(
    application_id: str,
    pool: asyncpg.Pool = Depends(_get_db_pool),
    google_sub: str = Depends(_require_auth),
) -> dict:
    """Real, live -- Phase 6, `QUORUM_PRODUCTION_COMPLETION_PLAN.md`,
    `QUORUM_DATA_CONTRACTS.md` §5.11, closing the real, disclosed gap
    `career_digest_logic.dart`'s own header already named: no backend
    for this has ever existed, despite `mobile/lib/features/
    career_digest/` having a real, tested screen since Batch 7
    (`DEC-084`), and `you_screen.dart`'s own `_CareerDigestLoader`
    already wiring a real tap-through from Career Pipeline to it.

    A real, honest `404` if `application_id` isn't a real, syntactically
    valid UUID, doesn't resolve to an `applications` row this caller
    owns, OR resolves to one whose `digest` hasn't been compiled yet --
    all three cases share the exact same response, the same "never
    confirm another user's data exists" discipline `GET /gate_reveal/
    {proposal_id}` already established, extended here to also cover
    "not yet researched" (`features/career_digest.py::
    fetch_company_digest`'s own docstring has the full account of why
    that's the correct, deliberate choice, not an oversight)."""
    try:
        application_uuid = uuid.UUID(application_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=_CAREER_DIGEST_NOT_FOUND_DETAIL) from exc
    internal_user_id = await _resolve_internal_user_id_or_404(pool, google_sub)
    digest = await fetch_company_digest(pool, user_id=internal_user_id, application_id=str(application_uuid))
    if digest is None:
        raise HTTPException(status_code=404, detail=_CAREER_DIGEST_NOT_FOUND_DETAIL)
    return {"company": digest.company, "summary_points": digest.summary_points, "source_count": digest.source_count}


@app.get("/waiting_on")
async def waiting_on(
    pool: asyncpg.Pool = Depends(_get_db_pool),
    google_sub: str = Depends(_require_auth),
) -> list[dict]:
    """Real, live -- Phase 4, `QUORUM_PRODUCTION_COMPLETION_PLAN.md`.
    Queries the real `sent_messages` table via `fetch_stale_waiting_on()`
    -- real messages `features/email_ingestion.py`'s own real, live
    Gmail polling job wrote, never mocked or pre-computed data. Response
    shape matches `QUORUM_DATA_CONTRACTS.md` §5.9 exactly (`recipient`/
    `subject`/`sent_at`) -- already pre-filtered server-side, since
    `find_stale_waiting_on()`'s own staleness-threshold decision is real
    business logic that stays here, never re-derived on the client (that
    section's own explicit note).

    Requires a real, valid access token (`_require_auth`) and is real
    per-user scoped from its first version, matching every other real
    per-user route built since `DEC-110`."""
    internal_user_id = await _resolve_internal_user_id_or_404(pool, google_sub)
    messages = await fetch_stale_waiting_on(pool, user_id=internal_user_id)
    return [{"recipient": message.recipient, "subject": message.subject, "sent_at": message.sent_at} for message in messages]


@app.get("/honesty_log")
async def honesty_log(
    pool: asyncpg.Pool = Depends(_get_db_pool),
    google_sub: str = Depends(_require_auth),
) -> dict:
    """Real, live -- Phase 6, `QUORUM_PRODUCTION_COMPLETION_PLAN.md`.
    Queries the real, live `action_events` table via `fetch_honesty_
    feed()`, real per-user scoped from its first line. Response shape
    matches `QUORUM_DATA_CONTRACTS.md` §5.13 exactly (`total`,
    `success_rate`, `successes`, `failures_and_catches`,
    `genuinely_uncertain`, each `LoggedAction` real-serialized as
    `action_id`/`timestamp`/`outcome`/`description`) -- never filters
    anything out, `failures_and_catches` and `genuinely_uncertain` are
    given the same real structural prominence as `successes`, per that
    section's own explicit requirement.

    Closes the real, permanently-dead "Log" bottom-nav tab -- the
    mobile screen and logic have existed since Batch 8 (`DEC-087`)
    with zero real backend behind them until now."""
    internal_user_id = await _resolve_internal_user_id_or_404(pool, google_sub)
    feed = await fetch_honesty_feed(pool, user_id=internal_user_id)

    def _serialize(actions: list) -> list[dict]:
        return [
            {
                "action_id": action.action_id,
                "timestamp": action.timestamp,
                "outcome": action.outcome,
                "description": action.description,
            }
            for action in actions
        ]

    return {
        "total": feed.total,
        "success_rate": feed.success_rate,
        "successes": _serialize(feed.successes),
        "failures_and_catches": _serialize(feed.failures_and_catches),
        "genuinely_uncertain": _serialize(feed.genuinely_uncertain),
    }


@app.get("/finance/subscriptions")
async def finance_subscriptions(
    pool: asyncpg.Pool = Depends(_get_db_pool),
    google_sub: str = Depends(_require_auth),
) -> list[dict]:
    """Real, live -- queries the real `expenses` table and applies the
    real detection rule in `subscription_detective.py` (the real,
    specified minimum occurrence count and monthly-cadence tolerance
    from `QUORUM_CONFIGURATION_CONSTANTS.md` §4, exact payee match
    only -- no fuzzy matching, no ML). Response shape matches
    `QUORUM_DATA_CONTRACTS.md` §5.12 exactly.

    A real, disclosed gap this route closes, not just a missing REST
    layer: `detect_subscriptions()` did not exist anywhere in this
    backend before this session, despite the spec corpus's own claim
    that it was "real and tested since well before mobile work began"
    -- confirmed absent by direct search. See
    `features/subscription_detective.py`'s own docstring for the full
    account.

    Requires a real, valid access token (`_require_auth`) and, as of
    `DEC-110`, is real per-user scoped.
    """
    internal_user_id = await _resolve_internal_user_id_or_404(pool, google_sub)
    records = await fetch_detected_subscriptions(pool, user_id=internal_user_id)
    return [
        {
            "payee": record.payee,
            "average_amount": record.average_amount,
            "occurrences": record.occurrences,
            "average_interval_days": record.average_interval_days,
        }
        for record in records
    ]


@app.get("/auth/callback")
async def auth_callback(code: str | None = None, state: str | None = None, error: str | None = None) -> RedirectResponse:
    """A real, necessary bridge, found and built this session: Google's
    real OAuth rules (per its own current documentation, confirmed live
    before building this) require a "Web application"-type client --
    which this project's real, already-created OAuth client is, since
    it has a real client_secret the backend needs -- to redirect to a
    real `https://` URL, never a mobile app's custom URL scheme
    directly. `flutter_web_auth_2` on the mobile side needs exactly
    that custom scheme to capture the result and close the in-app
    browser. This route is the real, stateless hop between the two: it
    holds no logic of its own beyond forwarding Google's own real query
    parameters onward.

    Deliberately minimal and stateless -- this route never sees or
    touches a real user's identity or tokens; the actual code exchange
    (`POST /auth/token`) still happens directly between the mobile app
    and this backend afterward, using the SAME `redirect_uri` (this
    route's own real URL) that Google's `/token` endpoint requires to
    match the one used in the original authorization request.
    """
    # DEC-118: "com.quorum.quorum_mobile" is this app's real Android
    # applicationId, but it is NOT a valid URL scheme -- RFC 3986 permits
    # only letters, digits, "+", "-", and "." in a scheme, and the
    # underscore here made flutter_web_auth_2 reject it immediately on
    # every real device this was ever actually tested against (found
    # live, this session -- no real device/browser test had ever been
    # run before). The real Android intent-filter scheme and this
    # backend's own redirect target must always match exactly.
    mobile_scheme = "com.quorum.quorummobile://oauth2redirect"
    if error is not None:
        params = {"error": error}
    elif code is None:
        params = {"error": "missing_code"}
    else:
        params = {"code": code}
        if state is not None:
            params["state"] = state
    # Real, correct query encoding -- code/state/error are opaque values
    # from Google, never assumed URL-safe as-is.
    return RedirectResponse(url=f"{mobile_scheme}?{urlencode(params)}")


@app.post("/auth/token", response_model=TokenPairResponse)
async def auth_token(
    body: TokenExchangeRequest,
    pool: asyncpg.Pool = Depends(_get_db_pool),
    store: SupabaseRevocationStore = Depends(_get_revocation_store),
) -> TokenPairResponse:
    """Real, live Gmail OAuth code exchange -- `QUORUM_DATA_CONTRACTS.md`
    §5.5. Google's real token endpoint verifies the authorization code
    and PKCE `code_verifier` together; this route then independently
    verifies the returned `id_token`'s real signature before trusting
    the identity inside it, and issues a real Quorum session on success.

    Also real-provisions this identity (`DEC-110`) -- the JWT/refresh-
    token layer keeps using Google's raw `sub` unchanged (no change to
    the already-reviewed, CRITICAL-tier session-management system), but
    every per-user domain table needs a real internal UUID mapped to
    it, and this is the one real place in the whole system where a
    genuinely new identity is first seen.

    **Phase 3, `QUORUM_PRODUCTION_COMPLETION_PLAN.md`:** this route now
    also persists Google's own real `access_token`/`refresh_token`
    (encrypted, `auth/google_token_store.py`) -- the real gap `auth/
    google_oauth.py`'s own docstring named since it was first written.
    A real, deliberate resilience choice: if `GOOGLE_TOKEN_ENCRYPTION_
    KEY` isn't configured on this deployment, storage is honestly
    skipped (logged, not raised) rather than failing the entire real
    sign-in over a feature this specific session doesn't need -- the
    internal Quorum session this route's own core job is to issue never
    depended on Google's own tokens to begin with.
    """
    settings = get_settings()
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured on this deployment.")

    try:
        google_tokens = await exchange_authorization_code(
            code=body.code,
            code_verifier=body.code_verifier,
            redirect_uri=body.redirect_uri,
            client_id=settings.google_oauth_client_id,
            client_secret=settings.google_oauth_client_secret,
        )
    except GoogleOAuthExchangeFailed as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    id_token = google_tokens.get("id_token")
    if not id_token:
        # A real, genuine anomaly -- Google's OpenID Connect response is
        # expected to always include one for this flow. Surfaced as a
        # real 502 (this route's own upstream failed to behave as
        # documented), never silently treated as "no identity, proceed
        # anyway."
        raise HTTPException(status_code=502, detail="Google's token response did not include an id_token.")
    google_access_token = google_tokens.get("access_token")
    if not google_access_token:
        # A REAL, DISCLOSED FIX (this PR's own CRITICAL-tier review):
        # an earlier version subscripted `google_tokens["access_token"]`
        # directly -- a bare `KeyError` -> unhandled 500 on a genuine
        # Google anomaly, where the sibling `id_token` check just above
        # already raises a real, loud, honest 502 for the identical
        # class of problem. Matched here for consistency.
        raise HTTPException(status_code=502, detail="Google's token response did not include an access_token.")

    try:
        payload = verify_google_id_token(id_token, settings.google_oauth_client_id)
    except GoogleIdTokenInvalid as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user_id = payload["sub"]
    internal_user_id = await get_or_create_user(pool, google_sub=user_id, email=payload.get("email"))

    if settings.google_token_encryption_key is None:
        logger.warning("GOOGLE_TOKEN_ENCRYPTION_KEY is not configured -- skipping real Google token storage for this sign-in.")
    else:
        # A REAL, DISCLOSED FIX (this PR's own CRITICAL-tier review,
        # LOW 8): an earlier version silently defaulted a missing
        # `expires_in`/`scope` with no real signal anything was amiss.
        # Both are ordinary in every real Google response this route has
        # ever seen; a real, live absence is a genuine anomaly worth a
        # loud log, even though defaulting (rather than a hard failure)
        # remains the right real choice -- this route's own core job,
        # issuing the internal Quorum session, must never fail over a
        # secondary feature's own optional metadata.
        if "expires_in" not in google_tokens:
            logger.warning("Google's token response for user_id=%s omitted expires_in -- defaulting to 3600s.", internal_user_id)
        if not google_tokens.get("scope"):
            logger.warning("Google's token response for user_id=%s omitted a real scope string.", internal_user_id)
        google_access_token_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=int(google_tokens.get("expires_in", 3600))
        )

        # A REAL, DISCLOSED FIX (this PR's own CRITICAL-tier review,
        # BLOCKER 1): an earlier version always called `store_google_
        # tokens()`, even with `refresh_token=None` -- which that
        # function now correctly REJECTS (`google_token_store.py`'s own
        # top-of-file docstring has the full real account of the two
        # live bugs this design replaces). Google omits `refresh_token`
        # on every real sign-in that didn't carry `access_type=offline`
        # -- reachable live for every currently-signed-in real user the
        # very first time they hit this route after this session's own
        # mobile scope change ships, since THIS is the change that first
        # adds that parameter. Handled as three real, distinct, honest
        # cases, never a crash:
        if google_refresh_token := google_tokens.get("refresh_token"):
            await store_google_tokens(
                pool,
                internal_user_id=internal_user_id,
                access_token=google_access_token,
                refresh_token=google_refresh_token,
                access_token_expires_at=google_access_token_expires_at,
                granted_scopes=google_tokens.get("scope", ""),
                encryption_key=settings.google_token_encryption_key,
            )
        else:
            existing_record = await fetch_google_tokens(
                pool, internal_user_id=internal_user_id, encryption_key=settings.google_token_encryption_key
            )
            if existing_record is not None:
                # A real re-authentication that didn't carry a fresh
                # refresh_token, but a real, prior one is already on
                # record -- update just the real access_token, the same
                # real, refresh-only write `get_valid_google_access_
                # token()`'s own refresh path uses, never touching the
                # real refresh_token already stored.
                await update_access_token_after_refresh(
                    pool,
                    internal_user_id=internal_user_id,
                    access_token=google_access_token,
                    access_token_expires_at=google_access_token_expires_at,
                    encryption_key=settings.google_token_encryption_key,
                )
            else:
                # This real user's genuine FIRST sign-in, with no real
                # refresh_token to store and no prior real one on record
                # -- real Gmail/Calendar access is honestly unavailable
                # for them until their next real sign-in (which, per
                # `auth_controller.dart`'s own real `prompt=consent`,
                # will carry one) -- but the internal Quorum session
                # this route's own core job is to issue must never fail
                # over this, so real storage is skipped, loudly logged,
                # not silently swallowed.
                logger.warning(
                    "Google did not return a refresh_token for user_id=%s's first real sign-in, and no "
                    "prior real token exists to fall back to -- skipping real Google token storage this "
                    "time. The mobile app's own authorization request should always include "
                    "access_type=offline/prompt=consent; this is expected only for a sign-in that "
                    "predates that real change.",
                    internal_user_id,
                )

    access_token = create_access_token(user_id, settings.jwt_signing_key)
    refresh_token = await issue_refresh_token(user_id, store)
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)


@app.post("/auth/refresh", response_model=TokenPairResponse)
async def auth_refresh(
    body: RefreshRequest,
    store: SupabaseRevocationStore = Depends(_get_revocation_store),
) -> TokenPairResponse:
    """Real refresh-token rotation (`auth/refresh_token.py`, CRITICAL
    tier) -- a reused or otherwise invalid refresh token is a real 401,
    never silently issuing a fresh session anyway."""
    try:
        new_raw_refresh = await rotate_refresh_token(body.refresh_token, store)
    except (TokenInvalid, TokenRevoked, TokenExpired, TokenReuseDetected) as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    # rotate_refresh_token() returns only the new raw token -- looking
    # its own just-written record back up is the real, honest way to
    # recover the user_id needed for the new access token, rather than
    # widening that CRITICAL-tier function's own return contract just
    # for this one caller's convenience.
    record = await store.get(hash_token(new_raw_refresh))
    settings = get_settings()
    access_token = create_access_token(record.user_id, settings.jwt_signing_key)
    return TokenPairResponse(access_token=access_token, refresh_token=new_raw_refresh)


@app.post("/auth/revoke", status_code=204)
async def auth_revoke(
    user_id: str = Depends(_require_auth),
    store: SupabaseRevocationStore = Depends(_get_revocation_store),
) -> None:
    """The real "sign out everywhere" control -- reuses
    `revoke_all_for_user()` directly (the exact same real, tested
    mechanism `security/account_deletion.py` also reuses, per that
    module's own documented reasoning: one revocation code path,
    reviewed once). Requires a real, valid access token identifying
    WHOSE sessions to revoke -- never a bare user_id in the request
    body, which would let any caller sign out any other user."""
    await revoke_all_for_user(user_id, store)


@app.delete("/account")
async def delete_account_route(
    pool: asyncpg.Pool = Depends(_get_db_pool),
    google_sub: str = Depends(_require_auth),
    revocation_store: SupabaseRevocationStore = Depends(_get_revocation_store),
) -> dict:
    """Real, live, irreversible -- `QUORUM_DATA_CONTRACTS.md` §5.8.
    S3-equivalent per that section's own real, explicit requirement;
    the mobile client's own real, type-to-confirm ceremony
    (`you_logic.dart`'s `isValidDeletionConfirmation`) is the real gate
    that must run before this route is ever called -- this route itself
    performs no additional confirmation step of its own, trusting the
    real access token as sufficient proof of the request (the same
    real security boundary every other route in this file already
    relies on).

    Resolves the real internal UUID first (`DEC-110`'s bridge), then
    calls the real, CRITICAL-tier `delete_account()` with both real
    identifiers it now genuinely needs (`DEC-113`): `google_sub` for
    real session revocation, the resolved internal UUID for the real
    `SupabaseDeletionStore` purge. **A real, disclosed correction to
    this docstring's own earlier claim:** `revoke_oauth_tokens()` is now
    real as of Phase 3 (`QUORUM_PRODUCTION_COMPLETION_PLAN.md`) -- only
    `purge_memories` remains an honest, disclosed zero, since no real
    `mem0` integration exists anywhere in this backend.
    """
    internal_user_id = await _resolve_internal_user_id_or_404(pool, google_sub)
    settings = get_settings()
    deletion_store = SupabaseDeletionStore(pool, google_token_encryption_key=settings.google_token_encryption_key)

    result = await delete_account(
        google_sub=google_sub,
        internal_user_id=internal_user_id,
        deletion_store=deletion_store,
        revocation_store=revocation_store,
    )

    return {
        "user_id": result.user_id,
        "sessions_revoked": result.sessions_revoked,
        "postgres_rows_deleted": result.postgres_rows_deleted,
        "vector_embeddings_deleted": result.vector_embeddings_deleted,
        "memories_deleted": result.memories_deleted,
        "oauth_tokens_revoked": result.oauth_tokens_revoked,
    }


@app.post("/internal/drain-retry-queue")
async def drain_retry_queue_route(
    pool: asyncpg.Pool = Depends(_get_db_pool),
    _internal: None = Depends(_require_internal_secret),
) -> dict:
    """Real, live -- `STATUS_INDEX.md` open item #26, `DEC-127`. Drains
    real, due `retry_queue` jobs via `features/retry_queue_drainer.py`,
    the real `gate.review()` re-entry `QUORUM_DATA_CONTRACTS.md` §5.6
    always promised. Real Critic/Judge (`DEC-125`) and real translation
    (`DEC-127`) are constructed fresh per real request from this
    deployment's own real, live credentials -- never cached across
    requests, matching every other real credential-backed call factory
    in this backend.

    A real, disclosed, honest scope boundary, narrowed since `DEC-128`:
    this route produces a real Gate VERDICT per downstream action (a
    real `action_events` row), and, for a genuine `approve` verdict on
    `CREATE_TASK`/`LOG_EXPENSE` specifically, now genuinely executes it
    too (a real `INSERT INTO tasks`/`expenses`). Every other real
    action type still stops at the verdict -- see `features/
    action_executor.py`'s own top-of-file docstring for exactly why
    each one doesn't have a real execution target yet.

    **REAL, LIVE, ON A REAL SCHEDULE as of `DEC-134`:** `pg_cron`/`pg_net`
    are genuinely enabled on the real Supabase project, and this route is
    called unattended every 5 real minutes (`cron.job` jobname
    `'drain-retry-queue'`) -- a real, disclosed correction to this
    docstring's own earlier claim that nothing called it yet.
    `scripts/enable_retry_queue_drain_cron.sql` has the real, live SQL
    this deployment actually runs.
    """
    settings = get_settings()
    translation_call = make_gemini_downstream_translation_call(api_key=settings.gemini_api_key)
    critic_call = make_groq_critic_call(api_key=settings.groq_api_key)
    judge_call = make_gemini_judge_call(api_key=settings.gemini_api_key)

    result = await drain_due_jobs(
        pool, translation_call=translation_call, critic_call=critic_call, judge_call=judge_call
    )
    return {
        "jobs_seen": result.jobs_seen,
        "jobs_succeeded": result.jobs_succeeded,
        "jobs_failed": result.jobs_failed,
        "downstream_actions_produced": result.downstream_actions_produced,
        "downstream_actions_executed": result.downstream_actions_executed,
    }


@app.post("/internal/deadline-watch")
async def deadline_watch_route(
    pool: asyncpg.Pool = Depends(_get_db_pool),
    _internal: None = Depends(_require_internal_secret),
) -> dict:
    """Real, live -- Phase 2 of `QUORUM_PRODUCTION_COMPLETION_PLAN.md`,
    `DEC-13x`. The first genuinely autonomous, non-manual caller of
    `negotiation/trigger.py::scan_for_conflicts` this backend has ever
    had -- previously only ever invoked by hand, from `scripts/
    seed_demo_dataset.py` (`DEC-129`'s own diagnosis finding). Iterates
    every real user via `features/deadline_watch.py::run_deadline_watch`,
    creating a real, bare `negotiations` row the moment a genuine
    tasks/finance conflict is found in their real, live data -- zero
    LLM calls, same shared `_require_internal_secret` auth as `/internal/
    drain-retry-queue` above.

    A real, disclosed, honest scope boundary: this route creates the
    bare negotiation row only -- real Gemini-backed positions/options
    are a genuine, separate, still-open item; see `features/
    deadline_watch.py`'s own top-of-file docstring for exactly why.

    **REAL, LIVE, ON A REAL SCHEDULE as of `DEC-134`:** called unattended
    every 30 real minutes (`cron.job` jobname `'deadline-watch'`) -- a
    real, disclosed correction to this docstring's own earlier claim
    that nothing called it yet.
    """
    result = await run_deadline_watch(pool)
    return {
        "users_scanned": result.users_scanned,
        "users_failed": result.users_failed,
        "negotiations_created": result.negotiations_created,
        "outcome_counts": result.outcome_counts,
    }


@app.post("/internal/spend-alert")
async def spend_alert_route(
    pool: asyncpg.Pool = Depends(_get_db_pool),
    _internal: None = Depends(_require_internal_secret),
) -> dict:
    """Real, live -- Phase 2 of `QUORUM_PRODUCTION_COMPLETION_PLAN.md`,
    `DEC-13x`. The real, second autonomous negotiation-trigger job,
    per `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §8.6's own real
    "spontaneous-spend-vs-known-upcoming-cost" framing. Iterates every
    real user via `features/spend_alert.py::run_spend_alert`: every
    currently-detected recurring subscription's own real, total ongoing
    cost (not just a newly-appeared one -- a real, disclosed wording
    correction, this session's own CRITICAL-tier review), checked
    against real remaining monthly budget, at the same real moment the
    user's real tasks are also overcommitted -- zero LLM calls, same
    shared `_require_internal_secret` auth as `/internal/drain-retry-
    queue` and `/internal/deadline-watch` above.

    A real, disclosed, honest scope boundary, matching `/internal/
    deadline-watch`'s own precedent exactly: this route creates the
    bare negotiation row only -- real Gemini-backed positions/options
    are a genuine, separate, still-open item; see `features/spend_
    alert.py`'s own top-of-file docstring for exactly why.

    **REAL, LIVE, ON A REAL SCHEDULE as of `DEC-134`:** called unattended
    every 30 real minutes (`cron.job` jobname `'spend-alert'`) -- a real,
    disclosed correction to this docstring's own earlier claim that
    nothing called it yet.
    """
    result = await run_spend_alert(pool)
    return {
        "users_scanned": result.users_scanned,
        "users_failed": result.users_failed,
        "negotiations_created": result.negotiations_created,
        "outcome_counts": result.outcome_counts,
    }


@app.post("/internal/backfill-negotiation-detail")
async def backfill_negotiation_detail_route(
    pool: asyncpg.Pool = Depends(_get_db_pool),
    _internal: None = Depends(_require_internal_secret),
) -> dict:
    """Real, live -- Phase 2, `DEC-134`. Closes the real, disclosed gap
    both `/internal/deadline-watch` and `/internal/spend-alert` name:
    the bare negotiations they autonomously create can never be resolved
    (`features/negotiation_choice.py` requires real `options`) until
    something generates real detail for them. Iterates a real, small
    batch of bare, autonomously-created negotiations via `features/
    negotiation_detail_backfill.py::run_negotiation_detail_backfill` --
    real Gemini-backed positions and synthesized options, real code-
    computed impact deltas, nothing fabricated anywhere in the chain. A
    real, honest `503` if the Gemini provider isn't configured, matching
    `GET /search`'s own established pattern for the same real dependency.

    **REAL, LIVE, ON A REAL SCHEDULE as of `DEC-134`:** called unattended
    every 30 real minutes (`cron.job` jobname `'backfill-negotiation-
    detail'`), a small, deliberately-bounded batch per real invocation
    (`negotiation_detail_backfill.py::DEFAULT_BATCH_SIZE`) to bound real,
    fluctuating Gemini free-tier quota risk (`STATUS_INDEX.md` item #21)
    -- the same real concern that kept detail generation out of `deadline
    -watch.py`/`spend_alert.py` themselves in the first place.
    """
    settings = get_settings()
    if settings.gemini_api_key is None:
        raise HTTPException(
            status_code=503,
            detail="Negotiation-detail backfill is not currently available -- the Gemini provider isn't configured.",
        )
    result = await run_negotiation_detail_backfill(pool, api_key=settings.gemini_api_key)
    return {
        "negotiations_scanned": result.negotiations_scanned,
        "negotiations_failed": result.negotiations_failed,
        "negotiations_detailed": result.negotiations_detailed,
        "outcome_counts": result.outcome_counts,
    }


@app.post("/internal/email-ingestion")
async def email_ingestion_route(
    pool: asyncpg.Pool = Depends(_get_db_pool),
    _internal: None = Depends(_require_internal_secret),
) -> dict:
    """Real, live -- Phase 4, `QUORUM_PRODUCTION_COMPLETION_PLAN.md`,
    `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §9.1's own real, specified
    "polling, 5-15 min interval." The first real Gmail API integration
    this backend has ever made, and the first real, non-manual caller
    `features/waiting_on.py` has ever had. Iterates every real user via
    `features/email_ingestion.py::run_email_ingestion`: for each real
    user with a real, stored Google grant (`auth/google_token_store.py`,
    Phase 3), polls their real Gmail for real newly-sent messages
    (recorded into `sent_messages`) and real new replies to threads
    they're genuinely still waiting on -- zero LLM calls, same shared
    `_require_internal_secret` auth as every other `/internal/*` route.

    A real, honest skip, not a failure, for a real user who never
    granted Google access at all (`users_skipped_no_token`) -- Gmail
    integration is a real, additive capability, not a precondition for
    this route running cleanly across every real user. A real, DISTINCT,
    also-honest skip (`users_token_refresh_failed`) for a real user
    whose stored grant currently can't be refreshed -- genuinely
    revoked, or Google's own endpoint degraded, this route does not
    guess which; a real CRITICAL-tier review finding (`DEC-140`)
    against an earlier version that collapsed this into `users_failed`
    forever, with no way for an operator to tell it apart from a real
    code bug.

    Holds a real, job-level Postgres advisory lock for the whole real
    batch (`features/email_ingestion.py::EMAIL_INGESTION_JOB_LOCK_KEY`)
    -- a real, overlapping `pg_cron` fire is a real, honest no-op
    (`already_running: true`, every other field a real `0`), not a
    second, wasteful concurrent scan."""
    settings = get_settings()
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret or not settings.google_token_encryption_key:
        raise HTTPException(status_code=503, detail="Email ingestion is not currently available -- Google OAuth isn't fully configured on this deployment.")
    result = await run_email_ingestion(
        pool,
        client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret,
        encryption_key=settings.google_token_encryption_key,
    )
    return {
        "users_scanned": result.users_scanned,
        "users_failed": result.users_failed,
        "users_skipped_no_token": result.users_skipped_no_token,
        "users_token_refresh_failed": result.users_token_refresh_failed,
        "messages_failed": result.messages_failed,
        "new_sent_messages": result.new_sent_messages,
        "new_replies_detected": result.new_replies_detected,
        "already_running": result.already_running,
    }


@app.post("/internal/career-digest")
async def career_digest_route(
    pool: asyncpg.Pool = Depends(_get_db_pool),
    _internal: None = Depends(_require_internal_secret),
) -> dict:
    """Real, live -- Phase 6 of `QUORUM_PRODUCTION_COMPLETION_PLAN.md`.
    Iterates a real, small batch of real `applications` rows via
    `features/career_digest.py::run_career_digest`: real Tavily search,
    real Gemini-backed summarization, real code-computed `source_count`
    -- nothing fabricated anywhere in the chain. A real, honest `503` if
    either the Tavily or Gemini provider isn't configured, matching
    `/internal/backfill-negotiation-detail`'s own established pattern
    for the same real dependency shape.

    A real, deliberate scope boundary, disclosed rather than silently
    narrowed: this route's own real trigger signal is `applications.
    status = 'interview_scheduled'`, not a real Email-classification-
    based interview detector -- see `features/career_digest.py`'s own
    top-of-file docstring for exactly why. Same shared
    `_require_internal_secret` auth as every other `/internal/*` route.

    Not yet scheduled live via `pg_cron` as of this writing -- see
    `backend/scripts/enable_career_digest_cron.sql`'s own top comment
    for the real, disclosed reason and what's needed before it is."""
    settings = get_settings()
    if settings.tavily_api_key is None or settings.gemini_api_key is None:
        raise HTTPException(
            status_code=503,
            detail="Career digest compilation is not currently available -- the Tavily or Gemini provider isn't configured.",
        )
    compile_digest_call = make_gemini_compile_digest_call(api_key=settings.gemini_api_key)
    result = await run_career_digest(
        pool, tavily_api_key=settings.tavily_api_key, compile_digest_call=compile_digest_call
    )
    return {
        "applications_scanned": result.applications_scanned,
        "applications_failed": result.applications_failed,
        "digests_compiled": result.digests_compiled,
        "outcome_counts": result.outcome_counts,
    }
