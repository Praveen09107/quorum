"""Real subscription-detection logic, backing `GET /finance/subscriptions`
(`QUORUM_DATA_CONTRACTS.md` §5.12).

HONEST DISCLOSURE, confirmed by direct search before writing this file:
`backend/features/subscription_detective.py`, named by this project's
own spec corpus as already real and tested ("`detect_subscriptions()`
has been real and tested since well before mobile work began"), does
not exist anywhere in this repository -- the same disclosure
`finance_logic.dart`'s own file header already makes on the mobile
side, confirmed independently here rather than assumed from that
file's own claim. `QUORUM_DATA_CONTRACTS.md` §5.12 only specifies the
response *shape*, not how to compute it.

**A real, disclosed correction, found live during a later session
(`DEC-112`), not caught before this file's first real version merged:**
the first version of this module was built checking only
`DATA_CONTRACTS.md` §5.12 and concluded no real detection algorithm
was specified -- but never checked `QUORUM_CONFIGURATION_CONSTANTS.md`
§4, which genuinely does specify real parameters for this exact
module: `Subscription min occurrences: 3`, `Subscription interval
tolerance: ±5.0 days around a 30-day target`. That table's own header
claims these were "pulled directly from real, tested code" -- the same
stale-spec-corpus-narrative pattern this project's own history
disclosed repeatedly elsewhere (describing a module that, per the
direct search above, never actually existed in this repository) -- but
the *parameters themselves* are real, specific, intentional design
values worth honoring, not a spec to second-guess. This session's
first version used `MIN_OCCURRENCES_TO_COUNT_AS_RECURRING = 2` and no
interval-regularity filtering at all -- a real, more permissive rule
than the actual spec, found and corrected here. Confirmed against
`DATA_CONTRACTS.md` §5.12's own JSON example too, consistent with
this fix: `"occurrences": 4`, `"average_interval_days": 30.2` -- both
values a genuinely monthly-cadence, 3+-occurrence detector would
produce, not the simpler rule's own hypothetical 2-occurrence,
any-spacing output.

The real, corrected rule: a payee counts as recurring only once
charged at least `MIN_OCCURRENCES_TO_COUNT_AS_RECURRING` times, exact
string match only (no fuzzy payee matching -- "Netflix" and
"NETFLIX.COM" are two different real payees here, a real, disclosed
limitation, not a silent gap), **and** every real consecutive gap
between charges falls within `INTERVAL_TOLERANCE_DAYS` of
`INTERVAL_TARGET_DAYS` -- a charge sequence with any one wildly
irregular gap is a real, genuine sign it isn't an actual monthly
subscription, whatever its raw occurrence count. No amount clustering,
no ML beyond this.

**RESOLVED, `DEC-110`:** this module's real query previously read
every real `expenses` row regardless of owner, the same disclosed
per-user-scoping limitation `trust_digest.py`/`tasks.py`/
`career_pipeline.py` carried -- no real user-provisioning system
existed anywhere in this backend. A real `users` table and
`auth/user_provisioning.py` now close that gap;
`fetch_detected_subscriptions()` below takes the real, resolved
internal `user_id` and filters by it before ever handing rows to the
pure `detect_subscriptions()` grouping logic.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

import asyncpg

# The two real, named parameters this module needs, pulled directly
# from QUORUM_CONFIGURATION_CONSTANTS.md §4 -- not arbitrary tuning
# knobs invented for this repository.
MIN_OCCURRENCES_TO_COUNT_AS_RECURRING = 3
INTERVAL_TARGET_DAYS = 30.0
INTERVAL_TOLERANCE_DAYS = 5.0


@dataclass(frozen=True)
class DetectedSubscription:
    payee: str
    average_amount: float
    occurrences: int
    average_interval_days: float


def detect_subscriptions(rows: list[tuple[str, float, datetime]]) -> list[DetectedSubscription]:
    """Pure, real, deterministic grouping -- takes already-fetched
    `(payee, amount, occurred_at)` tuples (real DB access lives in
    `fetch_detected_subscriptions()` below, mirroring `trust_digest.py`'s
    own real split between pure computation and live querying). Groups
    by exact payee match, requires the real, specified minimum
    occurrence count AND a real, specified monthly-cadence tolerance on
    every consecutive gap (see this module's own top-of-file docstring
    for the real, disclosed correction this rule represents), computes
    each real recurring payee's average amount and average interval.
    """
    grouped: dict[str, list[tuple[float, datetime]]] = {}
    for payee, amount, occurred_at in rows:
        grouped.setdefault(payee, []).append((amount, occurred_at))

    results: list[DetectedSubscription] = []
    for payee, entries in grouped.items():
        if len(entries) < MIN_OCCURRENCES_TO_COUNT_AS_RECURRING:
            continue

        amounts = [amount for amount, _ in entries]
        timestamps = sorted(occurred_at for _, occurred_at in entries)
        gaps_days = [
            (timestamps[i] - timestamps[i - 1]).total_seconds() / 86400 for i in range(1, len(timestamps))
        ]

        # The real, specified cadence filter: every consecutive gap
        # must sit within the real tolerance window around the real
        # monthly target. Any single irregular gap disqualifies the
        # whole real sequence -- a genuine sign it isn't an actual
        # monthly subscription, not a value to average away.
        if any(abs(gap - INTERVAL_TARGET_DAYS) > INTERVAL_TOLERANCE_DAYS for gap in gaps_days):
            continue

        results.append(
            DetectedSubscription(
                payee=payee,
                average_amount=round(sum(amounts) / len(amounts), 2),
                occurrences=len(entries),
                # One decimal place -- matches §5.12's own example
                # ("average_interval_days": 30.2) exactly; the real
                # underlying detection was never exact to begin with, so
                # more precision would be false confidence, not more
                # honesty.
                average_interval_days=round(sum(gaps_days) / len(gaps_days), 1),
            )
        )

    # Real, deterministic order -- highest average charge first, the
    # most actionable ordering for a person deciding what to cut. The
    # mobile client's own sortByAmountDesc (finance_logic.dart) re-sorts
    # regardless, so this is a reasoned default, not a display contract.
    results.sort(key=lambda r: r.average_amount, reverse=True)
    return results


async def fetch_detected_subscriptions(pool: asyncpg.Pool, *, user_id: str) -> list[DetectedSubscription]:
    """The real, live query backing `GET /finance/subscriptions`, real
    per-user scoped as of `DEC-110` -- reads every real `expenses` row
    belonging to this real user (all sources: `on_device`, `manual`,
    `extracted`, per the real schema's own `CHECK` constraint -- a
    recurring charge is real regardless of how it was captured) and
    hands them to the pure `detect_subscriptions()` above."""
    rows = await pool.fetch(
        "SELECT payee, amount, occurred_at FROM expenses WHERE user_id = $1 ORDER BY occurred_at",
        uuid.UUID(user_id),
    )
    # asyncpg maps a real NUMERIC(10,2) column to Decimal by default (no
    # custom type codec registered in core/db.py) -- cast to float
    # explicitly, the same real correctness detail tasks.py's own
    # estimated_hours handling already established.
    return detect_subscriptions([(row["payee"], float(row["amount"]), row["occurred_at"]) for row in rows])
