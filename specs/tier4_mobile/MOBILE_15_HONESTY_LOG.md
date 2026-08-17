# MOBILE_15: THE LOG (HONESTY LOG)
## Where a stated design commitment had to become a literal, testable UI decision — not just a data shape

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_DATA_CONTRACTS.md` §5.13, `backend/features/honesty_log.py`

**Prerequisites:** `MOBILE_14`.

**Review tier:** STANDARD. Not security-relevant, but genuinely values-relevant — this screen is a direct, literal implementation of one of this project's own stated commitments, and getting it wrong would be a real failure of that commitment, not a cosmetic bug.

**A seventh real gap, found the same way as the prior six.** `honesty_log.py`'s `build_honesty_feed()` has existed since well before mobile work began; nothing ever exposed it. Fixed as §5.13.

**A real design decision, reasoned through explicitly rather than defaulted to the obvious pattern.** `build_honesty_feed()`'s own docstring states the actual commitment directly: successes and failures shown with "EQUAL prominence, not buried." The obvious UI pattern — a `TabBar` splitting the two — was considered and rejected: even with two visually symmetric tabs, one is what a person sees by default, and the other is a tap away. That's not equal enough for a commitment this explicit. This session uses a single scrolling screen instead, with identical heading style and identical card style for every section, in the same order the backend's own response already provides them — not reordered to push either one up or down.

**A second, genuinely important finding from reading the real backend code, not assumed:** `failures_and_catches` bundles two outcomes that mean structurally different things — `caught_by_gate` (the safety system worked, catching something before it went out) and `corrected_by_user` (the system missed something, and a person had to catch it after the fact). Collapsing both into one generic "failure" label would lose exactly the distinction this project's whole verification architecture exists to make meaningful. Both get their own honest, distinct label, proven by test to actually differ.

**What this session creates:** `mobile/lib/features/honesty_log/honesty_log_logic.dart` (zero Flutter dependencies), `mobile/lib/features/honesty_log/honesty_log_screen.dart`, `mobile/test/honesty_log_logic_test.dart`.

**Out of scope:** the real `HonestyLogRepository` HTTP implementation — deferred, same injected pattern as every other feature screen.

---

## FILE 1: `mobile/lib/features/honesty_log/honesty_log_logic.dart` (real, complete — see file)

**A real, honest distinction preserved in the data model itself, not just the labels.** `successRate` is nullable, and `formatSuccessRate(null)` renders "No data yet" — genuinely different from a real `0.0`, which renders "0%." Conflating "nothing to compute from" with "everything failed" would be a real, meaningful misrepresentation, proven distinct by test.

## FILE 2: `mobile/lib/features/honesty_log/honesty_log_screen.dart` (real, complete — see file)

The single-scroll, identical-styling design decision, with the reasoning for rejecting the TabBar alternative recorded directly in the file's own header comment — not left for a future reader to wonder why the obvious pattern wasn't used.

## FILE 3: real tests (11/11 — see file)

Includes a direct, explicit assertion that `corrected_by_user` and `caught_by_gate` produce genuinely different label strings — not just that each individually looks reasonable, but that they're provably not collapsed into each other.

---

## VERIFICATION STEPS (on a real machine — this sandbox cannot run these)

**Step 1:** `dart test test/honesty_log_logic_test.dart` → expected: 11 passed.
**Step 2:** `flutter analyze` → confirms the widget file.
**Step 3 (the real, meaningful one, once a repository exists):** confirm on an actual device, scrolling through a real feed with both real successes and real failures, that neither section requires extra interaction to reach and both render with visually identical treatment — the literal, human confirmation of the design commitment this whole session was built around.

---

## WHEN ALL VERIFICATIONS PASS

Update `STATUS_INDEX.md` — the Honesty Log is real; the seventh recurring contract gap, and the first mobile session where a stated project value had to be reasoned into a specific, defensible UI decision rather than just implemented in the obvious way.

Append to `DECISIONS_LOG.md`: the TabBar-vs-single-scroll reasoning, and the caught_by_gate/corrected_by_user distinction preserved.

---

*Document version: 1.0 — the fifteenth of 21 mobile sessions. `MOBILE_16`, the Trust screen, is next.*
