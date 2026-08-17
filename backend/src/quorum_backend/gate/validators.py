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

import re
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


class TasksAdapter(Protocol):
    def get_committed_hours_before(self, deadline: datetime) -> float: ...


def deadline_conflict_check(
    claimed_commitment_hours: float | None,
    deadline: datetime | None,
    available_hours_before_deadline: float,
    tasks: TasksAdapter,
) -> Finding:
    """Real remaining-hours math against task-deadline ground truth.

    No claimed commitment (or no deadline) is verified_true — nothing was
    claimed, nothing to falsify, same reasoning as availability_check's
    "no proposed slot" case. Otherwise, the real already-committed hours
    before this deadline (from TasksAdapter, not just the newly-claimed
    amount alone) are added to what's newly claimed and compared against
    real available capacity — this is what makes it a genuine *conflict*
    check rather than a check of the new commitment in isolation.
    """
    if claimed_commitment_hours is None or deadline is None:
        return Finding(
            validator="DeadlineConflictCheck",
            claim="No deadline-relevant time commitment in proposal",
            evidence_state="verified_true",
            confidence=1.0,
        )

    already_committed = tasks.get_committed_hours_before(deadline)
    total_needed = already_committed + claimed_commitment_hours

    if total_needed <= available_hours_before_deadline:
        return Finding(
            validator="DeadlineConflictCheck",
            claim=f"{total_needed}h needed vs {available_hours_before_deadline}h available before {deadline}",
            evidence_state="verified_true",
            confidence=1.0,
        )
    return Finding(
        validator="DeadlineConflictCheck",
        claim=f"{total_needed}h needed exceeds {available_hours_before_deadline}h available before {deadline}",
        evidence_state="verified_false",
        confidence=1.0,
    )


class ContactsAdapter(Protocol):
    def is_known_contact(self, email: str) -> bool: ...


def recipient_check(
    recipient_email: str | None,
    thread_participants: list[str],
    contacts: ContactsAdapter,
    is_reply_all: bool = False,
) -> Finding:
    """Real thread/contact verification, plus the reply-all hazard flag.

    No recipient at all is genuinely unresolved (no_data_found, not
    verified_true) -- unlike a missing time slot or commitment, a missing
    recipient on an outbound action is itself worth flagging rather than
    silently treated as nothing-to-check.

    A recipient who is neither a thread participant nor a known contact is
    a real, structural red flag -- verified_false, hard-fail. A large
    reply-all is deliberately NOT a hard-fail (no_data_found instead) --
    see this session's report/DECISIONS_LOG for why.
    """
    if recipient_email is None:
        return Finding(
            validator="RecipientCheck",
            claim="No recipient in proposal",
            evidence_state="no_data_found",
            confidence=0.3,
        )

    in_thread = recipient_email in thread_participants
    known = contacts.is_known_contact(recipient_email)

    if not in_thread and not known:
        return Finding(
            validator="RecipientCheck",
            claim=f"{recipient_email} is neither in the thread nor a known contact",
            evidence_state="verified_false",
            confidence=1.0,
        )

    if is_reply_all and len(thread_participants) > 5:
        return Finding(
            validator="RecipientCheck",
            claim=f"Reply-all to {len(thread_participants)} participants — flagged, not blocked",
            evidence_state="no_data_found",
            confidence=0.5,
        )

    return Finding(
        validator="RecipientCheck",
        claim=f"{recipient_email} verified as {'thread participant' if in_thread else 'known contact'}",
        evidence_state="verified_true",
        confidence=1.0,
    )


def commitment_check(
    draft_commitments: list[str],
    user_stated_intent: list[str],
) -> Finding:
    """Real term-overlap check between draft commitments and stated user
    intent. Protects against a draft implying a promise the user never
    actually made -- a fabricated commitment, not merely a factual error,
    which is why an unbacked one is a hard verified_false, not deferred.
    """
    if not draft_commitments:
        return Finding(
            validator="CommitmentCheck",
            claim="No commitments in draft to check",
            evidence_state="verified_true",
            confidence=1.0,
        )

    unbacked = [
        c
        for c in draft_commitments
        if not any(_terms_overlap(c, intent) for intent in user_stated_intent)
    ]

    if not unbacked:
        return Finding(
            validator="CommitmentCheck",
            claim=f"All {len(draft_commitments)} commitment(s) backed by stated user intent",
            evidence_state="verified_true",
            confidence=1.0,
        )
    return Finding(
        validator="CommitmentCheck",
        claim=f"{len(unbacked)} commitment(s) with no basis in stated intent: {unbacked}",
        evidence_state="verified_false",
        confidence=0.9,
    )


def _terms_overlap(a: str, b: str, min_shared_terms: int = 2) -> bool:
    terms_a = set(re.findall(r"[a-z0-9]+", a.lower()))
    terms_b = set(re.findall(r"[a-z0-9]+", b.lower()))
    return len(terms_a & terms_b) >= min_shared_terms


def pii_leak_check(
    outbound_content: str,
    privacy_flagged_spans: list[str],
) -> Finding:
    """Real, exact-match check that Privacy-Gate-flagged spans never leave
    unredacted. Deliberately exact-match, not fuzzy: a false negative here
    is a real privacy leak; a false positive only costs one unnecessary
    Stage B judgment call -- the asymmetry in what each error type costs is
    why this validator is intentionally conservative rather than "smart."

    privacy_flagged_spans is a real input, never computed here -- PII
    detection is the Privacy Gate's job (MOBILE_03, not yet built in this
    repository), not re-implemented in this validator. See this session's
    report/DECISIONS_LOG for why detection and verification stay separate.
    """
    if not privacy_flagged_spans:
        return Finding(
            validator="PIILeakCheck",
            claim="No spans flagged by the Privacy Gate for this content",
            evidence_state="verified_true",
            confidence=1.0,
        )

    leaked = [span for span in privacy_flagged_spans if span in outbound_content]

    if not leaked:
        return Finding(
            validator="PIILeakCheck",
            claim=f"All {len(privacy_flagged_spans)} flagged span(s) absent from outbound content",
            evidence_state="verified_true",
            confidence=1.0,
        )
    return Finding(
        validator="PIILeakCheck",
        claim=f"{len(leaked)} flagged span(s) present, unredacted, in outbound content",
        evidence_state="verified_false",
        confidence=1.0,
    )


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
