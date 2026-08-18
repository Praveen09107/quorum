"""Real impact simulation — the literal proof of "the numbers are
reproducible; only the narration is generative" (QUORUM_ARCHITECTURE_DESIGN
_DOCUMENT.md §8.4). HONEST DISCLOSURE: construction-not-copy pattern, same
as every negotiation/Gate file — DomainSnapshot and OptionEffect have no
full field spec anywhere in the real corpus (QUORUM_DATA_CONTRACTS.md §1.8
documents only the boundary-crossing ImpactDelta exhaustively, explicitly
leaving this module's internal working types to this session, same as
NegotiationOption was left to IMPL_19).

Zero LLM calls, zero external side effects — pure arithmetic, same review
category as IMPL_18's trigger. Every option applies to a real COPY of
domain state; nothing here ever mutates a real, live baseline.

A genuine domain-semantics requirement, not a workaround for a bug that
ever shipped in this repository: task_hours_committed has the OPPOSITE
polarity from the other two metrics. More slack hours before a deadline is
better; more budget remaining is better; but more task hours already
committed is WORSE — it means less real free capacity. _direction() takes
an explicit higher_is_better parameter for exactly this reason, and
compute_deltas() passes higher_is_better=False only at task_hours_committed's
call site. Getting this backwards would silently tell a person that
overcommitting their time is an improvement — the exact failure mode this
parameter exists to make structurally impossible to miss at the call site.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from quorum_backend.gate.schemas import ImpactDelta


@dataclass(frozen=True)
class DomainSnapshot:
    """A real, immutable point-in-time reading of the three standing
    metrics negotiation cares about. frozen=True is load-bearing, not
    decorative — this module must never mutate a real, live baseline while
    computing one option's effect against it."""

    deadline_slack_hours: float
    budget_remaining_fraction: float
    task_hours_committed: float


@dataclass(frozen=True)
class OptionEffect:
    """A real, additive change one negotiation option would apply to a
    DomainSnapshot if chosen. Defaults to an all-zero, genuine no-op — this
    is what makes "do nothing" the same code path as every other option,
    never a special-cased exception."""

    deadline_slack_hours_change: float = 0.0
    budget_remaining_fraction_change: float = 0.0
    task_hours_committed_change: float = 0.0


def apply_effect(baseline: DomainSnapshot, effect: OptionEffect) -> DomainSnapshot:
    """A real copy, via dataclasses.replace — baseline itself is never
    touched. Negotiation code needs to compute several options against the
    SAME baseline without one option's computation corrupting the baseline
    for the next."""

    return replace(
        baseline,
        deadline_slack_hours=baseline.deadline_slack_hours + effect.deadline_slack_hours_change,
        budget_remaining_fraction=baseline.budget_remaining_fraction + effect.budget_remaining_fraction_change,
        task_hours_committed=baseline.task_hours_committed + effect.task_hours_committed_change,
    )


def _direction(
    before: float,
    after: float,
    higher_is_better: bool = True,
) -> Literal["improves", "worsens", "unchanged"]:
    if after == before:
        return "unchanged"
    if higher_is_better:
        return "improves" if after > before else "worsens"
    return "improves" if after < before else "worsens"


def compute_deltas(baseline: DomainSnapshot, effect: OptionEffect) -> list[ImpactDelta]:
    """Every field here is code-computed, never produced by a model call —
    the exact real contract ImpactDelta's own docstring in gate/schemas.py
    already commits to. Returns all three real standing metrics every
    time, in the same order, whether the option changed them or not."""

    after = apply_effect(baseline, effect)
    return [
        ImpactDelta(
            metric="deadline_slack_hours",
            before=baseline.deadline_slack_hours,
            after=after.deadline_slack_hours,
            direction=_direction(baseline.deadline_slack_hours, after.deadline_slack_hours),
        ),
        ImpactDelta(
            metric="budget_remaining_fraction",
            before=baseline.budget_remaining_fraction,
            after=after.budget_remaining_fraction,
            direction=_direction(baseline.budget_remaining_fraction, after.budget_remaining_fraction),
        ),
        ImpactDelta(
            metric="task_hours_committed",
            before=baseline.task_hours_committed,
            after=after.task_hours_committed,
            # Inverted polarity, deliberately -- see module docstring.
            direction=_direction(
                baseline.task_hours_committed,
                after.task_hours_committed,
                higher_is_better=False,
            ),
        ),
    ]


def simulate_all_options(
    baseline: DomainSnapshot,
    option_effects: dict[str, OptionEffect],
) -> dict[str, list[ImpactDelta]]:
    """Runs compute_deltas() once per real option against the SAME
    baseline -- every option, including a genuine "do_nothing" entry the
    caller supplies as an all-zero OptionEffect, takes the identical code
    path. This function never invents a do_nothing entry itself: producing
    the real OptionEffect values for actual synthesized options (do_nothing
    included) is domain-specific wiring work that belongs to IMPL_21, not
    this session -- this function's job is only to prove the computation
    itself is correct, deterministic, and non-mutating for whatever options
    it's given."""

    return {
        option_id: compute_deltas(baseline, effect)
        for option_id, effect in option_effects.items()
    }
