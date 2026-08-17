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


class BudgetAdapter(Protocol):
    def get_remaining_budget(self, category: str) -> float: ...


def budget_check(
    claimed_amount: float | None,
    category: str,
    budget: BudgetAdapter,
) -> Finding:
    """Real check against finance ground truth.

    HONEST DISCLOSURE: unlike every validator built in the numbered
    IMPL_01-07 sessions, no document in this project's real specification
    corpus reproduces this function's full body -- only its interface
    signature (QUORUM_GATE_SPECIFICATION.md Sec 4's validator registry
    table: budget_check(claimed_amount: float | None, category: str,
    budget: BudgetAdapter) -> Finding). This implementation is a real,
    reasoned construction following the exact same pattern every other
    adapter-backed validator in this file already uses (no claim ->
    verified_true; compare the claim against a real adapter-queried value;
    exceed -> verified_false) -- not a copy of a given spec, because none
    exists to copy. Flagged explicitly rather than presented as if it were.
    """
    if claimed_amount is None:
        return Finding(
            validator="BudgetCheck",
            claim="No claimed amount in proposal",
            evidence_state="verified_true",
            confidence=1.0,
        )

    remaining = budget.get_remaining_budget(category)
    if claimed_amount <= remaining:
        return Finding(
            validator="BudgetCheck",
            claim=f"{claimed_amount} within {remaining} remaining budget for {category}",
            evidence_state="verified_true",
            confidence=1.0,
        )
    return Finding(
        validator="BudgetCheck",
        claim=f"{claimed_amount} exceeds {remaining} remaining budget for {category}",
        evidence_state="verified_false",
        confidence=1.0,
    )


class CalendarAdapter(Protocol):
    """The real, documented shape from IMPL_01's spec — find_event is used
    by temporal_fact_check, list_events_in_range by availability_check."""

    def find_event(self, description: str) -> dict | None: ...
    def list_events_in_range(self, start: datetime, end: datetime) -> list[dict]: ...


def temporal_fact_check(
    claimed_meeting: str | None,
    calendar: CalendarAdapter,
) -> Finding:
    """The worked example from QUORUM_GATE_SPECIFICATION.md Sec 4.1,
    reproduced as real code -- the single most important behavioral
    guarantee in the whole Gate: absence of a calendar entry is NOT proof
    a meeting never happened (it could be real but never entered), so a
    failed lookup is no_data_found, never verified_false. Collapsing that
    distinction was identified in this project's own design history as a
    real correctness risk this exact function exists to prevent.
    """
    if claimed_meeting is None:
        return Finding(
            validator="TemporalFactCheck",
            claim="No specific meeting claimed in proposal",
            evidence_state="verified_true",
            confidence=1.0,
        )

    event = calendar.find_event(claimed_meeting)
    if event is not None:
        return Finding(
            validator="TemporalFactCheck",
            claim=f"Meeting '{claimed_meeting}' confirmed on calendar",
            evidence_state="verified_true",
            source_ref=EvidenceRef(source_type="calendar", source_id=str(event.get("id", "unknown"))),
            confidence=1.0,
        )

    return Finding(
        validator="TemporalFactCheck",
        claim=f"No calendar entry found for '{claimed_meeting}' — absence is not proof it never happened",
        evidence_state="no_data_found",
        confidence=0.4,
    )


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


def provenance_check(justification_sources: list[str]) -> Finding:
    """CRITICAL TIER — the primary structural defense against prompt
    injection in this system.

    The defense is structural, not content-based: this function never
    inspects what any source actually says. justification_sources is a
    closed-vocabulary list of provenance labels ("user_request" /
    "ingested_content") recorded by trusted agent code before this
    validator ever runs -- untrusted content the system merely read has no
    path to change what label gets recorded for it. This is deliberately
    the opposite of keyword/content filtering, which is a losing arms race
    against adversarial phrasing; matching on WHERE a justification
    structurally originated is not defeated by HOW persuasively injected
    content is worded.

    Exhaustive over exactly four real cases, no fifth silent path:
      1. Empty list -> no_data_found (nothing recorded to judge at all).
      2. Contains "user_request" (regardless of anything else present)
         -> verified_true. A genuine user basis is sufficient on its own.
      3. Non-empty, no "user_request", every entry is exactly
         "ingested_content" -> verified_false. This IS the injection
         signature: an action justified only by things the system read,
         never by anything the user actually asked for.
      4. Non-empty, no "user_request", not all "ingested_content" (an
         unrecognized source string, alone or mixed in) -> no_data_found.
         Genuinely ambiguous provenance is not silently resolved either
         direction.
    """
    if not justification_sources:
        return Finding(
            validator="ProvenanceCheck",
            claim="No justification sources recorded for this action",
            evidence_state="no_data_found",
            confidence=0.3,
        )

    has_user_basis = "user_request" in justification_sources
    all_ingested = all(s == "ingested_content" for s in justification_sources)

    if has_user_basis:
        return Finding(
            validator="ProvenanceCheck",
            claim="Action justification includes genuine user-originated basis",
            evidence_state="verified_true",
            confidence=1.0,
        )
    if all_ingested:
        return Finding(
            validator="ProvenanceCheck",
            claim="Action justification traces ONLY to ingested content — no user-originated basis found",
            evidence_state="verified_false",
            confidence=0.95,
        )
    return Finding(
        validator="ProvenanceCheck",
        claim="Ambiguous provenance — neither clearly user-originated nor purely ingested",
        evidence_state="no_data_found",
        confidence=0.4,
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


def coverage_check(
    extracted_questions: list[str],
    draft_text: str,
    min_shared_terms: int = 1,
) -> Finding:
    """The deterministic set-comparison half of the hybrid CoverageCheck --
    extraction (prompts.build_coverage_extraction_prompt, a real, separate
    LLM call) produces extracted_questions; this function compares it
    against a draft with zero additional LLM cost.

    Catches a specific, real failure mode: a source email asks several
    distinct questions, and a draft reply silently answers only some of
    them. "Coverage," not "completeness" -- this is a mechanical set
    comparison, not a judgment call (completeness is a real Objection
    category the Critic weighs at Stage B; this is Stage A).

    HONEST, DOCUMENTED LIMITATION, verified live this session, not just
    described abstractly: this is term-overlap, not semantic understanding,
    and the regex (re.findall(r"[a-z0-9]+", ...)) does zero stopword
    filtering. At the real default min_shared_terms=1, a single SHARED
    STOPWORD (e.g. "the") between a question and the draft is enough to
    mark that question "covered" even when the draft doesn't address it at
    all -- confirmed reproducible: coverage_check(["Can you also send the
    quarterly budget report?"], "The meeting works at 3pm.") returns
    verified_true, because "the" is the only shared term and 1 >= 1. This
    is not a new finding -- it's the same trade-off the real IMPL_07 spec
    already names and deliberately accepts ("a real, known trade-off, not
    an oversight... anything subtler than [a fully dropped question] is
    exactly what Stage B's Critic exists to catch") -- restated here more
    precisely, naming the exact stopword mechanism, since the original
    spec's caveat didn't spell out that specific case. min_shared_terms is
    NOT changed and no stopword filtering is added here without an explicit
    decision to do so -- deviating from the real, documented spec
    unprompted would itself be a Rule 3 violation.
    """
    if not extracted_questions:
        return Finding(
            validator="CoverageCheck",
            claim="No questions extracted from source email",
            evidence_state="verified_true",
            confidence=1.0,
        )

    draft_terms = set(re.findall(r"[a-z0-9]+", draft_text.lower()))
    uncovered = [
        q
        for q in extracted_questions
        if len(set(re.findall(r"[a-z0-9]+", q.lower())) & draft_terms) < min_shared_terms
    ]

    if not uncovered:
        return Finding(
            validator="CoverageCheck",
            claim=f"All {len(extracted_questions)} extracted question(s) addressed in draft",
            evidence_state="verified_true",
            confidence=1.0,
        )
    return Finding(
        validator="CoverageCheck",
        claim=f"{len(uncovered)} question(s) not addressed: {uncovered}",
        evidence_state="verified_false",
        confidence=0.85,
    )
