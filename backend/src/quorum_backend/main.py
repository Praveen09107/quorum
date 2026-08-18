"""Quorum backend — FastAPI application entry point.

Deliberately minimal, per this batch's own kickoff-guide finding: /health
only. No import of gate/, router.py, agents/, or auth/ yet -- every one of
those is real and tested standalone, but wiring them into the running
application is real, separate, deliberately-later work
(QUORUM_IMPLEMENTATION_STRATEGY.md Phase 3), not folded into this
infrastructure session.

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
from typing import AsyncIterator

from fastapi import FastAPI

from quorum_backend.core.config import get_settings

logger = logging.getLogger("quorum_backend")


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.is_using_insecure_default_jwt_signing_key:
        logger.warning(
            "JWT_SIGNING_KEY is still the real, public, insecure default "
            '("change-me-in-real-deployment") -- set a real secret via '
            "the environment or .env before this deployment issues any "
            "real access token."
        )
    yield


app = FastAPI(title="Quorum Backend", lifespan=_lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
