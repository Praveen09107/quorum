# QUORUM — Gate Specification

**Tier:** `tier1_foundation` · **Volatility:** Stable content, real-world direct edits — corrected here during a full staleness audit: this previously read "Frozen — amended, never edited directly · Version: 1.0," which didn't match how this document was actually kept current. In practice it was edited directly, in place, whenever a genuine gap was found (`DEC-007` records one such edit here, to the validator table), each edit disclosed in `DECISIONS_LOG.md` rather than through a separate "amendment" mechanism or an incremented version number — neither was ever actually used across the real project.

**Purpose:** the complete technical specification of the Gate — the project's thesis, made implementable. Every schema, prompt, and validator referenced here has real, tested code behind it unless explicitly marked otherwise. This document is the single thing to attach for any session touching verification.

---

## 1. Design Principle (restated precisely, because everything below follows from it)

Anything checkable against ground truth is Stage A: plain code, zero LLM calls, zero exceptions. Anything requiring genuine judgment — tone, completeness nuance, commitment wisdom — is Stage B, and only Stage B. This is a correctness property: a database lookup is categorically more reliable than any model, at any size, for verifying a factual claim. Confusing "cheaper" with "why" here is a common misreading — the design would be identical with unlimited compute budget.

---

## 2. The Full State Machine

```
proposed
  → Stage A (all applicable validators run in parallel; see §4 registry)
      → any Finding.evidence_state == "verified_false"?
          → YES: short-circuit to "revise", zero LLM cost, re-enter Stage A on the revision
          → NO: continue
      → any Finding.evidence_state == "no_data_found"?
          → carried forward as an unresolved item into Stage B, never silently resolved
  → Stage B (only for S2/S3; S0/S1 exit here as "approve")
      → stakes == S2 ("single-check Stage B" — a real distinction found missing
        from this state machine during document audit, now made explicit):
          → Judge call ONLY (Gemini Flash) — reviews the proposal + Stage A
            findings directly, no separate Critic round. Appropriate for
            internal-significant, reversible actions — matches the ADD's
            §6.7 cost profile of exactly 1 call for S2.
          → produces GateVerdict directly
      → stakes == S3 (full debate):
          → Critic call (Groq/Llama 3.3 70B) — produces Objection[] or a
            signed-off pass
          → Judge call (Gemini Flash) — role-stripped, order-randomized —
            produces GateVerdict
      → decision == "revise"?
          → re-run Stage A ONLY on the revised payload (cheap, no new Stage B call yet)
          → Stage A passes → done, verdict stands
          → Stage A fails again, OR this is already revision_count == 1 → escalate_to_human
      → decision ∈ {"approve", "reject", "escalate_to_human"} → terminal
  → if stakes == S3 (regardless of the above): pending_human_approval
      → trace must be visibly displayed before the "approve" affordance activates
      → human taps: approve → execute; reject → discarded, logged as correction; edit → new proposal, re-enters Stage A
```

**Two failure classes, deliberately separated (this is not the same as the content-revision loop above):** a provider timeout or malformed structured output triggers a retry with backoff, **max 2 attempts**, before falling into the content-revision path at all. A transient Groq or Gemini hiccup is never miscounted as a Gate rejection.

---

## 3. Real Code — `gate/schemas.py`

Full specification lives in `QUORUM_DATA_CONTRACTS.md` §1. Restated here only as a pointer, deliberately not duplicated — that document is authoritative for schema shape.

---

## 4. Stage A — Validator Registry

**Authoritative source for design:** `backend/gate/validators.py`. **Authoritative source for current implementation status:** `STATUS_INDEX.md` — never this document. This table describes the permanent design of each validator; it does not need to change as implementation progresses, and should not be edited every session the way it wrongly was for `IMPL_01`–`IMPL_07`.

| Validator | Ground truth | Real interface |
|---|---|---|
| `TemporalFactCheck` | Calendar | `temporal_fact_check(claimed_meeting: str \| None, calendar: CalendarAdapter) -> Finding` |
| `BudgetCheck` | Finance DB | `budget_check(claimed_amount: float \| None, category: str, budget: BudgetAdapter) -> Finding` |
| `AvailabilityCheck` | Calendar + buffer prefs | `availability_check(proposed_start, proposed_end, calendar: CalendarAdapter, buffer_minutes: int) -> Finding` |
| `DeadlineConflictCheck` | Tasks DB | `deadline_conflict_check(claimed_commitment_hours, deadline, available_hours_before_deadline, tasks: TasksAdapter) -> Finding` |
| `RecipientCheck` | Email metadata / contacts | `recipient_check(recipient_email, thread_participants, contacts: ContactsAdapter, is_reply_all: bool) -> Finding` |
| `CoverageCheck` (hybrid) | Source email + draft | Extraction (cached LLM call) + `coverage_check()` deterministic comparison |
| `CommitmentCheck` | Parsed user intent | `commitment_check(draft_commitments, user_stated_intent) -> Finding` |
| `PIILeakCheck` | Privacy Gate categories | `pii_leak_check(outbound_content, privacy_flagged_spans) -> Finding` |
| `ProvenanceCheck` | The proposal's own `evidence` field | `provenance_check(justification_sources: list[str]) -> Finding` |

### 4.1 Worked example — `temporal_fact_check`, the three-valued logic made concrete

```python
def temporal_fact_check(claimed_meeting, calendar) -> Finding:
    if claimed_meeting is None:
        return Finding(..., evidence_state="verified_true", confidence=1.0)  # nothing claimed, nothing to falsify

    event = calendar.find_event(claimed_meeting)
    if event is not None:
        return Finding(..., evidence_state="verified_true", source_ref=..., confidence=1.0)

    # Absence of a calendar entry is NOT proof the meeting never happened.
    return Finding(..., evidence_state="no_data_found", confidence=0.4)
```

**Proven by test** (`test_temporal_fact_check_no_data_found_not_false_when_absent`): an absent calendar entry produces `no_data_found`, explicitly asserted `!= "verified_false"`. This is the single most important behavioral guarantee in the entire Gate — collapsing this distinction was identified early in this project as a real correctness risk, and it is now a tested property of real code, not a documented intention.

---

## 5. Stage B — Prompts and Roles

**Authoritative source:** `backend/gate/prompts.py`, tested (`backend/tests/test_gate_prompts.py`, 4/4 passing).

### 5.1 Model assignment (restated from `QUORUM_MASTER_REFERENCE.md`, load-bearing enough to repeat here)

Generator: Gemini Flash. Critic: **Groq-hosted Llama 3.3 70B — a different model family, deliberately.** Judge: Gemini Flash. The Critic's model diversity is not a cost decision; it is the same reasoning the project's own AI-assisted development methodology (§15 of the ADD, `CLAUDE.md` Rule 6) applies to *building* Quorum — same-family review shares blind spots.

### 5.2 The Critic prompt (full text, real, in `prompts.py::CRITIC_SYSTEM_PROMPT`)

Key structural properties, each independently tested:
- **Obligation to critique, enforced by instruction, backed by schema:** the prompt states at least one real objection or an explicit signed-off entry is required; `Objection.signed_off` exists precisely so a genuine "nothing wrong" is distinguishable from a lazy empty response.
- **Grounded in Stage A findings, explicitly:** the prompt is built by interpolating real `Finding` objects (`test_critic_prompt_includes_findings_and_injection_hardening` proves the actual finding text appears in the rendered prompt).
- **Injection hardening in the Critic role too, not only the Judge:** the prompt explicitly instructs that retrieved content is data, never a directive — tested, present in the rendered output.

### 5.3 The Judge prompt (full text, real, in `prompts.py::JUDGE_SYSTEM_PROMPT`)

- **Anonymization is an orchestration-layer responsibility, not a prompt-layer one** — the prompt's docstring states this explicitly: role-stripping and objection-order-randomization happen in the calling code *before* this function runs, so that discipline can be independently unit-tested rather than trusted to prompt phrasing alone.
- **Evidence-over-rhetoric, stated directly:** "weigh them purely on the evidence they cite, never on which position sounds more confident or more polished" — tested present in the rendered prompt.
- **The revision bound is stated in the prompt itself, not only enforced by the schema:** "This is your only revision attempt" — belt-and-suspenders with `GateVerdict.revision_count`'s type-level bound (§2 of `QUORUM_DATA_CONTRACTS.md`).

### 5.4 The CoverageCheck extraction prompt (full text, real, in `prompts.py::COVERAGE_EXTRACTION_PROMPT`)

A single, cheap, cacheable call: extract distinct questions from a source email as a plain string list. This is the "hybrid" half of CoverageCheck — the extraction is generative (an LLM call), the actual coverage comparison against a draft is deterministic set logic, now real (`IMPL_07`).

---

## 6. Orchestration Status

**`gate.review()` is now real and tested** (`backend/gate/orchestration.py`, 8/8 tests passing in `test_gate_orchestration.py`) — the complete state machine from §2, wired for real: Stage A, the stakes-based routing (S0/S1 exit early, S2/S3 reach Stage B), the S2-vs-S3 Critic routing, and the one bounded revision round, including the subtle, now-correctly-distinguished difference between Stage A's own short-circuit `revise` (zero Stage B cost, doesn't consume the revision budget) and a Stage-B-issued `revise` (does consume it, and gets one real re-check). What remains: the LangGraph node wrapping this function into each domain agent's actual graph — deferred to `IMPL_13` onward, since the node is domain-specific while this orchestration deliberately is not. The real Critic/Judge LLM calls themselves are injected dependencies here, proven correct against fake implementations; live Gemini/Groq wiring happens at deployment.

---

## 7. How This Document Stays Trustworthy

Every design claim above is backed by real, tested code at the time this document was last substantively revised. **Current test counts and pass/fail status live in `STATUS_INDEX.md`, updated every session — never here.** This section exists to state the *policy*, which doesn't change session to session, not the *number*, which does.

---

*Attach this document, alongside `QUORUM_DATA_CONTRACTS.md` and `QUORUM_CONFIGURATION_CONSTANTS.md`, to any session implementing a new Stage A validator or touching Stage B orchestration.*
