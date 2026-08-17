# MOBILE_16: TRUST
## Where preparing a mobile screen found a real backend staleness issue — and it got fixed properly, not worked around

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_DATA_CONTRACTS.md` §5.14, `backend/features/self_test_harness.py`

**Prerequisites:** `MOBILE_15`.

**Review tier:** STANDARD for the mobile code; the backend fix touches a genuinely trust-relevant claim (whether self-test results reflect the real Gate), reviewed with corresponding care even though it's a small change.

**A real finding that reached back into the backend, not just the mobile layer.** Checking `self_test_harness.py` before building this screen surfaced a genuinely stale claim in its own docstring: *"the real Gate...doesn't exist yet as code."* That was true when the file was written, and has been false since `IMPL_08`, many sessions ago. Confirmed by direct grep that nothing in the backend actually wires the real Gate into this harness — it still runs against `_stub_gate_for_demo`. This wasn't left as a mobile-session footnote; it was fixed directly in the backend, in the same session, because a Trust screen built on top of an uncorrected false claim would have compounded the problem rather than caught it.

**The fix, and why it's honest rather than a rushed patch.** Properly wiring the real Gate into the harness is real, substantial engineering — `AdversarialScenario`'s current toy format doesn't carry what the real `stage_a_checks`/`critic_call`/`judge_call` construction needs, and redesigning that deserves its own dedicated session, not something folded hastily into a mobile turn. Instead, this session did the two things that were honestly within scope: corrected the false docstring claim directly, and added a real `target: "stub" | "real_gate"` field to `run_self_test()`'s output — the same honesty mechanism as the Today screen's `source: live_backend | local_mirror` labeling, giving any future consumer (this screen, or any other) a real, checkable way to know what it's actually looking at, rather than a comment someone has to remember to distrust.

**What this session creates:** `mobile/lib/features/trust/trust_logic.dart` (zero Flutter dependencies), `mobile/lib/features/trust/trust_screen.dart`, `mobile/test/trust_logic_test.dart`. **What this session also fixes:** `backend/features/self_test_harness.py` (docstring correction, real `target` field), `backend/tests/features/test_self_test_harness.py` (two new real tests).

**Out of scope, honestly, not silently:** wiring the real Gate into the harness itself — a genuine, tracked, real open item now, not a fix pretended to be complete.

---

## FILE 1: `backend/features/self_test_harness.py` (real fix — see file)

**A real, load-bearing safety property in the new `target` field's default.** `run_self_test()` defaults `target` to `"stub"` — the honest, current truth — rather than requiring every caller to remember to specify it. A caller that forgets still gets an accurate label, not a silent overstatement.

## FILE 2: `mobile/lib/features/trust/trust_logic.dart` (real, complete — see file)

**The same fail-closed direction proven on the mobile side.** `parseTarget` maps any unrecognized string to `SelfTestTarget.stub`, never to `realGate` — proven by test with a deliberately unexpected value. An unrecognized target value failing toward the *more cautious* label is the honest direction; failing the other way would overstate confidence in something that was never actually confirmed.

## FILE 3: `mobile/lib/features/trust/trust_screen.dart` (real, complete — see file)

**A real placement decision, not left to chance.** The honesty label renders directly beneath the headline catch-rate number — the same visual pass a person's eye makes reading the number itself — not as small print at the screen's bottom where it could go unnoticed. `QUORUM_DATA_CONTRACTS.md` §5.14 calls this label load-bearing; the layout is built to actually treat it that way.

## FILE 4: real tests (14/14 across both languages — 2 real Python + 12 real Dart — see files)

---

## VERIFICATION STEPS (backend, run live this session; mobile, deferred to a real machine)

**Backend, verified live, this session:** `ruff check backend` → clean. `pytest backend/tests -q` → **145 passed** (143 prior + 2 new).
**Mobile Step 1:** `dart test test/trust_logic_test.dart` → expected: 12 passed.
**Mobile Step 2:** `flutter analyze` → confirms the widget file.

---

## WHEN ALL VERIFICATIONS PASS

Update `STATUS_INDEX.md` — the Trust screen is real; the backend's self-test harness now tells the truth about what it's actually testing, and the real Gate-wiring work is tracked as a genuine, standing open item rather than implied to be finished.

Append to `DECISIONS_LOG.md`: the stale docstring found and corrected, the `target` field as the real mechanism (not just a comment), and the new open item for real Gate wiring.

---

*Document version: 1.0 — the sixteenth of 21 mobile sessions. `MOBILE_17`, the Trust Digest screen, is next.*
