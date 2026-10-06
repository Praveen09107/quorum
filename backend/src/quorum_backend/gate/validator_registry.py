"""The real Stage A validator roster (`DEC-193`, product rebuild Block
E) -- backs `GET /gate/validators`, the data behind the "how it works"
half of the Gate showcase page.

WHY THIS EXISTS: a direct item in the product owner's own 11-point
mandate for this rebuild -- "I want to showcase how the backend
workflow, how the gate checks and validates in a separate page, so
that judges will understand it is real working." Every number this
route returns must come from live data, never hardcoded marketing
copy describing a system that doesn't exist. This file is the one,
real exception to that rule, and it is a DELIBERATE one: `VALIDATOR_
REGISTRY` below is real, hand-maintained metadata (a name, a one-line
description of what each validator checks), because the alternative --
parsing each validator's own long, narrative docstring at runtime to
extract a user-facing description -- would be fragile and would
produce worse copy than a human can write, for no real synchronization
benefit. **The synchronization guarantee is a test, not runtime
reflection:** `test_validator_registry.py` calls every real validator
with representative inputs and asserts each registry entry's `name`
genuinely matches the real `Finding.validator` string that function
produces. If a validator's own real name ever changes and this
registry isn't updated, that test fails -- the same "a test is the
sync mechanism" discipline this project already uses elsewhere (e.g.
`agent_telemetry.py`'s own exhaustiveness test against the real
`ActionType` enum).

`wired` is the one field that is NOT narrative -- it reflects the real,
current, confirmed fact (checked directly against `retry_queue_
drainer.py::build_stage_a_checks_for_domain()` before writing this)
that only `provenance_check`, `deadline_conflict_check`, and (`DEC-202`)
`recipient_check` have any real production caller today. This is itself
part of the showcase's own honesty: a judge should see which checks are
live right now, not be led to believe all nine run on every real
action.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidatorInfo:
    """One real Stage A validator's own real identity and real,
    current production status."""

    # Matches the real `Finding.validator` string this function
    # produces -- the real join key between this roster and any real,
    # live `Finding` a client has already seen.
    name: str

    # The real, live Python function name -- `gate/validators.py::name`
    # -- useful for a judge reading the real source alongside this page.
    function_name: str

    description: str
    evidence_source: str
    wired: bool


VALIDATOR_REGISTRY: tuple[ValidatorInfo, ...] = (
    ValidatorInfo(
        name="ProvenanceCheck",
        function_name="provenance_check",
        description="Confirms a proposed action's justification genuinely traces back to the user's own request, never a fabricated basis.",
        evidence_source="The proposal's own recorded justification sources (e.g. a real user-typed request, a real negotiation choice).",
        wired=True,
    ),
    ValidatorInfo(
        name="DeadlineConflictCheck",
        function_name="deadline_conflict_check",
        description="Confirms a claimed task commitment genuinely fits in the real hours available before its real deadline, against the user's own already-committed hours.",
        evidence_source="A real, live query of the user's other open tasks due before the same deadline.",
        wired=True,
    ),
    ValidatorInfo(
        name="RecipientCheck",
        function_name="recipient_check",
        description="Confirms an email's resolved recipient is a real, known contact, never an unverified address the model invented.",
        evidence_source="The user's own real sent-message history (who they have genuinely emailed before).",
        wired=True,
    ),
    ValidatorInfo(
        name="PIILeakCheck",
        function_name="pii_leak_check",
        description="Scans a drafted message for real personal information that was never part of what the user actually asked to share.",
        evidence_source="Pattern-matching against the user's own original request text.",
        wired=False,
    ),
    ValidatorInfo(
        name="CommitmentCheck",
        function_name="commitment_check",
        description="Confirms a claimed commitment (e.g. an estimated duration) is consistent with how the user has described similar real work before.",
        evidence_source="The user's own real task history for similar, already-recorded commitments.",
        wired=False,
    ),
    ValidatorInfo(
        name="AvailabilityCheck",
        function_name="availability_check",
        description="Confirms a proposed meeting time genuinely doesn't collide with a real event already on the calendar.",
        evidence_source="A real calendar query for the proposed time window.",
        wired=False,
    ),
    ValidatorInfo(
        name="BudgetCheck",
        function_name="budget_check",
        description="Confirms a claimed expense or budget change genuinely fits within the user's own real, current monthly budget ceiling.",
        evidence_source="The user's own real, live monthly budget limit and month-to-date spend.",
        wired=False,
    ),
    ValidatorInfo(
        name="TemporalFactCheck",
        function_name="temporal_fact_check",
        description="Confirms a referenced real-world event (e.g. 'the meeting we had Tuesday') genuinely exists on the calendar before a proposal is allowed to rely on it.",
        evidence_source="A real calendar lookup for the referenced event.",
        wired=False,
    ),
    ValidatorInfo(
        name="CoverageCheck",
        function_name="coverage_check",
        description="Confirms every claim a proposal makes was actually checked by at least one real validator above -- the Gate's own check on itself.",
        evidence_source="The real set of Finding objects Stage A already produced for this proposal.",
        wired=False,
    ),
)
