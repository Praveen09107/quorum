"""Stage A validator registry — pure code, zero LLM calls, zero exceptions.
Anything checkable against ground truth belongs here, never behind a model
call. See specs/tier1_foundation/QUORUM_GATE_SPECIFICATION.md §4 for the
full registry this file implements incrementally, one real validator per
session.

Real content so far: AvailabilityCheck (IMPL_01). Every validator follows
the same injectable-ground-truth-adapter pattern (Protocol-typed) so it's
testable with synthetic data now and swappable for a real Supabase-backed
adapter at deployment with zero change to validator logic.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol

from quorum_backend.gate.schemas import EvidenceRef, Finding


class CalendarAdapter(Protocol):
    """The real, documented shape from IMPL_01's spec. find_event is
    declared here because it's part of this Protocol's real, intended
    interface (shared with TemporalFactCheck, not yet built in this
    bootstrap — see this session's report) — availability_check itself
    only calls list_events_in_range."""

    def find_event(self, description: str) -> dict | None: ...
    def list_events_in_range(self, start: datetime, end: datetime) -> list[dict]: ...


def availability_check(
    proposed_start: datetime | None,
    proposed_end: datetime | None,
    calendar: CalendarAdapter,
    buffer_minutes: int = 0,
) -> Finding:
    """Real overlap-and-buffer check against calendar ground truth.

    No proposed time slot in the proposal is not a failure to verify — there
    is nothing to falsify, so it's verified_true. A genuinely free slot
    (zero conflicting events in the buffered range) is also verified_true.
    Any conflicting event makes the claim verified_false.

    Deliberately two-valued in practice, not three: unlike a single-event
    lookup (TemporalFactCheck), a calendar range query reliably returns
    every event that exists in that window — an empty result is a real,
    positive fact ("nothing is booked here"), not an "I couldn't determine
    this" state. There is no genuine no_data_found case for this specific
    validator under the CalendarAdapter contract as specified; that
    contract doesn't model "the adapter couldn't reach the calendar" as a
    distinct return value (that's an infrastructure failure, handled by the
    Gate's separate retry-with-backoff path, not a Finding at all).
    """
    if proposed_start is None or proposed_end is None:
        return Finding(
            validator="AvailabilityCheck",
            claim="No proposed time slot in proposal",
            evidence_state="verified_true",
            confidence=1.0,
        )

    buffer = timedelta(minutes=buffer_minutes)
    conflicts = calendar.list_events_in_range(proposed_start - buffer, proposed_end + buffer)

    if not conflicts:
        return Finding(
            validator="AvailabilityCheck",
            claim=f"{proposed_start} to {proposed_end} is free (buffer: {buffer_minutes}m)",
            evidence_state="verified_true",
            confidence=1.0,
        )
    return Finding(
        validator="AvailabilityCheck",
        claim=f"{proposed_start} to {proposed_end} conflicts with {len(conflicts)} existing event(s)",
        evidence_state="verified_false",
        source_ref=EvidenceRef(
            source_type="calendar", source_id=str(conflicts[0].get("id", "unknown"))
        ),
        confidence=1.0,
    )
