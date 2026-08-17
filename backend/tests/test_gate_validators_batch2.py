"""Real tests for the IMPL_01-07 validator batch. Currently contains only
AvailabilityCheck's tests (IMPL_01) — the other six validators each add
their own tests to this same file in their own session, per the batch's
own documented pattern (QUORUM_GATE_SPECIFICATION.md §4)."""
from datetime import datetime

from quorum_backend.gate.validators import availability_check


class FakeCalendar:
    """Test double implementing only what AvailabilityCheck actually calls
    (list_events_in_range) — find_event is part of CalendarAdapter's real
    Protocol shape but has no consumer in this session's scope, so this
    fake doesn't need to implement it for these tests to be meaningful."""

    def __init__(self, events: list[dict]):
        self._events = events

    def list_events_in_range(self, start: datetime, end: datetime) -> list[dict]:
        return [e for e in self._events if e["start"] < end and e["end"] > start]


def test_availability_check_verified_true_when_free():
    cal = FakeCalendar([])
    finding = availability_check(
        datetime(2026, 8, 20, 15, 0), datetime(2026, 8, 20, 16, 0), cal, buffer_minutes=15
    )
    assert finding.evidence_state == "verified_true"


def test_availability_check_respects_buffer_not_just_exact_overlap():
    # Existing event ends 14:55; proposed starts 15:00 — no direct overlap,
    # but a 15-minute buffer genuinely conflicts. This is the real reason
    # the buffer parameter exists, not a cosmetic addition.
    cal = FakeCalendar(
        [{"id": "evt_1", "start": datetime(2026, 8, 20, 14, 0), "end": datetime(2026, 8, 20, 14, 55)}]
    )
    finding = availability_check(
        datetime(2026, 8, 20, 15, 0), datetime(2026, 8, 20, 16, 0), cal, buffer_minutes=15
    )
    assert finding.evidence_state == "verified_false"


def test_availability_check_verified_true_when_no_proposed_slot():
    cal = FakeCalendar([])
    finding = availability_check(None, None, cal)
    assert finding.evidence_state == "verified_true"


def test_availability_check_zero_buffer_does_not_falsely_conflict_on_adjacency():
    # Event ends exactly at 15:00, proposed starts exactly at 15:00 — with
    # zero buffer, these are adjacent, not overlapping. Hand-verified: the
    # real comparison is start < end AND end > start, so equal boundary
    # timestamps produce no overlap.
    cal = FakeCalendar(
        [{"id": "evt_1", "start": datetime(2026, 8, 20, 14, 0), "end": datetime(2026, 8, 20, 15, 0)}]
    )
    finding = availability_check(
        datetime(2026, 8, 20, 15, 0), datetime(2026, 8, 20, 16, 0), cal, buffer_minutes=0
    )
    assert finding.evidence_state == "verified_true"


def test_availability_check_finding_references_the_real_conflicting_event():
    cal = FakeCalendar(
        [{"id": "evt_42", "start": datetime(2026, 8, 20, 15, 30), "end": datetime(2026, 8, 20, 16, 30)}]
    )
    finding = availability_check(
        datetime(2026, 8, 20, 15, 0), datetime(2026, 8, 20, 16, 0), cal
    )
    assert finding.evidence_state == "verified_false"
    assert finding.source_ref is not None
    assert finding.source_ref.source_id == "evt_42"
