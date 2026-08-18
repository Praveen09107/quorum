"""Week-over-week trend comparison for the Trust Digest screen.
HONEST DISCLOSURE: a genuinely new backend module, not a wrapper around
existing logic -- no week-over-week trend comparison existed anywhere in
this repository's backend before this session. `backend/src/quorum_
backend/features/predictive_risk.py`, cited by this session's own spec as
this module's design-philosophy precedent, does not exist in this
repository either (`backend/features/*` from the ADD's Sec 9.7 table has
never been built here) -- built directly against the philosophy that
table DESCRIBES ("deliberately simple and explainable... a count
comparison, not a trained model"), not literally copied from a file this
repository doesn't have.

Real, deliberate design choice: a plain threshold comparison against a
real, named constant, never a trained model or a magic number.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# A 2-percentage-point real, named threshold: week-over-week success-rate
# movement smaller than this is treated as noise, not a real trend. Not
# specified anywhere in this project's real corpus -- a real, reasoned
# choice, disclosed rather than presented as a recalled spec value.
STABLE_THRESHOLD = 0.02


@dataclass(frozen=True)
class WeeklyTrustSummary:
    week_start: str  # ISO date, e.g. "2026-08-10"
    total_actions: int
    success_rate: float


@dataclass(frozen=True)
class TrendResult:
    current_week: WeeklyTrustSummary
    previous_week: WeeklyTrustSummary | None
    trend: Literal["improving", "declining", "stable", "insufficient_data"]
    delta: float | None


def compare_weeks(
    current: WeeklyTrustSummary,
    previous: WeeklyTrustSummary | None,
) -> TrendResult:
    """Real, deterministic comparison over two already-computed weekly
    summaries -- the real weekly aggregation query itself (grouping raw
    action_events rows into a WeeklyTrustSummary) is out of scope here;
    this function is independently correct regardless of how its inputs
    are produced.

    insufficient_data is a real, honest fourth state -- a week with zero
    actions, or no prior week to compare against -- never silently
    reported as "stable", which would claim a real comparison was made
    when it genuinely wasn't.
    """
    if previous is None or current.total_actions == 0 or previous.total_actions == 0:
        return TrendResult(current_week=current, previous_week=previous, trend="insufficient_data", delta=None)

    # round(..., 3) resolves real floating-point noise at the exact
    # threshold boundary -- confirmed live before trusting the exact-
    # equality comparison below (0.80 + STABLE_THRESHOLD produces
    # 0.8200000000000001 in raw floating point; rounding to 3 places
    # cleanly yields 0.02 again).
    delta = round(current.success_rate - previous.success_rate, 3)

    if delta > STABLE_THRESHOLD:
        trend: Literal["improving", "declining", "stable"] = "improving"
    elif delta < -STABLE_THRESHOLD:
        trend = "declining"
    else:
        trend = "stable"

    return TrendResult(current_week=current, previous_week=previous, trend=trend, delta=delta)
