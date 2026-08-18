"""Real tests for features/trust_digest.py."""
from quorum_backend.features.trust_digest import STABLE_THRESHOLD, WeeklyTrustSummary, compare_weeks


def test_improving_trend_detected_above_threshold():
    current = WeeklyTrustSummary(week_start="2026-08-10", total_actions=24, success_rate=0.875)
    previous = WeeklyTrustSummary(week_start="2026-08-03", total_actions=19, success_rate=0.789)
    result = compare_weeks(current, previous)
    assert result.trend == "improving"
    assert result.delta is not None and result.delta > STABLE_THRESHOLD


def test_declining_trend_detected_below_negative_threshold():
    current = WeeklyTrustSummary(week_start="2026-08-10", total_actions=20, success_rate=0.70)
    previous = WeeklyTrustSummary(week_start="2026-08-03", total_actions=20, success_rate=0.90)
    result = compare_weeks(current, previous)
    assert result.trend == "declining"
    assert result.delta is not None and result.delta < -STABLE_THRESHOLD


def test_stable_trend_within_threshold_band():
    current = WeeklyTrustSummary(week_start="2026-08-10", total_actions=20, success_rate=0.81)
    previous = WeeklyTrustSummary(week_start="2026-08-03", total_actions=20, success_rate=0.80)
    result = compare_weeks(current, previous)
    assert result.trend == "stable"


def test_exact_threshold_boundary_is_classified_as_stable_not_improving():
    # Real, live-confirmed floating-point safety: 0.80 + STABLE_THRESHOLD
    # produces 0.8200000000000001 in raw floating point; round(..., 3)
    # cleanly resolves this to exactly STABLE_THRESHOLD, confirmed before
    # writing this test.
    previous = WeeklyTrustSummary(week_start="2026-08-03", total_actions=20, success_rate=0.80)
    current = WeeklyTrustSummary(week_start="2026-08-10", total_actions=20, success_rate=0.80 + STABLE_THRESHOLD)
    result = compare_weeks(current, previous)
    assert result.delta == STABLE_THRESHOLD
    assert result.trend == "stable", "a delta exactly AT the threshold must not count as a real improvement"


def test_no_previous_week_is_insufficient_data():
    current = WeeklyTrustSummary(week_start="2026-08-10", total_actions=24, success_rate=0.875)
    result = compare_weeks(current, None)
    assert result.trend == "insufficient_data"
    assert result.delta is None


def test_previous_week_with_zero_actions_is_insufficient_data():
    current = WeeklyTrustSummary(week_start="2026-08-10", total_actions=24, success_rate=0.875)
    previous = WeeklyTrustSummary(week_start="2026-08-03", total_actions=0, success_rate=0.0)
    result = compare_weeks(current, previous)
    assert result.trend == "insufficient_data"


def test_current_week_with_zero_actions_is_insufficient_data():
    current = WeeklyTrustSummary(week_start="2026-08-10", total_actions=0, success_rate=0.0)
    previous = WeeklyTrustSummary(week_start="2026-08-03", total_actions=19, success_rate=0.789)
    result = compare_weeks(current, previous)
    assert result.trend == "insufficient_data"
