"""Real, live persistence and retrieval for `GET /negotiations/{id}`
(`QUORUM_DATA_CONTRACTS.md` §5.5a -- written this session, since no real
contract for viewing a negotiation's positions/options ever existed
anywhere, confirmed by direct search before writing either the spec
section or this module).

A real, disclosed design choice: `positions`/`options` are stored as
JSONB snapshots on `negotiations` (`migrations/0006_negotiation_detail`),
not normalized into their own tables. A negotiation's positions/options
are the real, immutable output of one real run of the negotiation
subgraph (trigger -> positions -> synthesis -> impact simulation) --
there's no real use case for querying into individual fields across
negotiations, matching the same precedent `action_events.payload`
already established in this backend.

`options` merges each real `NegotiationOption` with its own real
`ImpactDelta` list at persistence time -- the subgraph's own real output
keeps these as two separate pieces (`options: list[NegotiationOption]`,
`impact: dict[str, list[ImpactDelta]]` keyed by `option_id`, confirmed
by reading `negotiation/subgraph.py` before designing this), but the
mobile `NegotiationOptionData` (`negotiation_logic.dart`) has always
expected `impact` to live directly on each option -- merging at write
time, once, is simpler than re-joining on every real read.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

import asyncpg

from quorum_backend.gate.schemas import ImpactDelta, NegotiationOption, Position


@dataclass(frozen=True)
class NegotiationDetail:
    positions: list[dict]
    options: list[dict]
    # RESOLVED, a real, disclosed gap found on-device (Session 2,
    # `QUORUM_FINAL_COMPLETION_PLAN.md`, `DEC-168`): this route never
    # returned whether a negotiation was already resolved at all --
    # `negotiations.resolved_at`/`chosen_option_id` existed on the real
    # schema since `DEC-123` but were never selected here, so a real
    # user re-opening an already-decided negotiation saw the exact same
    # fully-interactive, all-options-tappable screen as a genuinely open
    # one, discovering the truth only via a real, honest `409` AFTER
    # tapping "Choose this option" again -- confusing, not dishonest
    # (the 409 itself was always correct), but a real gap in when the
    # client learns the truth, not just how it's phrased once it does.
    resolved_at: str | None
    chosen_option_id: str | None


async def persist_negotiation_detail(
    pool: asyncpg.Pool,
    *,
    negotiation_id: str,
    positions: list[Position],
    options: list[NegotiationOption],
    impact: dict[str, list[ImpactDelta]],
) -> None:
    """Real, live write -- called once, right after a real negotiation
    subgraph run produces real positions/options/impact (currently only
    from the demo-dataset seed script; no production trigger exists yet
    to call this from a real user action, the same disclosed gap
    `DEC-119`'s own `/today` work already found for `action_events`/
    `negotiations` generally)."""
    positions_json = json.dumps([p.model_dump(mode="json") for p in positions])
    options_json = json.dumps(
        [
            {**option.model_dump(mode="json"), "impact": [d.model_dump(mode="json") for d in impact.get(option.option_id, [])]}
            for option in options
        ]
    )
    await pool.execute(
        "UPDATE negotiations SET positions = $1::jsonb, options = $2::jsonb WHERE negotiation_id = $3",
        positions_json,
        options_json,
        uuid.UUID(negotiation_id),
    )


async def fetch_negotiation_detail(pool: asyncpg.Pool, *, user_id: str, negotiation_id: str) -> NegotiationDetail | None:
    """Real, live, per-user-scoped read. Returns `None` on a genuine
    `404` case (no row, or a row owned by someone else -- indistinguishable
    on purpose, the same "never confirm another user's data exists"
    discipline every other real per-user route in this backend already
    holds itself to). A row that exists but has no detail computed yet
    (a real, honest in-progress state, §5.5a) returns real empty lists,
    never `None` -- only a caller with no real, owned row at all gets
    `None`."""
    row = await pool.fetchrow(
        "SELECT positions, options, resolved_at, chosen_option_id FROM negotiations WHERE negotiation_id = $1 AND user_id = $2",
        uuid.UUID(negotiation_id),
        uuid.UUID(user_id),
    )
    if row is None:
        return None
    # asyncpg returns a real JSONB column as a plain string by default
    # (no custom codec registered anywhere in core/db.py, the same real
    # fact every other JSONB-reading module in this backend has already
    # confirmed) -- a NULL column comes back as a real Python None, not
    # the string "null".
    positions = json.loads(row["positions"]) if row["positions"] is not None else []
    options = json.loads(row["options"]) if row["options"] is not None else []
    # `resolved_at` comes back as a real `datetime` -- serialized to a
    # real ISO 8601 string here, matching every other real timestamp
    # this backend hands to the mobile client (never a raw asyncpg
    # object leaking into a JSON response).
    resolved_at = row["resolved_at"].isoformat() if row["resolved_at"] is not None else None
    return NegotiationDetail(
        positions=positions, options=options, resolved_at=resolved_at, chosen_option_id=row["chosen_option_id"]
    )
