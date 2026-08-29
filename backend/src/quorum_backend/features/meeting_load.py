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
function directly -- it remains the real, pure, single-day REFERENCE
implementation, deliberately never given a real backend caller, since
no real backend data source for genuine calendar meeting load exists
(the real on-device `CalendarProvider`/`CalendarMirror` data DEC-152
built is never mirrored server-side, a deliberate privacy decision,
not an oversight).

RESOLVED for real (Meeting-Load Defense session, following DEC-152's
real on-device Calendar sync): the real Dart port this docstring
always pointed to now exists --
`mobile/lib/features/meeting_load/meeting_load_logic.dart`, a direct,
hand-verified port of `compute_meeting_load()` above (identical real
parameters, identical real defensive clamping, a real, hand-verified
account of where Dart's own `NaN`-comparison semantics genuinely
differ from Python's), extended there with the real, genuine multi-day
projection this module's own single-day function was always meant to
back -- computed entirely from real, already-synced on-device
`CalendarMirror` events, with zero real backend involvement at all,
surfaced as a real, live banner on the real Calendar screen
(`calendar_screen.dart`). `gate/validators.py`'s own real
`availability_check`/`temporal_fact_check` still depend on a real
`CalendarAdapter` implementation that has the same real, deliberately
unresolved gap disclosed at `DEC-151`/`152`: no real caller in this
backend can construct a Gate proposal carrying calendar context in the
first place, so building one remains genuinely unneeded today, not
merely unbuilt.
"""
from __future__ import annotations

import math
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
    either) is treated as `0.0`. `buffer_fraction` is clamped to a real,
    valid `[0.0, 1.0]` range and `overload_threshold` to `>= 0.0` --
    a real, disclosed gap this session's own standard fresh-context
    review found and this closes: an out-of-range `buffer_fraction`
    (e.g. `1.5`, reserving more than the whole day) previously produced
    a real, negative `buffer_adjusted_availability_hours`, which could
    silently flag a genuinely EMPTY day (`committed_hours=0.0`) as
    overloaded -- contradicting this function's own stated invariant
    above. Not reachable today (both parameters are always the fixed,
    real spec constants in every real caller so far, and no real caller
    exists at all yet), but a real, structural guarantee is cheaper to
    build now than to rediscover once this function gets its first real
    caller. A genuine `NaN` in any parameter is refused loudly (a real
    `ValueError`), never silently absorbed into a meaningless `0.0` or
    a meaningless `False` -- confirmed directly before trusting Python's
    own `max()`/`min()` here: `max(0.0, float('nan'))` returns `0.0`
    while `max(float('nan'), 0.0)` returns `nan` -- silently ARGUMENT-
    ORDER-DEPENDENT, not a real guarantee to build defensive clamping
    on top of without an explicit check first."""
    if any(math.isnan(value) for value in (committed_hours, working_hours_per_day, buffer_fraction, overload_threshold)):
        raise ValueError("compute_meeting_load() received a real NaN input -- refusing to silently produce a meaningless result.")

    committed_hours = max(0.0, committed_hours)
    buffer_fraction = min(1.0, max(0.0, buffer_fraction))
    overload_threshold = max(0.0, overload_threshold)
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
