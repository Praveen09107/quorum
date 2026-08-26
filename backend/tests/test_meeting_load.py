"""Real tests for features/meeting_load.py (Phase 5, DEC-144). Zero
database access, zero external calls -- `compute_meeting_load()` is
pure, so every test here is a pure, deterministic assertion, matching
`test_subscription_detective.py`'s own established style for this
project's other pure-computation modules.
"""
import pytest

from quorum_backend.features.meeting_load import (
    BUFFER_FRACTION,
    OVERLOAD_THRESHOLD,
    WORKING_HOURS_PER_DAY,
    compute_meeting_load,
)

# A real, hand-verified float fact, confirmed directly before trusting
# it (this project's own established discipline for exact boundary
# tests): with the real, specified defaults, `0.7 * (8.0 * 0.75)` is
# NOT exactly `4.2` in IEEE-754 double precision -- it's
# `4.199999999999999`, since `0.7` has no exact binary representation.
# Computing the real boundary the same way `compute_meeting_load()`
# does, rather than hardcoding a literal `4.2`, is what makes the
# "at the boundary" test genuinely test the boundary.
_DEFAULT_BUFFER_ADJUSTED_HOURS = WORKING_HOURS_PER_DAY * (1.0 - BUFFER_FRACTION)
_DEFAULT_OVERLOAD_BOUNDARY_HOURS = OVERLOAD_THRESHOLD * _DEFAULT_BUFFER_ADJUSTED_HOURS


def test_compute_meeting_load_default_buffer_adjusted_availability_is_six_hours():
    # The real, specified defaults: 8.0h working day, 25% buffer
    # reserved -> 6.0h genuinely bookable. Hand-verified: 8.0 * 0.75 is
    # exactly representable, no float-tolerance needed here.
    result = compute_meeting_load(committed_hours=0.0)
    assert result.buffer_adjusted_availability_hours == 6.0


def test_compute_meeting_load_a_light_day_is_not_overloaded():
    result = compute_meeting_load(committed_hours=2.0)
    assert result.is_overloaded is False
    assert result.committed_hours == 2.0


def test_compute_meeting_load_exactly_at_the_real_boundary_is_not_overloaded():
    """Deliberately strict `>`, not `>=` -- matches `QUORUM_
    CONFIGURATION_CONSTANTS.md` §4's own exact wording ("flags when
    committed time EXCEEDS 70%"), not "meets or exceeds"."""
    result = compute_meeting_load(committed_hours=_DEFAULT_OVERLOAD_BOUNDARY_HOURS)
    assert result.is_overloaded is False


def test_compute_meeting_load_just_past_the_real_boundary_is_overloaded():
    result = compute_meeting_load(committed_hours=_DEFAULT_OVERLOAD_BOUNDARY_HOURS + 0.01)
    assert result.is_overloaded is True


def test_compute_meeting_load_a_genuinely_full_day_is_overloaded():
    result = compute_meeting_load(committed_hours=8.0)
    assert result.is_overloaded is True


def test_compute_meeting_load_zero_committed_hours_is_never_overloaded():
    result = compute_meeting_load(committed_hours=0.0)
    assert result.is_overloaded is False


def test_compute_meeting_load_a_real_negative_committed_hours_is_clamped_to_zero():
    """Never legitimate (a real calendar duration can't be negative),
    but never trusted blindly either -- matches `today.py::compute_
    capacity_state()`'s own established defensive-clamping precedent."""
    result = compute_meeting_load(committed_hours=-3.0)
    assert result.committed_hours == 0.0
    assert result.is_overloaded is False


def test_compute_meeting_load_a_real_custom_working_day_is_honored():
    # A real, custom 10-hour working day, the real, specified default
    # buffer/threshold -- hand-verified: 10.0 * 0.75 = 7.5,
    # 0.7 * 7.5 = 5.25 (both exact in float, no tolerance needed).
    result = compute_meeting_load(committed_hours=5.0, working_hours_per_day=10.0)
    assert result.buffer_adjusted_availability_hours == 7.5
    assert result.is_overloaded is False

    result_overloaded = compute_meeting_load(committed_hours=5.3, working_hours_per_day=10.0)
    assert result_overloaded.is_overloaded is True


def test_compute_meeting_load_a_real_custom_buffer_fraction_is_honored():
    # A real, custom 0% buffer -- the full real working day is
    # genuinely bookable.
    result = compute_meeting_load(committed_hours=6.0, buffer_fraction=0.0)
    assert result.buffer_adjusted_availability_hours == WORKING_HOURS_PER_DAY


def test_compute_meeting_load_a_real_custom_overload_threshold_is_honored():
    # A real, custom, stricter 50% threshold over the real, default
    # 6.0h buffer-adjusted availability -> boundary is 3.0h exactly.
    result = compute_meeting_load(committed_hours=3.0, overload_threshold=0.5)
    assert result.is_overloaded is False
    result_over = compute_meeting_load(committed_hours=3.1, overload_threshold=0.5)
    assert result_over.is_overloaded is True


def test_compute_meeting_load_a_genuinely_nonpositive_working_day_has_zero_bookable_time():
    """A real, honest degenerate case -- a caller-supplied working day
    of zero or less has no real bookable time at all, so ANY real,
    positive committed time is, definitionally, an overload."""
    result = compute_meeting_load(committed_hours=0.5, working_hours_per_day=0.0)
    assert result.buffer_adjusted_availability_hours == 0.0
    assert result.is_overloaded is True

    result_zero_committed = compute_meeting_load(committed_hours=0.0, working_hours_per_day=0.0)
    assert result_zero_committed.is_overloaded is False

    result_negative_working_day = compute_meeting_load(committed_hours=1.0, working_hours_per_day=-2.0)
    assert result_negative_working_day.buffer_adjusted_availability_hours == 0.0
    assert result_negative_working_day.is_overloaded is True


# --- Real, disclosed gaps found by this session's own standard review, fixed here ---


def test_compute_meeting_load_an_out_of_range_buffer_fraction_never_flags_a_genuinely_empty_day():
    """A real, disclosed MEDIUM finding from this session's own
    standard fresh-context review: a `buffer_fraction` above `1.0`
    (reserving more than the whole day) used to produce a real,
    negative `buffer_adjusted_availability_hours`, which could flag a
    genuinely EMPTY day (`committed_hours=0.0`) as overloaded --
    contradicting this function's own stated invariant. Clamped to a
    real, valid `[0.0, 1.0]` range now."""
    result = compute_meeting_load(committed_hours=0.0, buffer_fraction=1.5)
    assert result.buffer_adjusted_availability_hours == 0.0  # clamped to 1.0, not -0.5
    assert result.is_overloaded is False  # zero real commitments is never an overload


def test_compute_meeting_load_a_negative_buffer_fraction_is_clamped_to_zero():
    result = compute_meeting_load(committed_hours=0.0, buffer_fraction=-0.5)
    assert result.buffer_adjusted_availability_hours == WORKING_HOURS_PER_DAY  # clamped to 0.0 -- no buffer reserved


def test_compute_meeting_load_a_negative_overload_threshold_never_flags_a_genuinely_empty_day():
    """The same real class of gap as the `buffer_fraction` finding
    above, for `overload_threshold` specifically: a negative threshold
    made `committed_hours=0.0` compare greater than a negative real
    number, flagging an empty day as overloaded."""
    result = compute_meeting_load(committed_hours=0.0, overload_threshold=-0.1)
    assert result.is_overloaded is False


def test_compute_meeting_load_refuses_a_real_nan_committed_hours_loudly():
    """A real, disclosed LOW finding: `max(0.0, float('nan'))` silently
    returns `0.0` in real Python (argument-order-dependent, confirmed
    directly before trusting it) -- a genuine NaN must never be
    silently absorbed into a meaningless result; it must fail loud."""
    with pytest.raises(ValueError, match="NaN"):
        compute_meeting_load(committed_hours=float("nan"))


def test_compute_meeting_load_refuses_a_real_nan_in_any_other_parameter_loudly():
    with pytest.raises(ValueError, match="NaN"):
        compute_meeting_load(committed_hours=1.0, working_hours_per_day=float("nan"))
    with pytest.raises(ValueError, match="NaN"):
        compute_meeting_load(committed_hours=1.0, buffer_fraction=float("nan"))
    with pytest.raises(ValueError, match="NaN"):
        compute_meeting_load(committed_hours=1.0, overload_threshold=float("nan"))
