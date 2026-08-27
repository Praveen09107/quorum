"""Real Gate Reveal (Phase 6, `QUORUM_PRODUCTION_COMPLETION_PLAN.md`)
-- backs `GET /gate_reveal/{proposal_id}`, closing the real, disclosed
gap `DEC-126` found: no `findings`/`objections` persistence or backend
route ever existed for this, despite `mobile/lib/features/gate_reveal/`
having real, tested logic and a real screen since Batch 6 (`DEC-080`),
and `mobile/lib/shell/main_shell.dart`'s own `_TodayTab` already wiring
a real tap-through from a "Needs you now" card to it.

REAL DATA SOURCE: `retry_queue_drainer.py::_persist_verdict()` now
writes the real Gate's own `findings`/`objections` (migration `0013`)
onto the exact same `action_events` row it already creates for every
real, downstream-translated action -- no new table, no duplicated
identity. `findings`/`objections` are both nullable (real rows written
before migration `0013` have neither) -- a genuinely missing column
value is treated the same as a real, honest empty list, never an
error.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

import asyncpg


@dataclass(frozen=True)
class GateRevealBundle:
    findings: list[dict]
    objections: list[dict]


async def fetch_gate_reveal(pool: asyncpg.Pool, *, user_id: str, proposal_id: str) -> GateRevealBundle | None:
    """Real, live, per-user-scoped lookup. Returns `None` honestly when
    `proposal_id` doesn't resolve to a real `action_events` row this
    exact user owns -- the caller (the real route) is responsible for
    turning that into a real `404`, the same "never confirm another
    user's data exists" discipline `GET /negotiations/{negotiation_id}`
    already established.

    Each real `Finding`/`Objection` is returned exactly as `gate.
    review()` itself serialized it (`Pydantic.model_dump()`, written by
    `retry_queue_drainer.py`) -- plain JSON objects with the real,
    already-specified field names (`validator`/`claim`/`evidence_state`/
    ...; `category`/`severity`/`description`/`signed_off`/...), never
    re-shaped here. The real client-side mapping from `evidence_state`
    to a visual state already exists and is already tested
    (`gate_reveal_logic.dart::visualStateForEvidence()`)."""
    row = await pool.fetchrow(
        "SELECT findings, objections FROM action_events WHERE proposal_id = $1 AND user_id = $2",
        uuid.UUID(proposal_id),
        uuid.UUID(user_id),
    )
    if row is None:
        return None
    findings = json.loads(row["findings"]) if row["findings"] is not None else []
    objections = json.loads(row["objections"]) if row["objections"] is not None else []
    return GateRevealBundle(findings=findings, objections=objections)
