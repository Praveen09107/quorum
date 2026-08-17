# IMPL_04: VALIDATOR — COMMITMENT CHECK
## Real term-overlap check between draft commitments and stated user intent

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_GATE_SPECIFICATION.md`, `QUORUM_DATA_CONTRACTS.md`

**Prerequisites:** `IMPL_03`.

**Review tier:** STANDARD.

**What this session creates:** `commitment_check()` and its helper `_terms_overlap()` — deliberately deterministic term-overlap, not semantic judgment, reusing the same tokenization spirit already proven in `search.py`.

**Out of scope:** extracting `draft_commitments` and `user_stated_intent` themselves — those are upstream extraction steps (LLM-assisted, cached), this validator only compares two already-extracted lists.

---

## FILE 1: `backend/gate/validators.py` (extension — real, already implemented)

```python
import re

def commitment_check(
    draft_commitments: list[str],
    user_stated_intent: list[str],
) -> Finding:
    if not draft_commitments:
        return Finding(validator="CommitmentCheck", claim="No commitments in draft to check",
                        evidence_state="verified_true", confidence=1.0)

    unbacked = [c for c in draft_commitments
                if not any(_terms_overlap(c, intent) for intent in user_stated_intent)]

    if not unbacked:
        return Finding(validator="CommitmentCheck",
                        claim=f"All {len(draft_commitments)} commitment(s) backed by stated user intent",
                        evidence_state="verified_true", confidence=1.0)
    return Finding(validator="CommitmentCheck",
                    claim=f"{len(unbacked)} commitment(s) with no basis in stated intent: {unbacked}",
                    evidence_state="verified_false", confidence=0.9)


def _terms_overlap(a: str, b: str, min_shared_terms: int = 2) -> bool:
    terms_a = set(re.findall(r"[a-z0-9]+", a.lower()))
    terms_b = set(re.findall(r"[a-z0-9]+", b.lower()))
    return len(terms_a & terms_b) >= min_shared_terms
```

## FILE 2: real tests (excerpt, passing)

```python
def test_commitment_check_verified_false_when_unbacked():
    finding = commitment_check(
        draft_commitments=["I will personally cover the flight costs"],
        user_stated_intent=["can you reply to Priya about Thursday"],
    )
    assert finding.evidence_state == "verified_false"
```

**Why this matters concretely:** this is the exact failure mode named all the way back in the original Gate design — a draft that implies a financial commitment the user never actually made. This test proves the validator genuinely catches it, not just that it returns a Finding.

---

## VERIFICATION STEPS

**Step 1:** `ruff check backend` → `All checks passed!` — **verified live.**
**Step 2:** `pytest backend/tests/test_gate_validators_batch2.py -k commitment -v` → `2 passed` — **verified live.**

---

## WHEN ALL VERIFICATIONS PASS

```bash
git commit -m "IMPL-04: CommitmentCheck — real term-overlap validator, 2/2 tests passing"
```

---

*Document version: 1.0*
