"""Real Meeting-Load Defense (Phase 5, `QUORUM_PRODUCTION_COMPLETION_
PLAN.md`) -- proactively flags an over-scheduled day. Real parameters
already specified in `QUORUM_CONFIGURATION_CONSTANTS.md` §4 ("Meeting-
load working hours/day", "Meeting-load buffer fraction", "Meeting-load
overload threshold"), confirmed directly before writing this file, not
invented: `WORKING_HOURS_PER_DAY = 8.0`, `BUFFER_FRACTION = 0.25` (25%
of the day reserved, never bookable), `OVERLOAD_THRESHOLD = 0.7`
(flags when committed time exceeds 70% of buffer-adjusted
availability).

REAL, DELIBERATE SOURCE-AGNOSTIC DESIGN, matching `today.py`'s own
`compute_capacity_state()`/`compute_budget_state()` precedent
(`DEC-119`) and `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §10.5's own
real reconciliation design: this module's real function is pure and
takes `committed_hours` as an already-computed input, never queries
anything itself. The ADD's own §9.2/§10.3 are explicit that real
calendar ground truth is ON-DEVICE (`device_calendar` Flutter package,
zero OAuth), not a backend database -- `QUORUM_PRODUCTION_COMPLETION_
PLAN.md`'s own Phase 5 section names the real, deliberate decision
that a backend `calendar_events` table, if it exists at all, would
only ever hold a thin record of externally-booked events, never a full
mirror of a real user's true calendar. A backend module computing
"today's real meeting load" from its own database alone could never be
honest, so it doesn't try to -- this pure function is the real,
canonical reference implementation, meant to be ported to Dart
(mirroring `computed_state.py`/`computed_state.dart`'s own established
split) so the real, live computation runs where the real committed-
hours figure is actually available, including fully offline (the ADD's
own §10.3 point about `AvailabilityCheck` applies equally here).

HONEST DISCLOSURE: no real backend route or caller invokes this
function yet. The real, on-device `CalendarProvider` integration and
the Dart port of this function are real, separate, substantial mobile
work, tracked as Phase 5's own remaining scope -- not silently assumed
done by this session. `gate/validators.py`'s own real, already-built
`availability_check`/`temporal_fact_check` depend on a real
`CalendarAdapter` implementation that has the same real, unresolved
gap: none exists anywhere in this backend yet, on-device or otherwise,
since no route today ever needs to construct a real Gate proposal
carrying calendar context in the first place (the same "no real
caller" gap `SEND_EMAIL` execution disclosed, `DEC-142`).
"""
from __future__ import annotations

from dataclasses import dataclass

# The three real, named parameters this module needs, pulled directly
# from QUORUM_CONFIGURATION_CONSTANTS.md §4 -- not arbitrary tuning
# knobs invented for this repository. `today.py`'s own `TODAY_WORKING_
# HOURS_PER_DAY` previously duplicated the first of these as a second,
# local `8.0` -- closed by having that module import this one instead
# (this session's own real fix).
WORKING_HOURS_PER_DAY = 8.0
BUFFER_FRACTION = 0.25
OVERLOAD_THRESHOLD = 0.7


@dataclass(frozen=True)
class MeetingLoadState:
    buffer_adjusted_availability_hours: float
    committed_hours: float
    is_overloaded: bool


def compute_meeting_load(
    *,
    committed_hours: float,
    working_hours_per_day: float = WORKING_HOURS_PER_DAY,
    buffer_fraction: float = BUFFER_FRACTION,
    overload_threshold: float = OVERLOAD_THRESHOLD,
) -> MeetingLoadState:
    """Pure, real, deterministic -- see this module's own top-of-file
    docstring for why `committed_hours` is an input, never computed
    here.

    `buffer_adjusted_availability_hours` is the real, bookable portion
    of the day once the real buffer fraction is reserved and never
    offered. `is_overloaded` flags when real committed time exceeds the
    real overload threshold of THAT buffer-adjusted figure, not of the
    raw working day -- confirmed against `QUORUM_CONFIGURATION_
    CONSTANTS.md` §4's own exact wording ("flags when committed time
    exceeds 70% of buffer-adjusted availability"), not the raw 8-hour
    day (a materially different, wrong threshold: 70% of 8.0h is 5.6h,
    not the real 4.2h this module actually flags at with the default
    parameters).

    Defensively clamped, matching `today.py::compute_capacity_state()`'s
    own established precedent: a genuinely non-positive `working_hours_
    per_day` (a real, honest degenerate case -- a caller-supplied
    working day of zero or less) has no real bookable time at all, so
    `buffer_adjusted_availability_hours` is `0.0` and any real, positive
    `committed_hours` is, definitionally, an overload. A negative real
    `committed_hours` (never legitimate, but never trusted blindly
    either) is treated as `0.0`."""
    committed_hours = max(0.0, committed_hours)
    if working_hours_per_day <= 0:
        return MeetingLoadState(
            buffer_adjusted_availability_hours=0.0,
            committed_hours=committed_hours,
            is_overloaded=committed_hours > 0.0,
        )

    buffer_adjusted_availability_hours = working_hours_per_day * (1.0 - buffer_fraction)
    is_overloaded = committed_hours > overload_threshold * buffer_adjusted_availability_hours
    return MeetingLoadState(
        buffer_adjusted_availability_hours=buffer_adjusted_availability_hours,
        committed_hours=committed_hours,
        is_overloaded=is_overloaded,
    )
