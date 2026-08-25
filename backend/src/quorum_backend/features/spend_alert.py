"""The real, second autonomous negotiation-trigger job -- Phase 2 of
`QUORUM_PRODUCTION_COMPLETION_PLAN.md`, real spend-alert monitoring,
per `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §8.6's own real framing:
the negotiation trigger extends beyond rare literal collisions to
everyday tensions including "spontaneous-spend-vs-known-upcoming-cost"
-- same real machinery `features/deadline_watch.py` (`DEC-132`) already
proved out, a genuinely different real trigger condition.

REAL, CONFIRMED DESIGN (Preethish, directly, before writing a line of
this file): a real recurring subscription's ongoing cost, checked
against real remaining monthly budget, at the same real moment the
user's real tasks are also overcommitted -- reusing `subscription_
detective.py`'s own already-real, already-tested detection algorithm
(`detect_subscriptions()`, pure, unchanged, not duplicated), not a
single-large-expense heuristic this session would have had to invent.
**A REAL, DISCLOSED CORRECTION to this paragraph's own earlier wording:**
this scan re-evaluates EVERY currently-detected subscription on every
real run, not only a newly-appeared one -- "NEW" in an earlier draft of
this docstring overclaimed a real notion of novelty the code never
actually tracked.

WHY THIS NEEDS `trigger_source` (migration `0008`), NOT JUST A
GENERIC "unresolved negotiation" CHECK: `scan_for_conflicts` requires
2+ conflicted domains to trigger at all (confirmed against `negotiation
/trigger.py` before designing this) -- a finance-only signal alone can
never create a real negotiation. This module's own real finance claim
is the SUM of every real, currently-detected recurring subscription's
own `average_amount` (not just the priciest one -- a genuine, real
picture of total ongoing recurring burden, not a partial one), checked
against the same real tasks-domain claim `deadline_watch.py` already
computes (`features/negotiation_trigger_support.py::
build_tasks_claim_and_state`, shared, not duplicated).

**A REAL, DISCLOSED CORRECTION, found by this session's own CRITICAL-
tier review:** the real, precise idempotency key was originally
`spend_alert:<payee>` for the single most expensive real detected
subscription. Live-proven by the review to be the wrong real anchor:
an entirely ordinary month-to-month shift in which real subscription
happens to cost the most (a new bill arrives, a price changes) flips
this key even though the user's real underlying financial strain is
genuinely unchanged, silently defeating `BARE_NEGOTIATION_COOLDOWN_
HOURS` and spamming a fresh, duplicate bare negotiation for the SAME
real situation. Fixed: `SPEND_ALERT_TRIGGER_SOURCE` below is a single,
job-wide key, not payee-scoped -- correct because the bare negotiation
row this module creates carries no payee-specific content yet (real
Gemini-backed detail generation, this module's own disclosed, still-
open item below), so there is nothing payee-specific to lose by
de-scoping the key. This key stays genuinely independent of `deadline
_watch.py`'s own `'deadline_watch'`-keyed negotiations for the same
user (`negotiation_trigger_support.py`'s own top-of-file docstring has
the full real reasoning for why an exact `trigger_source` match is
what keeps two DIFFERENT real jobs' own bare negotiations from
suppressing each other -- a real, disclosed, deliberately NOT-yet-closed
gap remains one level up from that: two DIFFERENT real jobs can still
each independently create their own real, unresolved negotiation for
what may be the same underlying real resource strain, rendering as two
separate, un-mergeable cards on a real Today screen -- tracked as a
genuine, still-open item, not silently assumed solved by this fix).

A REAL, DELIBERATE SCOPE BOUNDARY, DISCLOSED HERE, matching `deadline_
watch.py`'s own precedent exactly: this module creates the bare
negotiation row only -- real Gemini-backed positions/options are a
genuine, separate, still-open item, for the same real, disclosed
Gemini-quota reason that module's own top-of-file docstring already
explains.

A user with no real detected recurring subscription has no real claim
to construct -- skipped honestly (`ScanOutcome.NO_CLAIM`), never
defaulted to zero.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from enum import Enum, auto

import asyncpg

from quorum_backend.features.negotiation_trigger_support import (
    build_tasks_claim_and_state,
    create_bare_negotiation,
    fetch_remaining_monthly_budget,
    has_blocking_negotiation,
)
from quorum_backend.features.subscription_detective import DetectedSubscription, detect_subscriptions
from quorum_backend.gate.schemas import ResourceClaim
from quorum_backend.negotiation.trigger import DomainState, scan_for_conflicts

# Same real logger name main.py's own module-level logger already uses.
logger = logging.getLogger("quorum_backend")

# The real trigger_source (migration 0008) this module writes onto
# every negotiation it creates -- a single, job-wide key, not payee-
# scoped; see this module's own top-of-file docstring for the real,
# disclosed correction that established this (a payee-scoped anchor
# let an ordinary priciest-subscription change spam a duplicate bare
# negotiation for an unchanged real situation).
SPEND_ALERT_TRIGGER_SOURCE = "spend_alert"


class SpendAlertUserNotFoundError(Exception):
    """Same real gap, same real fix as `deadline_watch.py`'s own
    `DeadlineWatchUserNotFoundError` -- a missing `FOR UPDATE` lock row
    means a genuinely nonexistent user, raised loud rather than
    silently scanned unserialized."""


class ScanOutcome(Enum):
    NO_CLAIM = auto()  # no real detected recurring subscription -- honestly skipped
    NO_CONFLICT = auto()  # a real claim exists but doesn't exceed real available capacity
    ALREADY_NEGOTIATING = auto()  # a real conflict, but a real, unresolved negotiation already covers it
    CREATED = auto()  # a real, genuine conflict -- a new, bare negotiation row was created


@dataclass(frozen=True)
class SpendAlertResult:
    users_scanned: int
    users_failed: int
    negotiations_created: int
    outcome_counts: dict[str, int]


async def _fetch_detected_subscriptions_via_conn(conn: asyncpg.Connection, *, user_id: str) -> list[DetectedSubscription]:
    """Real, live query -- the same real logic `subscription_detective.
    py::fetch_detected_subscriptions` already applies, queried directly
    on the SAME real transaction's own `conn` here (not that function's
    own `pool` parameter), so this module's own read is transaction-
    consistent with the rest of the per-user check-and-create block,
    the same real discipline `deadline_watch.py` already established.
    Reuses `detect_subscriptions()` -- the real, pure, already-tested
    grouping logic -- directly, never reimplemented."""
    rows = await conn.fetch(
        "SELECT payee, amount, occurred_at FROM expenses WHERE user_id = $1 ORDER BY occurred_at",
        uuid.UUID(user_id),
    )
    return detect_subscriptions([(row["payee"], float(row["amount"]), row["occurred_at"]) for row in rows])


async def scan_one_user(conn: asyncpg.Connection, *, user_id: str) -> tuple[ScanOutcome, str | None]:
    """Real, live, per-user scan -- mirrors `deadline_watch.py::
    scan_one_user`'s own real shape exactly. Returns `(outcome,
    negotiation_id)` -- `negotiation_id` is only ever real and
    non-`None` for `ScanOutcome.CREATED`."""
    subscriptions = await _fetch_detected_subscriptions_via_conn(conn, user_id=user_id)
    if not subscriptions:
        return ScanOutcome.NO_CLAIM, None

    total_recurring_cost = sum(sub.average_amount for sub in subscriptions)

    remaining_budget = await fetch_remaining_monthly_budget(conn, user_id=user_id)
    resource_claims = [ResourceClaim(claim_type="money", amount=total_recurring_cost, unit="currency_minor_units")]
    domain_states = {"finance": DomainState(domain="finance", available=remaining_budget, unit="currency_minor_units")}

    tasks_claim_and_state = await build_tasks_claim_and_state(conn, user_id=user_id)
    if tasks_claim_and_state is not None:
        tasks_claim, tasks_state = tasks_claim_and_state
        resource_claims.append(tasks_claim)
        domain_states["tasks"] = tasks_state

    scan_result = scan_for_conflicts(resource_claims, domain_states)
    if not scan_result.triggers_negotiation:
        return ScanOutcome.NO_CONFLICT, None

    if await has_blocking_negotiation(conn, user_id=user_id, trigger_source=SPEND_ALERT_TRIGGER_SOURCE):
        return ScanOutcome.ALREADY_NEGOTIATING, None

    negotiation_id = await create_bare_negotiation(
        conn, user_id=user_id, conflicted_domains=scan_result.conflicted_domains, trigger_source=SPEND_ALERT_TRIGGER_SOURCE
    )
    return ScanOutcome.CREATED, negotiation_id


async def run_spend_alert(pool: asyncpg.Pool, *, user_ids: list[str] | None = None) -> SpendAlertResult:
    """The real entry point -- `POST /internal/spend-alert` (`main.py`)
    calls this with `user_ids=None` (the real, live default). Mirrors
    `deadline_watch.py::run_deadline_watch`'s own real shape exactly,
    including every real, live-proven fix that module's own CRITICAL-
    tier review found: a real `FOR UPDATE` lock (raising loud on a
    missing user row, never silently unserialized), and real, per-user
    failure isolation (one real user's own failure is logged, tallied
    into `users_failed`, and never aborts the scan for every other real
    user). `user_ids`, when explicitly passed, scopes the scan to
    exactly those real users -- the same real, disclosed test-safety
    boundary `deadline_watch.py`'s own test suite already established,
    applied here from this module's first version, not retrofitted
    after a real incident."""
    if user_ids is None:
        user_ids = [str(row["user_id"]) for row in await pool.fetch("SELECT user_id FROM users")]

    users_scanned = 0
    users_failed = 0
    negotiations_created = 0
    outcome_counts: dict[str, int] = {outcome.name: 0 for outcome in ScanOutcome}

    for user_id in user_ids:
        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    lock_row = await conn.fetchrow("SELECT user_id FROM users WHERE user_id = $1 FOR UPDATE", uuid.UUID(user_id))
                    if lock_row is None:
                        raise SpendAlertUserNotFoundError(
                            f"No real users row for user_id={user_id!r} -- cannot safely lock/scan a nonexistent user"
                        )
                    outcome, _negotiation_id = await scan_one_user(conn, user_id=user_id)
        except Exception:  # noqa: BLE001 -- deliberately broad, same real reasoning as deadline_watch.py::run_deadline_watch
            users_failed += 1
            logger.exception("Real spend-alert scan failed for user_id=%s -- continuing to the next real user", user_id)
            continue

        users_scanned += 1
        outcome_counts[outcome.name] += 1
        if outcome is ScanOutcome.CREATED:
            negotiations_created += 1

    return SpendAlertResult(
        users_scanned=users_scanned,
        users_failed=users_failed,
        negotiations_created=negotiations_created,
        outcome_counts=outcome_counts,
    )
