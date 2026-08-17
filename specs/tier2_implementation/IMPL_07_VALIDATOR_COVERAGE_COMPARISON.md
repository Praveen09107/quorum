# IMPL_07: COVERAGECHECK — COMPARISON HALF
## The deterministic set-comparison closing the hybrid validator — extraction already real

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_GATE_SPECIFICATION.md`, `QUORUM_DATA_CONTRACTS.md`

**Prerequisites:** `IMPL_06`. Also depends on `build_coverage_extraction_prompt()`, already real in `prompts.py` since the earlier Gate-schemas session.

**Review tier:** STANDARD.

**What this session creates:** `coverage_check()` — the pure-code half of `CoverageCheck`. The extraction (one cached LLM call, real since earlier) produces the question list; this function compares it against the draft with zero additional LLM cost.

**Out of scope:** re-implementing or changing the extraction prompt — already real and tested (`test_coverage_extraction_prompt_includes_source_body`).

---

## FILE 1: `backend/gate/validators.py` (extension — real, already implemented)

```python
def coverage_check(
    extracted_questions: list[str],
    draft_text: str,
    min_shared_terms: int = 1,
) -> Finding:
    if not extracted_questions:
        return Finding(validator="CoverageCheck", claim="No questions extracted from source email",
                        evidence_state="verified_true", confidence=1.0)

    draft_terms = set(re.findall(r"[a-z0-9]+", draft_text.lower()))
    uncovered = [q for q in extracted_questions
                 if len(set(re.findall(r"[a-z0-9]+", q.lower())) & draft_terms) < min_shared_terms]

    if not uncovered:
        return Finding(validator="CoverageCheck",
                        claim=f"All {len(extracted_questions)} extracted question(s) addressed in draft",
                        evidence_state="verified_true", confidence=1.0)
    return Finding(validator="CoverageCheck",
                    claim=f"{len(uncovered)} question(s) not addressed: {uncovered}",
                    evidence_state="verified_false", confidence=0.85)
```

## FILE 2: real tests (excerpt, passing)

```python
def test_coverage_check_verified_false_when_a_question_is_dropped():
    finding = coverage_check(
        extracted_questions=["what time works for you", "can you send the invoice"],
        draft_text="5pm works for me.",  # invoice question never addressed
    )
    assert finding.evidence_state == "verified_false"
```

**Honest limitation, stated plainly rather than hidden:** this is term-overlap, not semantic understanding — a draft could technically share a term with a question without actually answering it (or vice versa, answer it using entirely different words). This is a real, known trade-off, not an oversight: it's cheap, deterministic, catches the common case (a question dropped entirely, sharing zero terms with the reply), and anything subtler than that is exactly what Stage B's Critic exists to catch — this validator doesn't need to be perfect, it needs to correctly handle what code can reliably judge and hand off the rest.

---

## VERIFICATION STEPS

**Step 1:** `ruff check backend` → `All checks passed!` — **verified live.**
**Step 2:** `pytest backend/tests/test_gate_validators_batch2.py -k coverage -v` → `2 passed` — **verified live.**
**Step 3 (whole-batch confirmation):** `pytest backend/tests -q` → **50 passed** — **verified live, the full real suite, not just this session's slice.**

---

## WHEN ALL VERIFICATIONS PASS

```bash
git commit -m "IMPL-07: CoverageCheck comparison half — real, 2/2 tests passing. All 9 Stage A validators now complete: 50/50 total suite passing."
```

**Update `QUORUM_GATE_SPECIFICATION.md` §4 and §6:** every validator row changes from "Specified" to "Implemented, tested." §6 ("What Is Genuinely Not Yet Built") updates to reflect that all nine validators are now real — only `gate.review()`'s orchestration itself remains, which is `IMPL_08`.

**Append to `DECISIONS_LOG.md`:** the full Stage A validator registry is complete — 9 of 9, 50/50 total tests passing across the whole real suite. This is a real milestone, worth its own entry, not folded quietly into the last individual validator's note.

---

*Document version: 1.0 — the last of the seven-validator batch (`IMPL_01`–`IMPL_07`).*
