"""Real Honesty Log (Phase 6, `QUORUM_PRODUCTION_COMPLETION_PLAN.md`)
-- backs `GET /honesty_log` (`QUORUM_DATA_CONTRACTS.md` §5.13), closing
the real, permanently-dead "Log" bottom-nav tab. Confirmed by direct
search before writing this file: the tab's own real, tested mobile
logic (`mobile/lib/features/honesty_log/`) has existed since Batch 8
(`DEC-087`) with zero real backend behind it -- `backend/features/
honesty_log.py`, named by `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md`
§9.7's own table as already real and tested, does not exist anywhere
in this repository.

REAL DATA SOURCE, confirmed directly before writing a query: the real,
live `action_events` table already carries exactly the real, closed-
vocabulary `outcome` CHECK constraint this module needs --
`'approved_unchanged' | 'caught_by_gate' | 'corrected_by_user' |
'uncertain_no_data'` (migration `0001`), since widened by migrations
`0019` and `0020` (`DEC-188`) to also admit `'rejected_by_user'` and
`'outcome_unknown'` -- no new column, no new table. `retry_queue_drainer.py::map_verdict_to_outcome()` is the one
real, live producer today, and only ever writes `'approved_unchanged'`
or `'caught_by_gate'` -- `'corrected_by_user'` (a human corrected a
miss after the fact) and `'uncertain_no_data'` (a genuine Stage-A
`no_data_found` Finding propagating to the action-level outcome) are
real, valid, closed-schema values with no real producer yet, the same
disclosed "schema ready, no real caller yet" shape `SEND_EMAIL`
execution already carries (`DEC-142`).

THE REAL BUCKETING RULE, matching `build_honesty_feed()`'s own real
design commitment (`QUORUM_DATA_CONTRACTS.md` §5.13: "never filters
anything out... shown with EQUAL prominence, not buried"):
- `successes`: `'approved_unchanged'`.
- `failures_and_catches`: `'caught_by_gate'`, `'corrected_by_user'`,
  `'rejected_by_user'` -- real, structurally different reasons an
  action didn't sail through unchanged, deliberately still
  distinguishable via each real row's own `outcome` field (the mobile
  client's own already-built `outcomeLabel()` gives each a genuinely
  distinct, honest label).
- `genuinely_uncertain`: `'uncertain_no_data'`, `'outcome_unknown'` --
  real, honest third states, never folded into either bucket, the same
  `Finding.evidence_state` discipline this project holds everywhere
  else, applied here to the action-outcome level.

The authoritative, machine-readable form of that partition is the
`SUCCESS_OUTCOMES`/`FAILURE_OUTCOMES`/`UNCERTAIN_OUTCOMES` frozensets
below; this prose exists to explain the reasoning, not to be a second
source of truth that can drift from it. `DEC-189` added the last two
values after finding that `DEC-188` had widened the CHECK constraint
without updating this module, which silently dropped every real
rejected and every real genuinely-unknown action from the feed.

`success_rate` is REAL, DELIBERATELY NULLABLE (never a real `0.0`
standing in for "nothing to compute from") -- mirrors `trust_digest.py`'s
own already-established, real precedent exactly: `uncertain_no_data`
rows are excluded from both `total` and the success-rate denominator,
since counting "we don't know" as an attempt that merely didn't
succeed would collapse two genuinely different real states into one.
Nothing in this project's real spec corpus states this exact formula
-- a real, reasoned, disclosed choice, not a recalled spec value,
matching `trust_digest.py`'s own honest precedent for the same kind of
gap.

A REAL, NEW DESIGN DECISION THIS MODULE MAKES, DISCLOSED RATHER THAN
SILENTLY INVENTED: `QUORUM_DATA_CONTRACTS.md` §5.13 names a real
`description` field in its own JSON example ("Replied to Priya about
Thursday") but never specifies how to construct one -- `action_events`
has no dedicated description column, only `action_type`/`payload`.
`describe_action()` below is a real, honest, human-readable rendering
built directly from those two real, already-stored fields, defensive
throughout (a real payload missing an expected key never raises, it
just produces a slightly less specific real sentence) -- not scraped
from any spec, since none exists for this exact transformation.

A REAL, RELATED GAP FOUND WHILE READING THIS MODULE'S OWN REAL
PRECEDENT, DISCLOSED HERE AT THE TIME RATHER THAN SILENTLY FIXED (OUT
OF THIS SESSION'S OWN SCOPE): `main.py`'s real `GET /trust_digest`
route carried a comment claiming "`action_events` itself has no
`user_id` column" -- true when that route was first built, but
`action_events.user_id` has existed since migration `0004` (`DEC-119`,
predating this comment's own claim). `fetch_trust_digest()` aggregated
every real user's `action_events` together with no real per-user
filter at all -- a real, live, then-currently-deployed cross-user
aggregation gap, not just a stale comment. This module never repeated
that mistake -- `fetch_honesty_feed()` below has been real, per-user
scoped from its first line -- and the `/trust_digest` gap itself,
found here and left open at the time, is **RESOLVED as of `DEC-150`**:
both `aggregate_weekly_summary()` and `fetch_trust_digest()` now
require a real, resolved `user_id`.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime

import asyncpg

from quorum_backend.gate.schemas import ActionType


@dataclass(frozen=True)
class LoggedAction:
    action_id: str
    timestamp: datetime
    outcome: str
    description: str


@dataclass(frozen=True)
class HonestyFeed:
    total: int
    success_rate: float | None
    successes: list[LoggedAction]
    failures_and_catches: list[LoggedAction]
    genuinely_uncertain: list[LoggedAction]


def describe_action(action_type: str, payload: dict) -> str:
    """Real, honest, human-readable descriptions -- see this module's
    own top-of-file docstring for why this is a real, new design
    decision, not a recalled spec value. Defensive throughout: a real
    payload missing an expected key never raises.

    REAL, DISCLOSED FIX (the redesign's own real bug-fix work): made
    public (dropped the leading underscore) so `features/search.py` can
    reuse this exact same formatter for its own `decision`-type results
    -- closes a real, confirmed-live bug found during this session's
    on-device audit (raw jargon like `"update_budget: caught_by_gate"`
    shown directly in a real search result) rather than building a
    second, parallel human-readable mapping (the same "reuse, don't
    re-derive" precedent `gate_reveal_screen.dart`'s own public
    `FindingRow` already set on the mobile side, `DEC-153`)."""
    if action_type == ActionType.CREATE_TASK.value:
        return f"Created task: {payload.get('title') or 'a real task'}"
    if action_type == ActionType.LOG_EXPENSE.value:
        payee = payload.get("payee") or "an unknown payee"
        amount = payload.get("amount")
        return f"Logged expense: {payee}" + (f" (${amount})" if amount is not None else "")
    if action_type == ActionType.SEND_EMAIL.value:
        return f"Sent an email to {payload.get('to') or 'a recipient'}"
    if action_type == ActionType.ARCHIVE_EMAIL.value:
        return "Archived an email"
    if action_type == ActionType.LABEL_EMAIL.value:
        return "Labeled an email"
    if action_type == ActionType.CREATE_EMAIL_DRAFT.value:
        return f"Drafted an email to {payload.get('to') or 'a recipient'}"
    if action_type == ActionType.CREATE_APPLICATION.value:
        return f"Added application: {payload.get('company') or 'a company'}"
    # A real, open fallback for every other real ActionType -- never
    # raises on an unrecognized value, matching this project's own
    # established defensive-parsing precedent for genuinely open
    # vocabularies (career_pipeline_logic.dart's own de-snaking
    # fallback on the mobile side, mirrored here in Python).
    return action_type.replace("_", " ").capitalize()


# The real, complete partition of `action_events.outcome`'s own CHECK
# constraint, as of migration `0020`. Every value the constraint admits
# appears in exactly one of these three sets, and `build_honesty_feed()`
# raises on anything outside their union -- see its `else` branch for
# why that is loud rather than defensive. Keeping the three sets
# adjacent here, rather than inline in the branch conditions, is what
# makes "did we cover every constraint value?" answerable by reading
# twelve lines instead of tracing control flow.
#
# Made public (`DEC-192`, dropped the leading underscore) -- the exact
# same "make public for a second real reuse" precedent this module's
# own `describe_action()` already set: `features/agent_telemetry.py`
# needs the identical real partition for its own per-agent outcome
# breakdown and reuses these sets directly rather than re-deriving a
# second copy that could silently drift from this one.
SUCCESS_OUTCOMES = frozenset({"approved_unchanged"})
FAILURE_OUTCOMES = frozenset(
    {
        "caught_by_gate",
        "corrected_by_user",
        # `rejected_by_user` (migration `0019`, `DEC-188`): a human
        # declined a real S3 action the Gate had already cleared. It
        # belongs here, not in `successes`, by this bucket's own stated
        # definition -- "a real, structurally different reason an action
        # didn't sail through unchanged" -- and sits naturally beside
        # `corrected_by_user`, the other outcome where a human, not the
        # Gate, was the intervening party. It stays distinguishable from
        # both via the row's own `outcome` field.
        "rejected_by_user",
    }
)
UNCERTAIN_OUTCOMES = frozenset(
    {
        "uncertain_no_data",
        # `outcome_unknown` (migration `0020`, `DEC-188`): a transport
        # failure AFTER a real external call may already have taken
        # effect -- the system genuinely cannot tell whether the email
        # sent. This is the purest case this bucket exists for, and
        # folding it into either of the other two would assert knowledge
        # the system does not have. Excluded from `total` and from the
        # success-rate denominator for exactly the reason the module
        # docstring already gives for `uncertain_no_data`.
        "outcome_unknown",
    }
)


def build_honesty_feed(rows: list[tuple[str, datetime, str, str, dict]]) -> HonestyFeed:
    """Pure, real, deterministic grouping -- takes already-fetched
    `(action_id, timestamp, outcome, action_type, payload)` tuples
    (real DB access lives in `fetch_honesty_feed()` below, mirroring
    `trust_digest.py`/`subscription_detective.py`'s own established
    split between pure computation and live querying)."""
    successes: list[LoggedAction] = []
    failures_and_catches: list[LoggedAction] = []
    genuinely_uncertain: list[LoggedAction] = []

    for action_id, timestamp, outcome, action_type, payload in rows:
        entry = LoggedAction(
            action_id=action_id,
            timestamp=timestamp,
            outcome=outcome,
            description=describe_action(action_type, payload),
        )
        if outcome in SUCCESS_OUTCOMES:
            successes.append(entry)
        elif outcome in FAILURE_OUTCOMES:
            failures_and_catches.append(entry)
        elif outcome in UNCERTAIN_OUTCOMES:
            genuinely_uncertain.append(entry)
        else:
            # REAL, DELIBERATE REVERSAL, `DEC-189`: this branch used to
            # drop an unrecognized outcome silently, on the reasoning
            # that the CHECK constraint made it unreachable. That
            # reasoning was sound and the outcome was still a real bug,
            # because the constraint is not frozen -- `DEC-188` added
            # two genuinely new values to it (`rejected_by_user`,
            # `outcome_unknown`) and this function was never updated,
            # so from that moment every real rejected action and every
            # real genuinely-unknown execution vanished from the one
            # feed in this entire product whose stated contract is that
            # it "never filters anything out" (`QUORUM_DATA_CONTRACTS.md`
            # §5.13). A silent drop turned a schema change into
            # invisible data loss in the honesty surface specifically.
            #
            # Fail loud instead -- the same handling `CLAUDE.md` already
            # mandates for `tasks.status`, the project's other real
            # closed, CHECK-constrained set. The next person to widen
            # this constraint now gets an immediate, named failure
            # instead of a feed that quietly under-reports.
            raise ValueError(
                f"Unrecognized action_events.outcome {outcome!r}. This is a "
                f"closed, CHECK-constrained set: if a migration added a new "
                f"value, add it to exactly one of SUCCESS_OUTCOMES, "
                f"FAILURE_OUTCOMES or UNCERTAIN_OUTCOMES in honesty_log.py."
            )

    total = len(successes) + len(failures_and_catches)
    success_rate = round(len(successes) / total, 3) if total > 0 else None

    return HonestyFeed(
        total=total,
        success_rate=success_rate,
        successes=successes,
        failures_and_catches=failures_and_catches,
        genuinely_uncertain=genuinely_uncertain,
    )


async def fetch_honesty_feed(pool: asyncpg.Pool, *, user_id: str) -> HonestyFeed:
    """The real, live query backing `GET /honesty_log`, real per-user
    scoped from its first line -- confirmed directly against the real,
    live schema before writing this: `action_events.user_id` has
    existed since migration `0004` (`DEC-119`), so there is no excuse
    to repeat `trust_digest.py`'s own real, still-open cross-user
    aggregation gap here (see this module's own top-of-file docstring,
    disclosed separately, not fixed by this session)."""
    rows = await pool.fetch(
        "SELECT proposal_id, COALESCE(resolved_at, created_at) AS ts, outcome, action_type, payload "
        "FROM action_events WHERE user_id = $1 AND outcome IS NOT NULL "
        "ORDER BY COALESCE(resolved_at, created_at) DESC",
        uuid.UUID(user_id),
    )
    return build_honesty_feed(
        [
            (str(row["proposal_id"]), row["ts"], row["outcome"], row["action_type"], json.loads(row["payload"]))
            for row in rows
        ]
    )
