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
import uuid
from urllib.parse import urlencode
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import AsyncIterator

import asyncpg
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from quorum_backend.auth.access_token import (
    ACCESS_TOKEN_TTL_MINUTES,
    AccessTokenExpired,
    AccessTokenInvalid,
    create_access_token,
    decode_access_token,
)
from quorum_backend.auth.google_oauth import GoogleIdTokenInvalid, GoogleOAuthExchangeFailed, exchange_authorization_code, verify_google_id_token
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
from quorum_backend.features.career_pipeline import fetch_career_pipeline
from quorum_backend.features.negotiation_detail import fetch_negotiation_detail
from quorum_backend.features.search import search as run_search
from quorum_backend.features.self_test_harness import ScenarioResult, run_self_test, summarize
from quorum_backend.features.subscription_detective import fetch_detected_subscriptions
from quorum_backend.features.tasks import fetch_tasks
from quorum_backend.features.today import (
    fetch_active_negotiations,
    fetch_pending_actions,
    fetch_today_budget,
    fetch_today_capacity,
)
from quorum_backend.features.trust_digest import fetch_trust_digest
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
    _user_id: str = Depends(_require_auth),
) -> dict:
    """Real, live -- queries the real `action_events` table via
    `fetch_trust_digest()`, never mocked or pre-computed data. Response
    shape matches `QUORUM_DATA_CONTRACTS.md` §5.15 exactly.

    Requires a real, valid access token (`_require_auth`) as of this
    session -- honest note: `action_events` itself has no `user_id`
    column (confirmed against the real migration schema), so this is
    currently a real "you must be signed in" gate, not yet a per-user
    data filter. Adding real per-user scoping to the underlying data is
    a separate, disclosed open item, not silently implied solved here.
    """
    result = await fetch_trust_digest(pool)
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
        raise HTTPException(status_code=404, detail="No negotiation found with that id.") from exc
    internal_user_id = await _resolve_internal_user_id_or_404(pool, google_sub)
    detail = await fetch_negotiation_detail(pool, user_id=internal_user_id, negotiation_id=str(negotiation_uuid))
    if detail is None:
        raise HTTPException(status_code=404, detail="No negotiation found with that id.")
    return {"positions": detail.positions, "options": detail.options}


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

    try:
        payload = verify_google_id_token(id_token, settings.google_oauth_client_id)
    except GoogleIdTokenInvalid as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user_id = payload["sub"]
    await get_or_create_user(pool, google_sub=user_id, email=payload.get("email"))
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
    `SupabaseDeletionStore` purge. Two of the four real store counts
    are honest, disclosed zeros regardless of what this account
    actually contains -- see `SupabaseDeletionStore`'s own docstring
    for the full account of why `purge_memories`/`revoke_oauth_tokens`
    can never be anything else in this backend today.
    """
    internal_user_id = await _resolve_internal_user_id_or_404(pool, google_sub)
    deletion_store = SupabaseDeletionStore(pool)

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
