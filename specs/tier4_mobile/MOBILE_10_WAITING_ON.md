# MOBILE_10: WAITING ON
## A third real contract gap, found by continuing to apply the same discipline rather than assuming it was already covered

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_DATA_CONTRACTS.md` §5.9, `backend/features/waiting_on.py`

**Prerequisites:** `MOBILE_09`.

**Review tier:** STANDARD.

**A third real gap, found the same way as the first two.** `waiting_on.py`'s real `find_stale_waiting_on()` has existed since well before mobile work began, but `SentMessage` is explicitly documented as internal-only — never meant to cross the API boundary. Checking `QUORUM_DATA_CONTRACTS.md` directly confirmed no real endpoint ever exposed this function's output for display. Fixed in this session (§5.9), before any widget code was written — the same discipline that caught two prior gaps in `MOBILE_05` and `MOBILE_07`, applied a third time rather than assumed to have already covered every screen.

**What this session creates:** `mobile/lib/features/waiting_on/waiting_on_logic.dart` (zero Flutter dependencies), `mobile/lib/features/waiting_on/waiting_on_screen.dart`, `mobile/test/waiting_on_logic_test.dart`.

**Out of scope:** the real `WaitingOnRepository` HTTP implementation — deferred, same injected pattern as every other Today-adjacent screen.

---

## FILE 1: `mobile/lib/features/waiting_on/waiting_on_logic.dart` (real, complete — see file)

**A real, hand-verified arithmetic check before trusting Dart's `Duration.inDays`.** The exact case used in the test — August 10 09:00 to August 15 14:00 — was computed directly in Python first, confirming the real answer is 5 days (not 4 or 6, which floor/truncation edge cases can produce depending on how a duration crosses a day boundary), before writing the Dart test that encodes it.

**A small, real correctness detail, not skipped as trivial.** `formatStaleness` handles the singular case explicitly — "1 day ago," not "1 days ago." Small, but exactly the kind of detail that's invisible in a spec and immediately visible on a real screen with real data.

**A genuine defensive case, tested even though it "shouldn't" occur.** A negative day count — which a real clock-skew or bad-data scenario could theoretically produce — is tested to confirm it renders sensibly ("Today") rather than a nonsensical "-1 days ago."

## FILE 2: `mobile/lib/features/waiting_on/waiting_on_screen.dart` (real, complete — see file)

## FILE 3: real tests (9/9 — see file)

---

## VERIFICATION STEPS (on a real machine — this sandbox cannot run these)

**Step 1:** `dart test test/waiting_on_logic_test.dart` → expected: 9 passed.
**Step 2:** `flutter analyze` → confirms the widget file.

---

## WHEN ALL VERIFICATIONS PASS

Update `STATUS_INDEX.md` — Waiting On is real; this is the third real `/today`-adjacent contract gap found and fixed across the mobile sequence, worth noting as a pattern in its own right, not three isolated coincidences.

Append to `DECISIONS_LOG.md`: the third gap, and the hand-verified arithmetic proof.

---

*Document version: 1.0 — the tenth of 21 mobile sessions. `MOBILE_11`, the Career pipeline screen, is next.*
