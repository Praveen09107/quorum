"""Quorum backend — FastAPI application entry point.

Originally deliberately minimal (/health only) per Phase 0's own
kickoff-guide finding -- no import of gate/, router.py, agents/, or
auth/. That was real, disclosed, deliberately-later work
(QUORUM_IMPLEMENTATION_STRATEGY.md Phase 3), and Phase 3 Part B is
where the first of it lands: a real, live `GET /trust_digest`, backed
by a real Postgres connection pool (`core/db.py`), not a stub.

Real, minimal integration of `core/config.py` (Phase 0's own settings
module), added the same session it was built: a real startup-time check,
not just an unreferenced file. If a real deployment ever boots with the
known, public, insecure default JWT signing key still in place, that's
loudly logged now -- a real safety net for exactly the "someone forgot
to set a real secret" failure mode, without going further and refusing
to start (auth routes don't exist yet to protect; that's real,
deliberately later work).
"""
import logging
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import AsyncIterator

import asyncpg
from fastapi import Depends, FastAPI, HTTPException, Request

from quorum_backend.core import db
from quorum_backend.core.config import get_settings
from quorum_backend.features.trust_digest import fetch_trust_digest

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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/trust_digest")
async def trust_digest(pool: asyncpg.Pool = Depends(_get_db_pool)) -> dict:
    """Real, live -- queries the real `action_events` table via
    `fetch_trust_digest()`, never mocked or pre-computed data. Response
    shape matches `QUORUM_DATA_CONTRACTS.md` §5.15 exactly."""
    result = await fetch_trust_digest(pool)
    return {
        "current_week": asdict(result.current_week),
        "previous_week": asdict(result.previous_week) if result.previous_week is not None else None,
        "trend": result.trend,
        "delta": result.delta,
    }
