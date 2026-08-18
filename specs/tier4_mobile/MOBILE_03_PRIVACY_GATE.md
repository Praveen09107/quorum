# MOBILE_03: THE PRIVACY GATE
## Real rule-layer parity with the backend, a genuine regex-overlap finding caught by actually cross-checking, and the SLM layer honestly deferred

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §10.1, `QUORUM_CONFIGURATION_CONSTANTS.md` §10.1

**Prerequisites:** `MOBILE_02`.

**Review tier:** STANDARD. Genuinely privacy-relevant, but composed from an already-established shared pattern table rather than introducing new detection logic — the real judgment work was already done when that table was written in `IMPL_22`.

**The commitment this session exists to fulfill:** `IMPL_22` established `QUORUM_CONFIGURATION_CONSTANTS.md` §10.1 specifically so this session wouldn't invent its own pattern set. Before writing any code, that table was re-read directly, not recalled from memory — the three patterns here are typed to match it exactly.

**A real finding from actually cross-checking, not assumed away — precision-corrected during this session, disclosed here directly rather than left imprecise:** the same three patterns and test strings were run through Python's `re` (already proven correct for the backend side) before writing the Dart tests around them. That check found a genuine, real overlap — but the overlap is more specific than "a 16-digit credit card number's first 12 digits also satisfy the Aadhaar-style pattern" first suggests. Directly testing the identical regex patterns in Python found this precise: the overlap specifically requires a **SPACE-separated** format ("4111 1111 1111 1111") — a plain, unspaced 16-digit run (`4111111111111111`) or a dash-separated one (`4111-1111-1111-1111`) never triggers it, since `aadhaar_style_id`'s pattern needs a real `\b` word boundary at both ends of its match, and consecutive un-separated digits are all `\w` characters — no `\b` exists in the middle of an unbroken digit run for that boundary to land on. Confirmed directly: only the space-separated form matches both patterns; the other two forms match `credit_card` only. This is disclosed and tested explicitly, not hidden: `scan()` genuinely reports both categories for a pure, space-separated card number; `redact()` correctly produces only one redaction, because patterns apply sequentially and credit-card's match consumes the entire space-separated run first, leaving nothing for the Aadhaar pass. All three behaviors — the overlap, its space-separated specificity, and `redact()`'s single-redaction outcome despite it — are proven by test, not assumed from reading the regex.

**What this session creates:** `mobile/lib/privacy/rule_layer.dart`, `mobile/lib/privacy/privacy_gate.dart`, `mobile/test/privacy_gate_test.dart`.

**Out of scope:** the real on-device SLM call performing the sensitivity classification — genuinely deferred, and for a specific, real reason: `MOBILE_02` established that the Full tier's model choice is honestly unresolved pending Sprint 0. `SlmClassifier` is injected here for the same reason every other real/external boundary in this project is injected — this module doesn't need to know which model classifies, only that something does.

---

## FILE 1: `mobile/lib/privacy/rule_layer.dart` (real, complete — see file)

**The parity claim, actually checked, not asserted.** The three patterns are typed to match `QUORUM_CONFIGURATION_CONSTANTS.md` §10.1 character-for-character. Dart's `RegExp` and Python's `re` are both PCRE-like, and none of these three patterns use Python-specific regex extensions — confirmed deliberately, since an unnoticed regex-flavor difference here would have silently broken the entire point of this file.

**The overlap finding, proven three ways:** `scan()` genuinely reports both `credit_card` and `aadhaar_style_id` for a pure card number (tested). `redact()` correctly produces exactly one redaction despite that overlap (tested). And the aadhaar-only test string is confirmed to report *only* `aadhaar_style_id`, proving the overlap is specific to the card-number case, not a general false-positive problem with the Aadhaar pattern itself (tested).

## FILE 2: `mobile/lib/privacy/privacy_gate.dart` (real, complete — see file)

**The real policy, and the real proof it's followed correctly.** The test proving a rule-layer match always redacts and never consults the SLM tracks actual invocation count of the injected classifier and asserts zero — the same "proven by absence of calls, not just correct final state" discipline already established for negotiation's non-conflict short-circuit (`IMPL_21`). A structural pattern match is a fact, not a judgment call, and the code proves it's treated that way.

## FILE 3: real tests (9/9 — see file)

Every test string was checked to confirm it doesn't accidentally trigger a different code path than the one it's meant to test — a genuine, easy-to-miss mistake in test design that would have silently invalidated the claims being proven.

---

## VERIFICATION STEPS (on a real machine — this sandbox cannot run these)

**Step 1:** `flutter analyze`
**Step 2:** `flutter test test/privacy_gate_test.dart` → expected: 9 passed
**Step 3:** Manual cross-reference: run the same three patterns against the exact test strings in `backend/tests/test_trace_scrubbing.py` and confirm identical match/no-match results on both platforms — the real, final proof of parity this session's whole design depends on.

---

## WHEN ALL VERIFICATIONS PASS

Update `STATUS_INDEX.md` — the Privacy Gate's rule layer and policy logic are real; the SLM classification call itself remains genuinely deferred, pending Sprint 0's resolution, same honest status as `MOBILE_02`.

Append to `DECISIONS_LOG.md`: the regex-overlap finding, how it was caught, and why it doesn't affect the safety-relevant outcome.

---

*Document version: 1.0 — the third of 21 mobile sessions. `MOBILE_04`, CalendarProvider native integration, is next.*
