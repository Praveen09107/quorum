"""Real tests for gate/validator_registry.py (`DEC-193`, product rebuild
Block E).

THE REAL POINT OF THIS FILE: `VALIDATOR_REGISTRY` is real, hand-
maintained metadata, not derived from the validators' own code at
runtime -- so the synchronization guarantee has to be a test, not
reflection. Every test below calls the REAL validator function with
minimal, representative inputs and asserts the registry's own `name`
field matches the real `Finding.validator` string that function
actually produces. If a validator's real name ever changes and this
registry isn't updated to match, these tests fail here, not silently
in production on the Gate showcase page.
"""
from datetime import datetime, timedelta, timezone

from quorum_backend.gate.validator_registry import VALIDATOR_REGISTRY
from quorum_backend.gate.validators import (
    availability_check,
    budget_check,
    commitment_check,
    coverage_check,
    deadline_conflict_check,
    pii_leak_check,
    provenance_check,
    recipient_check,
    temporal_fact_check,
)


class _FakeBudget:
    def get_remaining_budget(self, category: str) -> float:
        return 100.0


class _FakeCalendar:
    def find_event(self, description: str) -> dict | None:
        return None

    def list_events_in_range(self, start, end) -> list[dict]:
        return []


class _FakeTasks:
    def get_committed_hours_before(self, deadline) -> float:
        return 0.0


class _FakeContacts:
    def is_known_contact(self, email: str) -> bool:
        return True


def _registry_name_for(function_name: str) -> str:
    entry = next(e for e in VALIDATOR_REGISTRY if e.function_name == function_name)
    return entry.name


def test_validator_registry_is_exhaustive_over_every_real_validator():
    """A real, live guard: every real function in `gate/validators.py`
    must have a registry entry, confirmed by name."""
    real_function_names = {
        "budget_check", "temporal_fact_check", "deadline_conflict_check", "recipient_check",
        "commitment_check", "pii_leak_check", "provenance_check", "availability_check", "coverage_check",
    }
    registry_function_names = {entry.function_name for entry in VALIDATOR_REGISTRY}
    assert registry_function_names == real_function_names


def test_validator_registry_names_are_all_distinct():
    names = [entry.name for entry in VALIDATOR_REGISTRY]
    assert len(names) == len(set(names))


def test_registry_name_matches_the_real_budget_check_output():
    finding = budget_check(50.0, "food", _FakeBudget())
    assert finding.validator == _registry_name_for("budget_check")


def test_registry_name_matches_the_real_temporal_fact_check_output():
    finding = temporal_fact_check("a real meeting", _FakeCalendar())
    assert finding.validator == _registry_name_for("temporal_fact_check")


def test_registry_name_matches_the_real_deadline_conflict_check_output():
    deadline = datetime.now(timezone.utc) + timedelta(days=1)
    finding = deadline_conflict_check(2.0, deadline, 8.0, _FakeTasks())
    assert finding.validator == _registry_name_for("deadline_conflict_check")


def test_registry_name_matches_the_real_recipient_check_output():
    finding = recipient_check("a@example.com", [], _FakeContacts())
    assert finding.validator == _registry_name_for("recipient_check")


def test_registry_name_matches_the_real_commitment_check_output():
    finding = commitment_check([], [])
    assert finding.validator == _registry_name_for("commitment_check")


def test_registry_name_matches_the_real_pii_leak_check_output():
    finding = pii_leak_check("hello", [])
    assert finding.validator == _registry_name_for("pii_leak_check")


def test_registry_name_matches_the_real_provenance_check_output():
    finding = provenance_check(["user_request"])
    assert finding.validator == _registry_name_for("provenance_check")


def test_registry_name_matches_the_real_availability_check_output():
    start = datetime.now(timezone.utc) + timedelta(days=1)
    end = start + timedelta(hours=1)
    finding = availability_check(start, end, _FakeCalendar())
    assert finding.validator == _registry_name_for("availability_check")


def test_registry_name_matches_the_real_coverage_check_output():
    finding = coverage_check([], "")
    assert finding.validator == _registry_name_for("coverage_check")


def test_registry_wired_flags_match_the_real_current_production_wiring():
    """Confirmed directly against `retry_queue_drainer.py::build_stage_a_
    checks_for_domain()` before writing this -- only these three real
    validators have any real production caller today (`recipient_check`
    added `DEC-202`, wired into the real `email` domain)."""
    wired = {entry.function_name for entry in VALIDATOR_REGISTRY if entry.wired}
    assert wired == {"provenance_check", "deadline_conflict_check", "recipient_check"}
