"""Real tests for gate/schemas.py's schema-level guarantees — specifically
the constraints QUORUM_DATA_CONTRACTS.md §1 states are enforced by the
schema itself, not application logic. Each of these must actually fail to
construct, not just be documented as invalid."""
import pytest
from pydantic import ValidationError

from quorum_backend.gate.schemas import (
    ActionProposal,
    ActionType,
    EvidenceRef,
    Finding,
    GateVerdict,
)


def test_finding_confidence_out_of_range_rejected():
    with pytest.raises(ValidationError):
        Finding(
            validator="TemporalFactCheck",
            claim="test claim",
            evidence_state="verified_true",
            confidence=1.5,
        )


def test_finding_negative_confidence_rejected():
    with pytest.raises(ValidationError):
        Finding(
            validator="TemporalFactCheck",
            claim="test claim",
            evidence_state="verified_true",
            confidence=-0.1,
        )


def test_finding_invalid_evidence_state_rejected():
    with pytest.raises(ValidationError):
        Finding(
            validator="TemporalFactCheck",
            claim="test claim",
            evidence_state="maybe",  # not one of the three real values
            confidence=0.9,
        )


def test_finding_accepts_valid_no_data_found_state_with_no_source_ref():
    # no_data_found is a real, legitimate state — must construct cleanly
    # without a source_ref, since there is by definition no evidence to
    # point to when nothing was found.
    finding = Finding(
        validator="TemporalFactCheck",
        claim="Was a meeting with Priya ever entered on the calendar",
        evidence_state="no_data_found",
        confidence=0.4,
    )
    assert finding.evidence_state == "no_data_found"
    assert finding.source_ref is None


def test_gate_verdict_revision_count_out_of_bound_rejected():
    with pytest.raises(ValidationError):
        GateVerdict(
            decision="revise",
            trace_id="trace-123",
            revision_count=2,  # bound is [0,1] — this must be rejected
        )


def test_gate_verdict_revision_count_negative_rejected():
    with pytest.raises(ValidationError):
        GateVerdict(
            decision="approve",
            trace_id="trace-123",
            revision_count=-1,
        )


def test_action_proposal_defaults_are_real_not_placeholder():
    proposal = ActionProposal(
        action_type=ActionType.LOG_EXPENSE,
        payload={"amount": 450.0, "category": "groceries"},
    )
    # proposal_id is a real, auto-generated UUID — not empty, not a fixed stub
    assert proposal.proposal_id is not None
    assert str(proposal.proposal_id) != ""
    assert proposal.evidence == []
    assert proposal.assumptions == []
    assert proposal.created_at is not None


def test_evidence_ref_rejects_unrecognized_source_type():
    with pytest.raises(ValidationError):
        EvidenceRef(source_type="social_media", source_id="evt_1")
