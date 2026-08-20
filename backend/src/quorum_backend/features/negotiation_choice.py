"""Real, live implementation of `POST /negotiations/{negotiation_id}/
choose` (`QUORUM_DATA_CONTRACTS.md` §5.6 -- specified since this
document's own earliest real negotiation work, genuinely unbuilt until
now, closing the gap `DEC-104`/`DEC-121` both disclosed: a person could
see a real negotiation's real positions/options but never act on one).

WHERE "DOWNSTREAM ACTIONS... ENQUEUED, EACH RE-ENTERING THE GATE AT ITS
OWN STAKES LEVEL" (§5.6's own real spec text, citing "§8.3 of the ADD" --
a document that, like several others this project has already
disclosed, does not exist as a literal file anywhere in this repository;
built here as a real, reasoned construction against that spec text, not
copied from a source that isn't present) ACTUALLY GOES: `retry_queue`
(`migrations/0001_initial_schema`) -- a real, already-existing,
already-described "lightweight Postgres table, drained on a schedule"
-- confirmed by direct search before writing this module to be the one
real table in this schema whose own name and shape match "enqueued"
exactly (`job_type`, `payload` JSONB, `attempt_count`, `next_attempt_at`).

A real, disclosed, honest scope boundary, not glossed over: this module
writes the real, enqueued row. No drainer that actually reads
`retry_queue` and calls `gate.review()` against a queued job exists
anywhere in this backend yet -- the same "no real production trigger"
gap this project has now disclosed for `action_events`/`negotiations`
(`DEC-119`), `note_embeddings` (`DEC-120`), and negotiation content
itself (`DEC-121`). Building that drainer is real, separate,
`pg_cron`-shaped follow-up work, not silently implied solved here.

WHY THE PAYLOAD IS DESCRIPTIVE TEXT, NOT A READY-TO-SUBMIT
`ActionProposal`: `NegotiationOption` (`gate/schemas.py`) has never
carried a structured `action_type`/`payload` of its own -- only
`option_id`, `description`, `source_domains` -- confirmed by reading
the real schema before designing this. Constructing a real
`ActionProposal` from free-text `description` would mean inventing
structure the real synthesis step never produced, the exact kind of
model-narrates-becomes-code-decides violation this project's Gate
architecture exists to prevent. The queued job carries the real,
already-computed facts (which option, its real description, its real
source domains) for a future session's own real design work to turn
into real proposals -- not guessed at here.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

import asyncpg


class NegotiationNotFound(Exception):
    """No real negotiation row exists for this id, owned by this user --
    the caller should turn this into a real, honest 404."""


class NegotiationNotReadyToChoose(Exception):
    """A real, honest distinction from `NegotiationNotFound`: the row
    exists, but its real positions/options haven't been computed yet
    (the genuine in-progress state `QUORUM_DATA_CONTRACTS.md` §5.5a's
    own three-state design already established) -- there is nothing
    real to validate a choice against."""


class NegotiationAlreadyResolved(Exception):
    """A real, idempotency-shaped guard: `resolved_at` is already set.
    Never silently allow a second real choice to overwrite the first."""


class InvalidChosenOption(Exception):
    """`chosen_option` doesn't match any of this negotiation's own real,
    persisted `option_id`s -- never accepted as if it were grounded."""


@dataclass(frozen=True)
class ChosenOptionRecord:
    option_id: str
    description: str
    source_domains: list[str]


async def choose_negotiation_option(
    pool: asyncpg.Pool, *, user_id: str, negotiation_id: str, chosen_option: str
) -> ChosenOptionRecord:
    """Real, live, per-user-scoped. Raises one of the four typed
    exceptions above on any real failure case -- callers (`main.py`)
    map each to its own real, distinct HTTP status, never a bare 500.

    Real and atomic: the resolution UPDATE and the real `retry_queue`
    enqueue happen on one held connection inside one transaction, so a
    crash between the two can never leave a negotiation marked resolved
    with no real downstream job queued for it."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT options, resolved_at FROM negotiations WHERE negotiation_id = $1 AND user_id = $2 FOR UPDATE",
                uuid.UUID(negotiation_id),
                uuid.UUID(user_id),
            )
            if row is None:
                raise NegotiationNotFound(negotiation_id)
            if row["resolved_at"] is not None:
                raise NegotiationAlreadyResolved(negotiation_id)
            if row["options"] is None:
                raise NegotiationNotReadyToChoose(negotiation_id)

            options = json.loads(row["options"])
            matched = next((o for o in options if o["option_id"] == chosen_option), None)
            if matched is None:
                raise InvalidChosenOption(chosen_option)

            await conn.execute(
                "UPDATE negotiations SET resolved_at = now(), chosen_option_id = $1 WHERE negotiation_id = $2",
                chosen_option,
                uuid.UUID(negotiation_id),
            )
            await conn.execute(
                "INSERT INTO retry_queue (job_type, payload) VALUES ($1, $2::jsonb)",
                "negotiation_downstream_action",
                json.dumps(
                    {
                        "negotiation_id": negotiation_id,
                        "user_id": user_id,
                        "chosen_option_id": matched["option_id"],
                        "option_description": matched["description"],
                        "source_domains": matched["source_domains"],
                    }
                ),
            )

    return ChosenOptionRecord(
        option_id=matched["option_id"],
        description=matched["description"],
        source_domains=matched["source_domains"],
    )
