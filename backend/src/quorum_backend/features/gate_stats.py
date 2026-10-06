"""Real Gate statistics (`DEC-193`, product rebuild Block E) -- backs
`GET /gate/stats`, the numbers half of the Gate showcase page.

Real, per-user scoped, computed fresh from `action_events` on every
call -- the same architecture `agent_telemetry.py` already established
in `DEC-192`, applied here to a different real question: not "how is
each agent doing" but "how is the Gate itself performing, across every
agent." Reuses the exact same real outcome partition `honesty_log.py`
established and `agent_telemetry.py` already reused, rather than a
third, independently-derived copy.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field

import asyncpg

from quorum_backend.features.honesty_log import FAILURE_OUTCOMES, SUCCESS_OUTCOMES, UNCERTAIN_OUTCOMES


@dataclass(frozen=True)
class GateStats:
    """Real, honest Gate-wide stats for one real user. `stakes_counts`
    is keyed by the real stakes string (`"S0"`-`"S3"`) over every real
    resolved action, regardless of outcome -- a real, honest picture of
    which tier of decision this user's own agents actually make, not
    just whether those decisions succeeded."""

    total_resolved: int = 0
    stakes_counts: dict[str, int] = field(default_factory=dict)
    success_count: int = 0
    caught_count: int = 0
    rejected_count: int = 0
    uncertain_count: int = 0

    # How many of this user's own resolved actions genuinely carry a
    # recorded Gate timeline (`DEC-190`, migration `0021`) -- real,
    # honest context for `stage_b_ran_count`/`revision_count` below,
    # since neither is meaningful for a row that predates that
    # migration or was never processed through a timeline-aware path
    # (e.g. the negotiation-downstream drainer).
    rows_with_recorded_timeline: int = 0
    stage_b_ran_count: int = 0
    revised_count: int = 0

    @property
    def catch_rate(self) -> float | None:
        """Mirrors `agent_telemetry.py`'s own identical real precedent:
        `uncertain_count` excluded from both numerator and denominator.
        `None`, never a fabricated `0.0`, when there is nothing real to
        compute a rate from."""
        resolved = self.total_resolved - self.uncertain_count
        if resolved <= 0:
            return None
        return round(self.caught_count / resolved, 3)


async def fetch_gate_stats(pool: asyncpg.Pool, *, user_id: str) -> GateStats:
    """The real, live query -- every real, resolved `action_events` row
    for this user, matching `trust_digest.py`'s/`agent_telemetry.py`'s
    own established `outcome IS NOT NULL` convention."""
    rows = await pool.fetch(
        "SELECT stakes, outcome, revision_count, gate_timeline "
        "FROM action_events WHERE user_id = $1 AND outcome IS NOT NULL",
        uuid.UUID(user_id),
    )

    stakes_counts: dict[str, int] = {}
    success = caught = rejected = uncertain = 0
    rows_with_timeline = stage_b_ran = revised = 0

    for row in rows:
        stakes_counts[row["stakes"]] = stakes_counts.get(row["stakes"], 0) + 1

        if row["outcome"] in SUCCESS_OUTCOMES:
            success += 1
        elif row["outcome"] in FAILURE_OUTCOMES and row["outcome"] != "rejected_by_user":
            caught += 1
        elif row["outcome"] == "rejected_by_user":
            rejected += 1
        elif row["outcome"] in UNCERTAIN_OUTCOMES:
            uncertain += 1

        timeline = row["gate_timeline"]
        if timeline is not None:
            rows_with_timeline += 1
            # The real, EXACT fact, not a proxy -- `gate/timeline.py::
            # GateTimeline.finish()` already records a real `done` event
            # carrying `stage_b_ran: bool`, computed there from whether
            # a real `stage_b.judge` event genuinely fired for THIS
            # specific row (correctly `False` when Stage A hard-failed
            # a real S2/S3 proposal and short-circuited Stage B, which
            # a stakes-tier-only guess could not distinguish). asyncpg
            # returns JSONB as a bare string with no codec registered
            # -- confirmed directly rather than assumed, the same real
            # trap `main.py`'s own `_json_column()` helper already
            # guards against for this identical column.
            events = json.loads(timeline) if isinstance(timeline, str) else timeline
            done_event = next((e for e in events if e.get("event") == "done"), None)
            if done_event is not None and done_event.get("stage_b_ran"):
                stage_b_ran += 1
        if row["revision_count"] and row["revision_count"] > 0:
            revised += 1

    return GateStats(
        total_resolved=len(rows),
        stakes_counts=stakes_counts,
        success_count=success,
        caught_count=caught,
        rejected_count=rejected,
        uncertain_count=uncertain,
        rows_with_recorded_timeline=rows_with_timeline,
        stage_b_ran_count=stage_b_ran,
        revised_count=revised,
    )
