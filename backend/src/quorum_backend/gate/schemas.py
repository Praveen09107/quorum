"""Gate core schemas — the real, canonical data contracts for every value
crossing a Gate-relevant boundary.

First real, runnable definition of these concepts. Every validator,
orchestration, and negotiation module built from this point on imports from
here directly — this file is the contract, not a description of one.

Authoritative source for the documented shape this implements:
specs/tier1_foundation/QUORUM_DATA_CONTRACTS.md §1.

Not yet present here: NegotiationOption — per QUORUM_DATA_CONTRACTS.md's own
history (DEC-018), that schema was added alongside Position/ImpactDelta only
once real negotiation work (IMPL_19) needed it. Adding it now, unused, would
be exactly the kind of invented-ahead-of-need architecture CLAUDE.md Rule 3
rules out.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Stakes(str, Enum):
    """S0-S3, per QUORUM_CONFIGURATION_CONSTANTS.md Sec 1's hardcoded stakes
    table -- a lookup, never a learned classifier. Built here, in this
    bootstrap, because IMPL_08's real orchestration signature needs it and
    no document in this project's real corpus ever gave Stakes a full,
    exact type definition (router.py, where get_stakes() actually lives,
    is IMPL_09 -- not yet built here). Uses the plain S0/S1/S2/S3 naming
    consistently used everywhere real in this corpus (this table,
    QUORUM_DATA_CONTRACTS.md's action_events.stakes CHECK constraint,
    QUORUM_GATE_SPECIFICATION.md Sec 2's state machine) -- not the
    differently-named member (S3_EXTERNAL_IRREVERSIBLE) a batch-guide
    document used for this session, which doesn't match anything in the
    real spec corpus.
    """

    S0 = "S0"
    S1 = "S1"
    S2 = "S2"
    S3 = "S3"


class ActionType(str, Enum):
    """Closed enum — every real action the system can propose. Adding a new
    member requires a corresponding row in QUORUM_CONFIGURATION_CONSTANTS.md
    §1's stakes table in the same change. No default exists for an unmapped
    action type — that's a bug, not an implicit S0."""

    SEND_EMAIL = "send_email"
    CREATE_CALENDAR_EVENT_EXTERNAL = "create_calendar_event_external"
    CREATE_CALENDAR_EVENT_LOCAL = "create_calendar_event_local"
    CREATE_TASK = "create_task"
    UPDATE_TASK = "update_task"
    LOG_EXPENSE = "log_expense"
    UPDATE_BUDGET = "update_budget"
    CREATE_NOTE = "create_note"
    UPDATE_APPLICATION_STATUS = "update_application_status"
    ARCHIVE_EMAIL = "archive_email"
    LABEL_EMAIL = "label_email"


class EvidenceRef(BaseModel):
    """A pointer to real data, never restated claim text. This is what makes
    a Finding falsifiable — anyone can re-fetch source_id and check the claim
    independently, rather than trusting a model's paraphrase of it."""

    source_type: Literal["calendar", "task", "budget", "email_thread", "contact_history"]
    source_id: str
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Finding(BaseModel):
    """The three-valued verification result — evidence_state is NEVER
    binary. Collapsing verified_false and no_data_found produces false
    rejections when ground truth is merely incomplete (an informal meeting
    never entered into a calendar). Collapsing no_data_found into a pass
    silently defeats verification. no_data_found is neither pass nor fail —
    an unresolved item that must reach Stage B for explicit judgment."""

    validator: str
    claim: str
    evidence_state: Literal["verified_true", "verified_false", "no_data_found"]
    source_ref: EvidenceRef | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class Objection(BaseModel):
    """One Critic output. The obligation-to-critique rule is enforced by
    shape, not just instruction: signed_off=True with a real, non-empty
    description is how a genuine 'Stage B reviewed and found nothing' is
    distinguished from a lazy empty response — an empty Objection list is
    never a valid Critic output on its own."""

    category: Literal["tone", "completeness", "safety", "commitment_wisdom", "factual"]
    severity: Literal["low", "medium", "high"]
    description: str
    evidence_ref: EvidenceRef | None = None
    suggested_fix: str | None = None
    signed_off: bool = False


class ContextSnapshot(BaseModel):
    """What informed a proposal's draft. Kept minimal and honest about what's
    actually real right now — extended by later sessions as real retrieval
    (thread summarization, note search) actually exists, not pre-populated
    with fields nothing yet produces."""

    thread_id: str | None = None
    retrieved_note_ids: list[str] = Field(default_factory=list)
    preference_weights_version: str | None = None


class ActionProposal(BaseModel):
    proposal_id: UUID = Field(default_factory=uuid4)
    action_type: ActionType
    payload: dict
    evidence: list[EvidenceRef] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    context_used: ContextSnapshot = Field(default_factory=ContextSnapshot)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GateVerdict(BaseModel):
    """revision_count is bounded [0,1] by the schema's own type — the
    one-content-revision-round rule is a type constraint the Gate's
    orchestration logic cannot accidentally violate, not application logic
    that could be forgotten in one code path."""

    decision: Literal["approve", "revise", "reject", "escalate_to_human"]
    revised_payload: dict | None = None
    findings: list[Finding] = Field(default_factory=list)
    objections: list[Objection] = Field(default_factory=list)
    trace_id: str
    revision_count: int = Field(ge=0, le=1, default=0)


class ResourceClaim(BaseModel):
    claim_type: Literal["time", "money", "effort"]
    amount: float
    unit: str


class Position(BaseModel):
    """One domain's real, evidence-backed stance in a negotiation.
    proposed_resolution is the field that turns synthesis from invention into
    merging — see QUORUM_GATE_SPECIFICATION.md §4 (referenced there; real
    negotiation logic itself is IMPL_18 onward, not part of this bootstrap)."""

    domain: Literal["calendar", "tasks", "finance"]
    concern: str
    severity_claim: str
    resource_claims: list[ResourceClaim] = Field(default_factory=list)
    proposed_resolution: str
    evidence: list[EvidenceRef] = Field(default_factory=list)


class ImpactDelta(BaseModel):
    """Every field here is code-computed — never produced by a model call.
    This is the literal implementation of 'the model narrates, the code
    computes,' the single most important honesty distinction in negotiation."""

    metric: Literal["deadline_slack_hours", "budget_remaining_fraction", "task_hours_committed"]
    before: float
    after: float
    direction: Literal["improves", "worsens", "unchanged"]
