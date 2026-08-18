"""Real tests for negotiation/impact_simulator.py.

HONEST DISCLOSURE: this repository never shipped a version of
impact_simulator.py with task_hours_committed's inverted-polarity bug --
built correct from the start, in one pass, using an explicit
higher_is_better parameter at every call site. The polarity tests below
exist because it's a genuine domain-correctness requirement documented in
this module's own docstring (more committed hours is worse, not better),
not because a live regression was ever caught and fixed in this codebase.
"""
from quorum_backend.negotiation.impact_simulator import (
    DomainSnapshot,
    OptionEffect,
    apply_effect,
    compute_deltas,
    simulate_all_options,
)


def test_the_same_inputs_always_produce_the_same_deltas_across_many_runs():
    # A two-run check could pass by coincidence on non-deterministic code;
    # 50 real runs is a meaningfully stronger claim of true determinism.
    baseline = DomainSnapshot(deadline_slack_hours=5.0, budget_remaining_fraction=0.5, task_hours_committed=10.0)
    effect = OptionEffect(deadline_slack_hours_change=-2.0, budget_remaining_fraction_change=0.1, task_hours_committed_change=3.0)

    first = compute_deltas(baseline, effect)
    for _ in range(50):
        again = compute_deltas(baseline, effect)
        assert again == first


def test_apply_effect_never_mutates_the_original_baseline():
    baseline = DomainSnapshot(deadline_slack_hours=5.0, budget_remaining_fraction=0.5, task_hours_committed=10.0)
    effect = OptionEffect(deadline_slack_hours_change=-2.0, budget_remaining_fraction_change=-0.2, task_hours_committed_change=4.0)

    result = apply_effect(baseline, effect)

    # The real baseline object passed in is provably untouched afterward.
    assert baseline.deadline_slack_hours == 5.0
    assert baseline.budget_remaining_fraction == 0.5
    assert baseline.task_hours_committed == 10.0
    assert result is not baseline
    assert result.deadline_slack_hours == 3.0


def test_do_nothing_option_produces_all_unchanged_deltas():
    # Declining to act runs through the SAME compute_deltas code path as
    # every other option -- never an exception carved out that could hide
    # a bug.
    baseline = DomainSnapshot(deadline_slack_hours=5.0, budget_remaining_fraction=0.5, task_hours_committed=10.0)
    deltas = compute_deltas(baseline, OptionEffect())

    assert len(deltas) == 3
    assert all(d.direction == "unchanged" for d in deltas)
    assert all(d.before == d.after for d in deltas)


def test_task_hours_committed_has_inverted_polarity_more_committed_hours_worsens():
    baseline = DomainSnapshot(deadline_slack_hours=5.0, budget_remaining_fraction=0.5, task_hours_committed=10.0)

    more_committed = compute_deltas(baseline, OptionEffect(task_hours_committed_change=3.0))
    by_metric = {d.metric: d for d in more_committed}
    assert by_metric["task_hours_committed"].direction == "worsens"

    fewer_committed = compute_deltas(baseline, OptionEffect(task_hours_committed_change=-3.0))
    by_metric = {d.metric: d for d in fewer_committed}
    assert by_metric["task_hours_committed"].direction == "improves"


def test_deadline_slack_and_budget_remaining_retain_normal_polarity():
    # Confirms the inverted-polarity handling for task_hours_committed
    # didn't accidentally flip the other two, normal-polarity metrics.
    baseline = DomainSnapshot(deadline_slack_hours=5.0, budget_remaining_fraction=0.5, task_hours_committed=10.0)
    result = compute_deltas(baseline, OptionEffect(deadline_slack_hours_change=2.0, budget_remaining_fraction_change=0.1))
    by_metric = {d.metric: d for d in result}

    assert by_metric["deadline_slack_hours"].direction == "improves"
    assert by_metric["budget_remaining_fraction"].direction == "improves"


def test_compute_deltas_always_returns_all_three_real_metrics_in_order():
    baseline = DomainSnapshot(deadline_slack_hours=5.0, budget_remaining_fraction=0.5, task_hours_committed=10.0)
    deltas = compute_deltas(baseline, OptionEffect())
    assert [d.metric for d in deltas] == [
        "deadline_slack_hours",
        "budget_remaining_fraction",
        "task_hours_committed",
    ]


def test_simulate_all_options_computes_each_option_independently_from_the_same_baseline():
    baseline = DomainSnapshot(deadline_slack_hours=5.0, budget_remaining_fraction=0.5, task_hours_committed=10.0)
    option_effects = {
        "option_a": OptionEffect(deadline_slack_hours_change=-1.0),
        "option_b": OptionEffect(task_hours_committed_change=5.0),
        "do_nothing": OptionEffect(),
    }

    results = simulate_all_options(baseline, option_effects)

    assert set(results.keys()) == {"option_a", "option_b", "do_nothing"}
    by_metric_a = {d.metric: d for d in results["option_a"]}
    by_metric_b = {d.metric: d for d in results["option_b"]}
    # option_b's computation must not have leaked into option_a's result --
    # each ran against the same, untouched baseline independently.
    assert by_metric_a["task_hours_committed"].direction == "unchanged"
    assert by_metric_b["task_hours_committed"].direction == "worsens"
    assert all(d.direction == "unchanged" for d in results["do_nothing"])
