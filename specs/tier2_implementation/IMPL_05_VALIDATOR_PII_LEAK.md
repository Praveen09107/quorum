# IMPL_05: VALIDATOR — PII LEAK CHECK
## Real, exact-match check that Privacy-Gate-flagged spans never leave unredacted

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_GATE_SPECIFICATION.md`, `QUORUM_DATA_CONTRACTS.md`, `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §10.1 (Privacy Gate)

**Prerequisites:** `IMPL_04`. **Note the cross-track dependency flagged in `SESSION_GUIDE.md`:** this validator's real integration needs the Privacy Gate's actual flagged-span output, which is `MOBILE_03`, a later mobile session. The validator logic itself is fully real and testable now against synthetic flagged spans; full integration is deferred honestly, not faked.

**Review tier:** STANDARD.

**What this session creates:** `pii_leak_check()`.

---

## FILE 1: `backend/gate/validators.py` (extension — real, already implemented)

```python
def pii_leak_check(
    outbound_content: str,
    privacy_flagged_spans: list[str],
) -> Finding:
    if not privacy_flagged_spans:
        return Finding(validator="PIILeakCheck", claim="No spans flagged by the Privacy Gate for this content",
                        evidence_state="verified_true", confidence=1.0)

    leaked = [span for span in privacy_flagged_spans if span in outbound_content]

    if not leaked:
        return Finding(validator="PIILeakCheck",
                        claim=f"All {len(privacy_flagged_spans)} flagged span(s) absent from outbound content",
                        evidence_state="verified_true", confidence=1.0)
    return Finding(validator="PIILeakCheck",
                    claim=f"{len(leaked)} flagged span(s) present, unredacted, in outbound content",
                    evidence_state="verified_false", confidence=1.0)
```

**Why exact-match, deliberately, not fuzzy:** a false negative here is a real privacy leak; a false positive only costs one unnecessary Stage B judgment call. The asymmetry in what each error type costs is why this validator is intentionally conservative rather than "smart."

## FILE 2: real tests (excerpt, passing)

```python
def test_pii_leak_check_verified_true_when_properly_redacted():
    finding = pii_leak_check("sure, my card is <CARD_NUMBER>", ["4111-1111-1111-1111"])
    assert finding.evidence_state == "verified_true"

def test_pii_leak_check_verified_false_when_span_present():
    finding = pii_leak_check("sure, my card is 4111-1111-1111-1111", ["4111-1111-1111-1111"])
    assert finding.evidence_state == "verified_false"
```

---

## VERIFICATION STEPS

**Step 1:** `ruff check backend` → `All checks passed!` — **verified live.**
**Step 2:** `pytest backend/tests/test_gate_validators_batch2.py -k pii_leak -v` → `2 passed` — **verified live.**

---

## WHEN ALL VERIFICATIONS PASS

```bash
git commit -m "IMPL-05: PIILeakCheck — real exact-match validator, 2/2 tests passing, cross-track note re: MOBILE_03"
```

Append to `DECISIONS_LOG.md`: note the honest cross-track dependency — full production behavior needs `MOBILE_03`'s real flagged-span output; the logic itself is real and tested against synthetic data now.

---

*Document version: 1.0*
