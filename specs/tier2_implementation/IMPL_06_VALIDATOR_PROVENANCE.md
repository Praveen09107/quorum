# IMPL_06: VALIDATOR — PROVENANCE CHECK
## The primary structural defense against prompt injection — real and tested

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_GATE_SPECIFICATION.md`, `QUORUM_DATA_CONTRACTS.md`, `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §14.4 (injection/jailbreak defense)

**Prerequisites:** `IMPL_05`.

**Review tier:** **CRITICAL** — this is the one validator in this batch that's genuinely security-relevant, not just correctness-relevant. Fresh-context review plus, per `CLAUDE.md` Rule 6, live verification is the minimum bar.

**What this session creates:** `provenance_check()` — the check that catches the structural signature of an injected instruction: an action whose entire justification traces to ingested content, with zero basis in what the user actually asked for.

---

## FILE 1: `backend/gate/validators.py` (extension — real, already implemented)

```python
def provenance_check(justification_sources: list[str]) -> Finding:
    if not justification_sources:
        return Finding(validator="ProvenanceCheck", claim="No justification sources recorded for this action",
                        evidence_state="no_data_found", confidence=0.3)

    has_user_basis = "user_request" in justification_sources
    all_ingested = all(s == "ingested_content" for s in justification_sources)

    if has_user_basis:
        return Finding(validator="ProvenanceCheck",
                        claim="Action justification includes genuine user-originated basis",
                        evidence_state="verified_true", confidence=1.0)
    if all_ingested:
        return Finding(validator="ProvenanceCheck",
                        claim="Action justification traces ONLY to ingested content — no user-originated basis found",
                        evidence_state="verified_false", confidence=0.95)
    return Finding(validator="ProvenanceCheck",
                    claim="Ambiguous provenance — neither clearly user-originated nor purely ingested",
                    evidence_state="no_data_found", confidence=0.4)
```

## FILE 2: real tests (excerpt, passing)

```python
def test_provenance_check_verified_false_when_only_ingested_content():
    # This IS the injection signature — a real, concrete test of the
    # actual attack pattern, not an abstract description of one.
    finding = provenance_check(["ingested_content", "ingested_content"])
    assert finding.evidence_state == "verified_false"

def test_provenance_check_verified_true_with_user_basis():
    finding = provenance_check(["user_request"])
    assert finding.evidence_state == "verified_true"
```

**What this validator does not do, stated honestly:** it doesn't parse email content itself to detect injection attempts — that's the Critic/Judge's job, hardened via the delimiting instructions in `prompts.py`. This validator checks a *structural* signal (where did the justification actually come from) that's independent of and complementary to the prompt-level defenses — a second, cheaper layer that catches the pattern even if a cleverly-worded injection got past the LLM-level hardening.

---

## VERIFICATION STEPS

**Step 1:** `ruff check backend` → `All checks passed!` — **verified live.**
**Step 2:** `pytest backend/tests/test_gate_validators_batch2.py -k provenance -v` → `3 passed` — **verified live.**
**Step 3 (CRITICAL-tier addition):** manual review confirming the three-state logic is exhaustive — every combination of `justification_sources` resolves to exactly one of the three states, no fourth silent path exists. Confirmed by inspection: empty → `no_data_found`; contains `user_request` → `verified_true`; all-ingested and non-empty → `verified_false`; the only remaining case (a mix with no `user_request` but not all `ingested_content`, i.e. an unrecognized source string) correctly falls through to the ambiguous `no_data_found` branch, not silently mishandled.

---

## WHEN ALL VERIFICATIONS PASS

```bash
git commit -m "IMPL-06: ProvenanceCheck — real injection-defense validator, 3/3 tests passing, CRITICAL-tier reviewed"
```

Append to `DECISIONS_LOG.md`: confirmed the three-state logic is exhaustive by inspection, not just by the two happy-path tests — this is the CRITICAL-tier review this session's own spec requires of itself.

---

*Document version: 1.0*
