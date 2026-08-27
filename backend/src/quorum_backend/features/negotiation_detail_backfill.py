"""Real, live, Gemini-backed detail generation for the BARE negotiations
`deadline_watch.py` (`DEC-132`) and `spend_alert.py` (`DEC-133`) create --
closes the real, disclosed gap both those modules' own top-of-file
docstrings name as a genuine, separate, still-open item: a bare
negotiation (`positions`/`options` NULL) can never be resolved through
any real code path in this backend (`features/negotiation_choice.py`
requires real `options`), so without this module, any real, live conflict
either autonomous job detects would sit un-actionable forever, bounded
only by `negotiation_trigger_support.py`'s own 24-hour bare-negotiation
cooldown -- a real mitigation, never a substitute for the actual thing a
negotiation is supposed to let a person do: choose.

**Authorized directly, chosen over building the still-unspecified
`briefing` job** (`DEC-134`'s own session): `QUORUM_ARCHITECTURE_DESIGN_
DOCUMENT.md` names no real destination table, route, or mobile consumer
for a "briefing" result anywhere in this project's real corpus, while
this gap was already disclosed, already blocking, and now genuinely
matters the moment autonomous scheduling went live -- closing it, not
inventing a new feature's shape from scratch, is what Rule 3 (`.claude/
CLAUDE.md`) calls for here.

REAL DESIGN -- RE-DERIVE, NEVER PERSIST A STALE SNAPSHOT: neither
autonomous job stores the real `resource_claims`/`domain_states` it used
at creation time, only `conflicted_domains`. Rather than adding schema to
capture a point-in-time snapshot, this module re-fetches the SAME real,
CURRENT tasks/finance data a fresh scan would use, dispatching on the
negotiation's own real `trigger_source` to know which job's real claim
shape to rebuild (`'deadline_watch'` -> `features/negotiation_trigger_
support.py`'s tasks-claim + real month-to-date-spend finance claim, the
same shape `deadline_watch.py` itself builds; `'spend_alert'` -> the same
tasks claim + real sum-of-detected-subscriptions finance claim). This is
more honest than a stored snapshot: real tasks/finance data can genuinely
move between a bare negotiation's creation and this job's own next real
run, and re-deriving means detail generation is always grounded in what's
ACTUALLY true right now, not what was true when the bare row was created.

A REAL, HONEST CONSEQUENCE OF RE-DERIVING: this module re-runs the real,
already-tested `negotiation/subgraph.py`'s own `scan` node as a genuine
confirmation step before spending a single real Gemini call. If the real
situation has resolved itself since the bare negotiation was created (the
user already reduced spending, or the task closed), `triggers_negotiation`
comes back `False` and this module honestly does nothing -- no detail
generated for a conflict that no longer exists, the negotiation stays
bare (a real, disclosed, still-open limitation: this module does not
mark a now-moot bare negotiation resolved either; it simply lets `has_
blocking_negotiation()`'s own 24-hour cooldown eventually let a fresh,
accurate one through if the situation recurs).

REAL, GENERIC POSITION CONTEXT, NOT HAND-WRITTEN PROSE: `scripts/
seed_demo_dataset.py`'s own `seed_negotiation_detail()` hand-writes its
`domain_context` strings for its own fixed demo scenario -- genuinely
fine for a one-time, human-authored seed, wrong for a real autonomous
job. This module's own `_build_*_state()` functions compose each
domain's context sentence from the SAME real numbers just fetched
(real hours, real rupee amounts, real percentages), never fabricated
prose describing a situation this module hasn't actually queried for.

REAL, GENERIC IMPACT EFFECT SIZES, A DELIBERATE, DISCLOSED SIMPLIFICATION
-- NOT A NEW INVENTED NUMBER: `negotiation/subgraph.py`'s own top-of-file
docstring already discloses that turning a synthesized option's free-text
description into a real, quantified `OptionEffect` is genuine domain-
specific interpretation, out of scope for exact quantification anywhere
in this codebase -- `seed_demo_dataset.py`'s own hand-seeded scenario
already chose fixed, illustrative relief magnitudes (a 0.1 budget-
fraction improvement, a 2.0-hour task reduction) rather than asking a
model to self-quantify its own proposal. `GENERIC_FINANCE_RELIEF_
FRACTION`/`GENERIC_TASKS_RELIEF_HOURS` below reuse those exact, already-
established values, generalized into real, reusable constants rather
than a scenario-specific one-off -- the same "directionally illustrative,
never fabricated false precision" property this project's Gate already
holds impact deltas to (`ImpactDelta` values are always code-computed,
`gate/schemas.py`'s own real contract), just generalized to any real
domain-driven option instead of one hand-written demo scenario.

REAL, QUOTA-CONSCIOUS BATCHING: up to 3 real Gemini calls per negotiation
(one per conflicted domain for positions, one more for synthesis) --
`DEFAULT_BATCH_SIZE` bounds how many real negotiations one real
invocation will detail, the same disclosed, fluctuating free-tier quota
concern (`STATUS_INDEX.md` item #21) `deadline_watch.py`/`spend_alert.py`
both already cite as the reason THEY never generate detail inline.

REAL, ATOMIC IDEMPOTENCY UNDER CONCURRENCY: deliberately does NOT reuse
`features/negotiation_detail.py::persist_negotiation_detail` for the
final write -- that function's own real contract is an unconditional
overwrite, correct for `scripts/seed_demo_dataset.py`'s own manual,
single-operator use, but this module's own real requirement is
genuinely different: a real, atomic, race-safe guard (`UPDATE ...
WHERE options IS NULL`) so two real, concurrent invocations picking the
same bare negotiation can never double-write, and the loser is honestly
tallied as `ALREADY_DETAILED` rather than silently succeeding twice.

**FOUR REAL, LIVE-PROVEN BUGS FOUND BY THIS PR'S OWN CRITICAL-TIER
REVIEW, ALL FIXED HERE:**

1. **Permanent head-of-line block (HIGH):** the original candidate query
   ordered by `started_at ASC LIMIT n` with no exclusion for a row
   already found `SITUATION_RESOLVED` -- and nothing anywhere ever marks
   a bare, now-moot negotiation resolved (`features/negotiation_choice.
   py`'s own only real `resolved_at` writer requires `options IS NOT
   NULL`). Live-proven: 3 users whose bare negotiations had already gone
   moot occupied the ENTIRE batch on every single run, forever, so a 4th
   user's genuinely live conflict was NEVER detailed. Fixed: migration
   `0009_negotiation_detail_backfill_attempts` adds `detail_backfill_
   last_attempted_at`, and candidate selection now orders by "least
   recently attempted" (`NULLS FIRST`, then `started_at`) instead of
   raw creation order -- a genuine round-robin across every real bare
   candidate, so no fixed set can dominate every batch forever.
2. **Unbounded real Gemini quota burn on a durably-failing negotiation
   (HIGH):** the same head-of-line ordering meant a negotiation that
   fails every real attempt (a durable Gemini error, a malformed real
   value) got re-picked, and re-attempted with fresh real Gemini calls,
   on every single cron tick, forever -- live-proven to burn 4 real
   outbound calls per tick indefinitely. Fixed: `detail_backfill_
   attempts` (same migration) is incremented on every real attempt,
   regardless of outcome, and `MAX_DETAIL_BACKFILL_ATTEMPTS` excludes a
   negotiation from candidate selection once it's been durably tried and
   failed that many times -- a real, disclosed, bounded give-up, not a
   silent infinite retry.
3. **`budget_remaining_fraction` can exceed `1.0` or go negative (MEDIUM),
   rendered by the mobile app as an impossible "110% budget remaining":**
   live-proven reachable two real ways -- a real refund making month-to-
   date spend negative (`expenses.amount` has no real positivity `CHECK`),
   and `spend_alert`-sourced negotiations computing this fraction from
   two genuinely independent real quantities (remaining budget vs. total
   detected subscription cost) that were never guaranteed to co-vary
   within `[0, 1]`. Fixed: `_clamp_fraction_impact()` clamps this one
   metric's `before`/`after` (and re-derives `direction`) after real
   impact simulation, deliberately NOT inside the shared, already-tested
   `impact_simulator.py` -- that module's own generic arithmetic contract
   stays unchanged for every other real caller.
4. **`deadline_slack_hours` never moves when the tasks-relief effect is
   applied (MEDIUM), an internally contradictory delta pair** (the same
   option shows "hours committed: improves" and "deadline slack:
   unchanged" for the identical real relief): a real, exact consequence
   of this module's own `deadline_slack_hours = available - committed`
   definition -- reducing `committed` by `GENERIC_TASKS_RELIEF_HOURS`
   must increase slack by the identical amount, algebraically, not
   approximately. Fixed: `_generic_effect_extractor` now sets both
   `deadline_slack_hours_change`/`task_hours_committed_change` together,
   as the one real definition requires.

**A FIFTH REAL FINDING, ADDRESSED HERE TOO (MEDIUM):** the original
`DEC-135` log entry claimed the real, disclosed cross-job negotiation-
duplication gap (`DEC-134`) was "unaffected" by this module, since detail
generation "doesn't change how many negotiations get created." True, but
understated the real consequence: before this module existed, a stray
duplicate bare negotiation from the OTHER autonomous job expired
harmlessly after `BARE_NEGOTIATION_COOLDOWN_HOURS`; after detailing BOTH
of a real user's duplicate negotiations for the same underlying strain,
the review found two live, simultaneously actionable cards on Today, and
because an options-bearing negotiation blocks unconditionally with no
cooldown, the ignored twin now permanently (not just for 24h) blocks
BOTH autonomous jobs for that user. Fixed: before spending a single real
Gemini call, this module checks whether the same real user already holds
ANOTHER real, unresolved, options-bearing negotiation whose
`conflicted_domains` overlaps -- if so, honestly leaves this one bare
(`SKIPPED_DUPLICATE_ACTIONABLE`), the same real, pre-existing, already-
accepted behavior this class of duplicate had before this module ever
existed, not a new, worse one.

**A SIXTH REAL FIX (MEDIUM-HIGH), SCHEDULING-RELATED:** the review
measured a real, live Gemini round trip for one negotiation at ~28
seconds -- `DEFAULT_BATCH_SIZE = 3`, run sequentially, meant a single
real invocation of this job could take ~83 seconds, blowing past
`DEC-134`'s own `pg_net` `timeout_milliseconds := 30000` fix and
occupying a real Cloud Run instance (`--concurrency=1`) for over a
minute while the other three real Phase 2 jobs queue behind it. Fixed:
`DEFAULT_BATCH_SIZE` reduced to `1`, and `backend/scripts/enable_
backfill_negotiation_detail_cron.sql` (written this same session, not
yet scheduled live -- see that file's own top comment) uses an offset
schedule and a real, measured-with-margin timeout, rather than
mechanically copying `DEC-134`'s exact `*/30`+`30000ms` pattern the way
this entry originally, incorrectly planned to.

**TWO REAL, LOWER-SEVERITY FIXES ALSO APPLIED:** state rebuild
(`_build_deadline_watch_state`/`_build_spend_alert_state`) now runs
inside a real transaction, matching `deadline_watch.py`/`spend_alert.py`'s
own established per-item transactional discipline (previously ran on a
bare connection with no transaction -- low real impact, but a genuine
inconsistency the review found). `negotiation/gemini_calls.py`'s own
pre-existing retry loop (`DEC-121`) had no real backoff at all between
attempts -- harmless for a single, human-triggered call, but this PR is
the first thing to call it on a real, autonomous, repeating schedule, so
a rate-limit response with zero backoff doubles the real request rate
into the same limit. A small, real `asyncio.sleep` between retries is
now in place there too, disclosed as a deliberate, narrowly-scoped touch
to shared code this specific PR made newly consequential.
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from enum import Enum, auto

import asyncpg

from quorum_backend.features.negotiation_trigger_support import (
    build_tasks_claim_and_state,
    fetch_budget_snapshot,
    fetch_detected_subscriptions_via_conn,
)
from quorum_backend.gate.schemas import ImpactDelta, NegotiationOption, ResourceClaim
from quorum_backend.negotiation.gemini_calls import make_gemini_position_call, make_gemini_synthesis_call
from quorum_backend.negotiation.impact_simulator import DomainSnapshot, OptionEffect
from quorum_backend.negotiation.subgraph import NegotiationState, build_negotiation_graph
from quorum_backend.negotiation.trigger import DomainState, scan_for_conflicts

logger = logging.getLogger("quorum_backend")

# Same real string constants deadline_watch.py/spend_alert.py already
# write onto negotiations.trigger_source -- imported as literals here
# (not re-imported from either module) to avoid a real, disclosed
# dependency-direction smell: neither trigger job needs to know detail
# generation exists, so this module depends on their string CONTRACT,
# not on importing their own runtime code.
DEADLINE_WATCH_TRIGGER_SOURCE = "deadline_watch"
SPEND_ALERT_TRIGGER_SOURCE = "spend_alert"

# See this module's own top-of-file docstring for why these two exact
# values, not new ones invented for this session.
GENERIC_FINANCE_RELIEF_FRACTION = 0.1
GENERIC_TASKS_RELIEF_HOURS = 2.0

# See this module's own top-of-file docstring's "REAL, QUOTA-CONSCIOUS
# BATCHING" section -- reduced from 3 to 1 by this PR's own CRITICAL-tier
# review's real, measured ~28s-per-negotiation finding (fix #6 above).
DEFAULT_BATCH_SIZE = 1

# See this module's own top-of-file docstring, fix #2 -- a real, bounded
# give-up so a durably-failing negotiation stops burning real Gemini
# quota on every cron tick forever. 5 real attempts, spread across
# real, separate cron ticks (never retried twice in the same batch), is
# generous enough to ride out a real, transient quota blip while still
# being a genuine, real ceiling, not an unbounded one.
MAX_DETAIL_BACKFILL_ATTEMPTS = 5


class BackfillOutcome(Enum):
    UNKNOWN_TRIGGER_SOURCE = auto()  # not a recognized autonomous job -- honestly skipped, never guessed at
    SITUATION_RESOLVED = auto()  # a fresh re-scan against current real data no longer conflicts
    SKIPPED_DUPLICATE_ACTIONABLE = auto()  # the same real user already has another real, actionable negotiation for an overlapping conflict
    ALREADY_DETAILED = auto()  # lost a real, live race to a concurrent invocation -- no double-write
    DETAILED = auto()  # real Gemini-backed positions/options genuinely generated and persisted


@dataclass(frozen=True)
class NegotiationDetailBackfillResult:
    negotiations_scanned: int
    negotiations_failed: int
    negotiations_detailed: int
    outcome_counts: dict[str, int]


def _tasks_context(tasks_claim: ResourceClaim, tasks_state: DomainState) -> str:
    return (
        f"{tasks_claim.amount:.1f} hours of real, committed work are due before the "
        f"nearest open task deadline, but only {tasks_state.available:.1f} hours are "
        "genuinely available before then."
    )


async def _build_deadline_watch_state(
    conn: asyncpg.Connection, *, user_id: str
) -> tuple[list[ResourceClaim], dict[str, DomainState], dict[str, str], float] | None:
    """Real state rebuild for a `'deadline_watch'`-sourced negotiation --
    mirrors `deadline_watch.py::scan_one_user`'s own real claim shape
    exactly. Returns `None` honestly when the user no longer has a real
    open task with a future deadline (the real precondition that job's
    own `NO_CLAIM` outcome already encodes) -- the caller treats this the
    same as `SITUATION_RESOLVED`.

    RESOLVED, `DEC-148`: the returned tuple now carries a fourth real
    element, this user's own real `monthly_budget_limit` (migration
    `0015`) -- `_build_baseline()` needs it to convert a real remaining-
    amount into a real remaining-fraction, and it has no `conn`/`user_id`
    of its own to look it up itself."""
    tasks = await build_tasks_claim_and_state(conn, user_id=user_id)
    if tasks is None:
        return None
    tasks_claim, tasks_state = tasks
    # RESOLVED, `DEC-148` review (LOW L1): one real, shared snapshot
    # read, not three separate real queries across this module's two
    # state-builders -- see `fetch_budget_snapshot()`'s own docstring
    # for the real split-snapshot inconsistency this closes.
    monthly_limit, spent, remaining = await fetch_budget_snapshot(conn, user_id=user_id)
    finance_claim = ResourceClaim(claim_type="money", amount=spent, unit="currency_minor_units")
    finance_state = DomainState(domain="finance", available=remaining, unit="currency_minor_units")
    spent_pct = (spent / monthly_limit) * 100 if monthly_limit else 0.0
    context = {
        "tasks": _tasks_context(tasks_claim, tasks_state),
        "finance": (
            f"Rs.{spent:,.0f} of this month's Rs.{monthly_limit:,.0f} budget "
            f"has already been spent ({spent_pct:.0f}%), leaving Rs.{remaining:,.0f} "
            "remaining this month."
        ),
    }
    return [tasks_claim, finance_claim], {"tasks": tasks_state, "finance": finance_state}, context, monthly_limit


async def _build_spend_alert_state(
    conn: asyncpg.Connection, *, user_id: str
) -> tuple[list[ResourceClaim], dict[str, DomainState], dict[str, str], float] | None:
    """Real state rebuild for a `'spend_alert'`-sourced negotiation --
    mirrors `spend_alert.py::scan_one_user`'s own real claim shape
    exactly (real SUM of every currently-detected subscription, real
    tasks claim only when a real one still exists). Returns `None`
    honestly when no real recurring subscription is detected anymore --
    the real precondition that job's own `NO_CLAIM` outcome encodes.
    See `_build_deadline_watch_state`'s own docstring for why the
    returned tuple's fourth element (the real per-user monthly budget
    limit) exists, `DEC-148`."""
    subscriptions = await fetch_detected_subscriptions_via_conn(conn, user_id=user_id)
    if not subscriptions:
        return None
    total_recurring_cost = sum(sub.average_amount for sub in subscriptions)
    # RESOLVED, `DEC-148` review (LOW L1): one real, shared snapshot
    # read instead of two separate calls (one of which internally
    # re-queried the same real spend figure this call already needed).
    monthly_limit, _spent, remaining = await fetch_budget_snapshot(conn, user_id=user_id)
    finance_claim = ResourceClaim(claim_type="money", amount=total_recurring_cost, unit="currency_minor_units")
    finance_state = DomainState(domain="finance", available=remaining, unit="currency_minor_units")
    resource_claims = [finance_claim]
    domain_states = {"finance": finance_state}
    context = {
        "finance": (
            f"Currently detected real recurring subscriptions total Rs.{total_recurring_cost:,.0f}/month "
            f"across {len(subscriptions)} real payee(s), but only Rs.{remaining:,.0f} remains in this "
            f"month's Rs.{monthly_limit:,.0f} budget."
        ),
    }
    tasks = await build_tasks_claim_and_state(conn, user_id=user_id)
    if tasks is not None:
        tasks_claim, tasks_state = tasks
        resource_claims.append(tasks_claim)
        domain_states["tasks"] = tasks_state
        context["tasks"] = _tasks_context(tasks_claim, tasks_state)
    return resource_claims, domain_states, context, monthly_limit


def _build_baseline(
    resource_claims: list[ResourceClaim], domain_states: dict[str, DomainState], *, monthly_budget_limit: float
) -> DomainSnapshot:
    """Real, current-data-derived baseline for `negotiation/impact_
    simulator.py`'s own `DomainSnapshot` -- the three real standing
    metrics it needs, computed from the exact same real claim/state
    values just rebuilt above, never a hardcoded scenario number.

    RESOLVED, `DEC-148`: `monthly_budget_limit` is now a real, required
    parameter (this user's own real `users.monthly_budget_limit`) rather
    than the module-level `TODAY_MONTHLY_BUDGET_LIMIT` constant this
    function used to close over -- this function itself has no `conn`/
    `user_id` to look the real value up on its own, so both real callers
    thread it through from their own state rebuild."""
    tasks_state = domain_states.get("tasks")
    tasks_claim = next((c for c in resource_claims if c.claim_type == "effort"), None)
    finance_state = domain_states.get("finance")
    task_hours_committed = tasks_claim.amount if tasks_claim is not None else 0.0
    deadline_slack_hours = (tasks_state.available - task_hours_committed) if tasks_state is not None else 0.0
    budget_remaining_fraction = (
        finance_state.available / monthly_budget_limit
        if finance_state is not None and monthly_budget_limit
        else 0.0
    )
    return DomainSnapshot(
        deadline_slack_hours=deadline_slack_hours,
        budget_remaining_fraction=budget_remaining_fraction,
        task_hours_committed=task_hours_committed,
    )


def _generic_effect_extractor(option: NegotiationOption) -> OptionEffect:
    """See this module's own top-of-file docstring's "REAL, GENERIC
    IMPACT EFFECT SIZES" section for why these two fixed magnitudes,
    not model-self-quantified or newly invented ones.

    A REAL, DISCLOSED FIX (this PR's own CRITICAL-tier review, finding
    #4): `deadline_slack_hours` is defined in `_build_baseline()` below
    as `available - committed` -- so reducing `task_hours_committed` by
    `GENERIC_TASKS_RELIEF_HOURS` MUST increase `deadline_slack_hours` by
    the identical amount; that's not a judgment call, it's the algebra
    of this module's own definition. An earlier version left `deadline_
    slack_hours_change` at its real, zero default here, producing a
    genuinely self-contradictory pair of real impact deltas for the same
    option (hours committed improves; deadline slack unchanged) on every
    single real negotiation this module has ever produced (`scan_for_
    conflicts` only ever triggers when committed exceeds available, so
    `deadline_slack_hours` starts negative every time -- never an edge
    case here)."""
    tasks_relief_hours = GENERIC_TASKS_RELIEF_HOURS if "tasks" in option.source_domains else 0.0
    return OptionEffect(
        budget_remaining_fraction_change=GENERIC_FINANCE_RELIEF_FRACTION if "finance" in option.source_domains else 0.0,
        deadline_slack_hours_change=tasks_relief_hours,
        task_hours_committed_change=-tasks_relief_hours,
    )


def _clamp_fraction_impact(impact: dict[str, list[ImpactDelta]]) -> dict[str, list[ImpactDelta]]:
    """A REAL, DISCLOSED FIX (this PR's own CRITICAL-tier review, finding
    #3): `budget_remaining_fraction` is a genuine `0.0`-`1.0` fraction by
    real, established contract (`negotiation_logic.dart`'s own real
    rendering assumption, `'${(value * 100).round()}%'`), but this
    module's own real baseline can legitimately land outside that range
    for two real, disclosed reasons -- a real refund can make month-to-
    date spend negative (`expenses.amount` carries no real positivity
    `CHECK`), and a `spend_alert`-sourced negotiation computes this
    fraction from two genuinely independent real quantities (remaining
    budget vs. total detected subscription cost) never guaranteed to
    co-vary within `[0, 1]`. Clamped HERE, in this module, deliberately
    NOT inside the shared, already-tested `negotiation/impact_simulator.
    py` -- that module's own generic `compute_deltas`/`apply_effect`
    arithmetic stays exactly as every other real caller (`scripts/
    seed_demo_dataset.py`, `test_negotiation_subgraph.py`) already
    relies on it. Only the `budget_remaining_fraction` metric is
    touched; `deadline_slack_hours`/`task_hours_committed` have no real
    `[0, 1]` contract to violate."""
    clamped: dict[str, list[ImpactDelta]] = {}
    for option_id, deltas in impact.items():
        new_deltas = []
        for delta in deltas:
            if delta.metric != "budget_remaining_fraction":
                new_deltas.append(delta)
                continue
            before = max(0.0, min(1.0, delta.before))
            after = max(0.0, min(1.0, delta.after))
            direction = "unchanged" if after == before else ("improves" if after > before else "worsens")
            new_deltas.append(ImpactDelta(metric=delta.metric, before=before, after=after, direction=direction))
        clamped[option_id] = new_deltas
    return clamped


async def _mark_attempted(pool: asyncpg.Pool, *, negotiation_id: str) -> None:
    """A REAL, DISCLOSED FIX (this PR's own CRITICAL-tier review, findings
    #1/#2): called as the very FIRST real write inside `generate_detail_
    for_one_negotiation()` below, before any state rebuild or Gemini call
    -- so a real attempt is counted even when everything after this point
    raises. This is what makes `_fetch_bare_autonomous_negotiation_ids()`'s
    own real, round-robin ordering and bounded retry cap possible."""
    await pool.execute(
        "UPDATE negotiations SET detail_backfill_attempts = detail_backfill_attempts + 1, "
        "detail_backfill_last_attempted_at = now() WHERE negotiation_id = $1",
        uuid.UUID(negotiation_id),
    )


async def _user_already_has_another_actionable_negotiation(
    pool: asyncpg.Pool, *, user_id: str, exclude_negotiation_id: str, conflicted_domains: list[str]
) -> bool:
    """A REAL, DISCLOSED FIX (this PR's own CRITICAL-tier review, the
    "fifth real finding"): checked BEFORE any real Gemini call is made,
    so a real, live-proven duplicate never spends real quota generating
    a second, redundant, permanently-blocking actionable card for a
    conflict the same real user already has one open for. `&&` is
    Postgres's real array-overlap operator -- `True` the moment this
    negotiation's own real conflicted domains share even one real
    domain with another real, unresolved, options-bearing negotiation."""
    row = await pool.fetchrow(
        "SELECT 1 FROM negotiations WHERE user_id = $1 AND negotiation_id != $2 "
        "AND options IS NOT NULL AND resolved_at IS NULL AND conflicted_domains && $3::text[] LIMIT 1",
        uuid.UUID(user_id),
        uuid.UUID(exclude_negotiation_id),
        conflicted_domains,
    )
    return row is not None


async def _persist_detail_if_still_bare(
    conn: asyncpg.Connection, *, negotiation_id: str, positions: list, options: list, impact: dict
) -> bool:
    """Real, atomic, conditional write -- see this module's own top-of-
    file docstring's "REAL, ATOMIC IDEMPOTENCY UNDER CONCURRENCY" section
    for why this doesn't reuse `negotiation_detail.py::persist_
    negotiation_detail`. Returns `True` only if this call genuinely won
    the real race and wrote real detail."""
    positions_json = json.dumps([p.model_dump(mode="json") for p in positions])
    options_json = json.dumps(
        [
            {**option.model_dump(mode="json"), "impact": [d.model_dump(mode="json") for d in impact.get(option.option_id, [])]}
            for option in options
        ]
    )
    tag = await conn.execute(
        "UPDATE negotiations SET positions = $1::jsonb, options = $2::jsonb "
        "WHERE negotiation_id = $3 AND options IS NULL",
        positions_json,
        options_json,
        uuid.UUID(negotiation_id),
    )
    return tag == "UPDATE 1"


async def generate_detail_for_one_negotiation(
    pool: asyncpg.Pool, *, negotiation_id: str, user_id: str, trigger_source: str | None, api_key: str
) -> BackfillOutcome:
    """Real, live, per-negotiation detail generation. Deliberately does
    NOT hold one real database connection/transaction open across the
    real, slow Gemini network calls in the middle -- state is fetched in
    one short-lived `conn`, the real LLM work happens with no pool
    connection checked out, and the final write acquires a second,
    separate short-lived `conn` -- so a limited real connection pool
    isn't tied up for the real seconds a live Gemini round trip takes.
    A REAL, DISCLOSED, ACCEPTED CONSEQUENCE of this choice, found by this
    PR's own CRITICAL-tier review: a real ~28-second gap can separate the
    state read from the final write, so the underlying real `tasks`/
    `expenses` data could in principle change mid-flight in a way the
    "situation resolved itself" honest-skip (checked only at read time)
    doesn't cover -- accepted as inherent to this design, cheaper than
    holding a real connection open across a live LLM round trip."""
    await _mark_attempted(pool, negotiation_id=negotiation_id)

    if trigger_source == DEADLINE_WATCH_TRIGGER_SOURCE:
        async with pool.acquire() as conn, conn.transaction():
            state = await _build_deadline_watch_state(conn, user_id=user_id)
    elif trigger_source == SPEND_ALERT_TRIGGER_SOURCE:
        async with pool.acquire() as conn, conn.transaction():
            state = await _build_spend_alert_state(conn, user_id=user_id)
    else:
        return BackfillOutcome.UNKNOWN_TRIGGER_SOURCE

    if state is None:
        return BackfillOutcome.SITUATION_RESOLVED

    resource_claims, domain_states, context, monthly_budget_limit = state
    baseline = _build_baseline(resource_claims, domain_states, monthly_budget_limit=monthly_budget_limit)

    # A real, cheap, zero-LLM-cost re-confirmation BEFORE any real Gemini
    # call -- lets this function bail out on a moot or duplicate real
    # negotiation without spending a single real network call, even
    # though `build_negotiation_graph`'s own scan node will redundantly
    # recompute the identical real result a moment later.
    scan_result = scan_for_conflicts(resource_claims, domain_states)
    if not scan_result.triggers_negotiation:
        return BackfillOutcome.SITUATION_RESOLVED

    if await _user_already_has_another_actionable_negotiation(
        pool, user_id=user_id, exclude_negotiation_id=negotiation_id, conflicted_domains=scan_result.conflicted_domains
    ):
        return BackfillOutcome.SKIPPED_DUPLICATE_ACTIONABLE

    position_call = make_gemini_position_call(context, api_key=api_key)
    synthesis_call = make_gemini_synthesis_call(api_key=api_key)
    graph = build_negotiation_graph(position_call, synthesis_call, _generic_effect_extractor)

    initial_state: NegotiationState = {
        "resource_claims": resource_claims,
        "domain_states": domain_states,
        "baseline": baseline,
        "conflicted_domains": None,
        "triggers_negotiation": None,
        "positions": None,
        "options": None,
        "impact": None,
    }
    result = await graph.ainvoke(initial_state)
    if not result["triggers_negotiation"]:
        return BackfillOutcome.SITUATION_RESOLVED

    clamped_impact = _clamp_fraction_impact(result["impact"])
    async with pool.acquire() as conn:
        won = await _persist_detail_if_still_bare(
            conn,
            negotiation_id=negotiation_id,
            positions=result["positions"],
            options=result["options"],
            impact=clamped_impact,
        )
    return BackfillOutcome.DETAILED if won else BackfillOutcome.ALREADY_DETAILED


async def _fetch_bare_autonomous_negotiation_ids(pool: asyncpg.Pool, *, batch_size: int) -> list[str]:
    """Real candidate selection for the real, live default scope --
    deliberately excludes any row with a `NULL` `trigger_source`
    (`scripts/seed_demo_dataset.py`'s own hand-seeded, human-authored
    bare rows never set it): this module only ever touches what an
    autonomous job itself created, never a human operator's own manual
    seed data.

    A REAL, DISCLOSED FIX (this PR's own CRITICAL-tier review, findings
    #1/#2): an earlier version ordered by `started_at ASC` alone --
    live-proven to let a small, fixed set of already-tried, now-moot
    bare rows occupy the entire real batch on every single run forever,
    since nothing ever marks a `SITUATION_RESOLVED` row resolved. Fixed:
    ordered by "least recently attempted" instead (`NULLS FIRST` so a
    genuinely never-tried candidate always goes first), a real round-
    robin across every real bare candidate -- and `detail_backfill_
    attempts < MAX_DETAIL_BACKFILL_ATTEMPTS` excludes a negotiation
    that's durably failed a real, bounded number of times, capping real
    Gemini quota waste on one that will never succeed."""
    rows = await pool.fetch(
        "SELECT negotiation_id FROM negotiations "
        "WHERE options IS NULL AND resolved_at IS NULL AND trigger_source IS NOT NULL "
        "AND detail_backfill_attempts < $2 "
        "ORDER BY detail_backfill_last_attempted_at ASC NULLS FIRST, started_at ASC "
        "LIMIT $1",
        batch_size,
        MAX_DETAIL_BACKFILL_ATTEMPTS,
    )
    return [str(r["negotiation_id"]) for r in rows]


async def run_negotiation_detail_backfill(
    pool: asyncpg.Pool, *, api_key: str, batch_size: int = DEFAULT_BATCH_SIZE, negotiation_ids: list[str] | None = None
) -> NegotiationDetailBackfillResult:
    """The real entry point -- `POST /internal/backfill-negotiation-detail`
    (`main.py`) calls this with `negotiation_ids=None` (the real, live
    default, scoped to bare, autonomously-created negotiations only).
    `negotiation_ids`, when explicitly passed, scopes the batch to
    exactly those real rows instead -- the same real, disclosed test-
    safety boundary `deadline_watch.py`/`spend_alert.py`'s own `user_ids`
    parameter already established.

    Per-negotiation lookup (`user_id`/`trigger_source`) happens INSIDE
    this loop's own per-item `try`/`except`, deliberately -- not in a
    single batch query up front. A real, disclosed correction found
    while writing this module's own tests: an earlier version resolved
    every `negotiation_ids` entry to a real `uuid.UUID` in one up-front
    list comprehension, so a single syntactically-malformed test id
    would raise before the per-item failure isolation below ever ran,
    crashing the WHOLE batch instead of isolating just that one item --
    exactly the property `deadline_watch.py`/`spend_alert.py`'s own
    `test_run_..._a_real_failure_for_one_user_never_blocks_the_rest`
    tests already prove for their own `user_ids` parameter. Fixed by
    moving the lookup (and its own `uuid.UUID()` parse) inside the loop,
    matching that established shape exactly."""
    if negotiation_ids is not None:
        candidate_ids = list(negotiation_ids)
    else:
        candidate_ids = await _fetch_bare_autonomous_negotiation_ids(pool, batch_size=batch_size)

    negotiations_scanned = 0
    negotiations_failed = 0
    negotiations_detailed = 0
    outcome_counts: dict[str, int] = {outcome.name: 0 for outcome in BackfillOutcome}

    for negotiation_id in candidate_ids:
        try:
            row = await pool.fetchrow(
                "SELECT user_id, trigger_source FROM negotiations WHERE negotiation_id = $1", uuid.UUID(negotiation_id)
            )
            if row is None:
                raise ValueError(f"No real negotiations row for negotiation_id={negotiation_id!r}")
            outcome = await generate_detail_for_one_negotiation(
                pool,
                negotiation_id=negotiation_id,
                user_id=str(row["user_id"]),
                trigger_source=row["trigger_source"],
                api_key=api_key,
            )
        except Exception:  # noqa: BLE001 -- one real negotiation's failure must never abort the rest of a real batch
            negotiations_failed += 1
            logger.exception(
                "Real negotiation-detail backfill failed for negotiation_id=%s -- continuing to the next real negotiation",
                negotiation_id,
            )
            continue

        negotiations_scanned += 1
        outcome_counts[outcome.name] += 1
        if outcome is BackfillOutcome.DETAILED:
            negotiations_detailed += 1

    return NegotiationDetailBackfillResult(
        negotiations_scanned=negotiations_scanned,
        negotiations_failed=negotiations_failed,
        negotiations_detailed=negotiations_detailed,
        outcome_counts=outcome_counts,
    )
