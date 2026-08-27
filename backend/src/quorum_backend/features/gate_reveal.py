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
value is returned as a real `None`, deliberately NOT collapsed into an
empty list. Collapsing "we never recorded this" into "the Gate found
nothing" would be the exact same mistake `Finding.evidence_state`'s own
three-valued discipline (`no_data_found` vs. a real pass/fail) exists
to rule out (CRITICAL-tier review, `DEC-146`) -- an empty list is a
real, positive claim ("Stage A ran and found zero findings"), which is
not what a pre-migration row means.

`stakes` is included on every real bundle because "did Stage B run" is
a genuinely different question from "is the objections list non-empty"
-- a CRITICAL-tier review finding (`DEC-146`) that this module's first
version got wrong. `gate/orchestration.py::run_stage_b()` only calls
the real Critic for S3; an S2 verdict reaches the real Judge directly
with `objections == []` and the Judge never fabricates a sign-off entry
on an empty input (`gate/llm_calls.py`). So a real, live S2 action that
the Judge genuinely reviewed -- possibly escalating it to a human --
can carry an honestly empty `objections` list, and the caller must not
read that as "Stage B never ran." `stakes` (S0/S1/S2/S3) is the real,
structural signal for that, exactly the same way `router.STAKES_TABLE`
is itself a hardcoded lookup rather than an inference from the data.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

import asyncpg


@dataclass(frozen=True)
class GateRevealBundle:
    stakes: str
    findings: list[dict] | None
    objections: list[dict] | None


async def fetch_gate_reveal(pool: asyncpg.Pool, *, user_id: str, proposal_id: str) -> GateRevealBundle | None:
    """Real, live, per-user-scoped lookup. Returns `None` honestly when
    `proposal_id` doesn't resolve to a real `action_events` row this
    exact user owns -- the caller (the real route) is responsible for
    turning that into a real `404`, the same "never confirm another
    user's data exists" discipline `GET /negotiations/{negotiation_id}`
    already established.

    Each real `Finding`/`Objection` is returned exactly as `gate.
    review()` itself serialized it (`Pydantic.model_dump(mode="json")`,
    written by `retry_queue_drainer.py`) -- plain JSON objects with the
    real, already-specified field names (`validator`/`claim`/
    `evidence_state`/...; `category`/`severity`/`description`/
    `signed_off`/...), never re-shaped here. The real client-side
    mapping from `evidence_state` to a visual state already exists and
    is already tested (`gate_reveal_logic.dart::visualStateForEvidence()`).

    `findings`/`objections` are `None`, not `[]`, on a real row written
    before migration `0013` -- see this module's own header for why
    that distinction is load-bearing, not pedantry."""
    row = await pool.fetchrow(
        "SELECT stakes, findings, objections FROM action_events WHERE proposal_id = $1 AND user_id = $2",
        uuid.UUID(proposal_id),
        uuid.UUID(user_id),
    )
    if row is None:
        return None
    findings = json.loads(row["findings"]) if row["findings"] is not None else None
    objections = json.loads(row["objections"]) if row["objections"] is not None else None
    return GateRevealBundle(stakes=row["stakes"], findings=findings, objections=objections)
