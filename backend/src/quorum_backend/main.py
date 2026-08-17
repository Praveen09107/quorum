"""Quorum backend — FastAPI application entry point.

Deliberately minimal, per this batch's own kickoff-guide finding: /health
only. No import of gate/, router.py, agents/, or auth/ yet -- every one of
those is real and tested standalone, but wiring them into the running
application is real, separate, deliberately-later work
(QUORUM_IMPLEMENTATION_STRATEGY.md Phase 3), not folded into this
infrastructure session.
"""
from fastapi import FastAPI

app = FastAPI(title="Quorum Backend")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
