"""Real tests for the two validators that predate the numbered IMPL_01-07
batch (per this project's own kickoff-guide convention): TemporalFactCheck
and BudgetCheck. Built alongside IMPL_07 in this repository since nothing
needed them until closing the "all 9 validators" gate."""
from datetime import datetime

from quorum_backend.gate.validators import budget_check, temporal_fact_check


class FakeCalendarForTemporal:
    def __init__(self, events: dict[str, dict]):
        self._events = events

    def find_event(self, description: str) -> dict | None:
        return self._events.get(description)

    def list_events_in_range(self, start: datetime, end: datetime) -> list[dict]:
        return []


def test_temporal_fact_check_verified_true_when_event_found():
    cal = FakeCalendarForTemporal({"meeting with Priya": {"id": "evt_1"}})
    finding = temporal_fact_check("meeting with Priya", cal)
    assert finding.evidence_state == "verified_true"
    assert finding.source_ref is not None
    assert finding.source_ref.source_id == "evt_1"


def test_temporal_fact_check_no_data_found_not_false_when_absent():
    # The single most important behavioral guarantee in the whole Gate --
    # explicitly asserted != "verified_false", not just == "no_data_found",
    # matching the real spec's own proof pattern.
    cal = FakeCalendarForTemporal({})
    finding = temporal_fact_check("meeting that was never entered", cal)
    assert finding.evidence_state != "verified_false"
    assert finding.evidence_state == "no_data_found"


def test_temporal_fact_check_verified_true_when_no_meeting_claimed():
    cal = FakeCalendarForTemporal({})
    finding = temporal_fact_check(None, cal)
    assert finding.evidence_state == "verified_true"


class FakeBudget:
    def __init__(self, remaining: float):
        self._remaining = remaining

    def get_remaining_budget(self, category: str) -> float:
        return self._remaining


def test_budget_check_verified_true_when_within_remaining():
    budget = FakeBudget(remaining=500.0)
    finding = budget_check(300.0, "travel", budget)
    assert finding.evidence_state == "verified_true"


def test_budget_check_verified_false_when_exceeds_remaining():
    budget = FakeBudget(remaining=100.0)
    finding = budget_check(300.0, "travel", budget)
    assert finding.evidence_state == "verified_false"


def test_budget_check_verified_true_when_no_amount_claimed():
    budget = FakeBudget(remaining=0.0)
    finding = budget_check(None, "travel", budget)
    assert finding.evidence_state == "verified_true"


def test_budget_check_exact_boundary_is_verified_true_not_false():
    budget = FakeBudget(remaining=300.0)
    finding = budget_check(300.0, "travel", budget)
    assert finding.evidence_state == "verified_true"
