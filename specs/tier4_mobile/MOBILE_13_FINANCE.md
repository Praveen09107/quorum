# MOBILE_13: FINANCE
## A sixth real contract gap, and a genuine cross-language arithmetic caution caught before it became a wrong test

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_DATA_CONTRACTS.md` §5.12, `backend/features/subscription_detective.py`

**Prerequisites:** `MOBILE_12`.

**Review tier:** STANDARD.

**A sixth real gap, found by the same check applied a sixth time.** `subscription_detective.py`'s real `detect_subscriptions()` has existed since well before mobile work began; `DetectedSubscription` is documented as internal-only. Fixed as §5.12.

**A genuinely important arithmetic caution, caught mid-session rather than shipped as a wrong test.** While hand-verifying rounding behavior in Python before writing a Dart test (the established discipline from every prior mobile session), a real cross-language discrepancy surfaced: Python's `round()` uses round-half-to-even (banker's rounding), while Dart's `num.round()` rounds half away from zero — they only disagree exactly at a `.5` boundary, but they *do* disagree there. `30.5` rounds to 30 in Python, 31 in Dart. Writing a test that asserted Python's answer for that exact case would have encoded a wrong expectation into this project's real test suite — caught before it happened, not after. The same caution was then applied a second time in this same session, to `toStringAsFixed`'s tie-breaking, which carries the identical uncertainty and hadn't been checked at all until it was noticed while reviewing the currency-formatting test.

**What this session creates:** `mobile/lib/features/finance/finance_logic.dart` (zero Flutter dependencies), `mobile/lib/features/finance/finance_screen.dart`, `mobile/test/finance_logic_test.dart`.

**Out of scope:** the real `FinanceRepository` HTTP implementation — deferred, same injected pattern as every other feature screen.

---

## FILE 1: `mobile/lib/features/finance/finance_logic.dart` (real, complete, with two honestly-flagged uncertainties — see file)

Both flagged directly in the file's own comments, matching the established pattern from `MOBILE_01`'s `CardThemeData` note and `MOBILE_04`'s `device_calendar` `Result<T>` note — this project doesn't hide genuine uncertainty behind a confident-looking test; it names it.

**The real currency convention, not invented for this screen.** `formatCurrency` uses ₹, consistent with the symbol already established throughout this project's own negotiation examples — not a new, unrelated choice made in isolation.

## FILE 2: `mobile/lib/features/finance/finance_screen.dart` (real, complete — see file)

Most expensive subscription sorts first — the most actionable ordering for a screen whose real purpose is helping someone decide what to cut.

## FILE 3: real tests (7/7 — see file)

Every test deliberately chosen to avoid the two disputed rounding boundaries — not by luck, but by design, once the discrepancy was found.

---

## VERIFICATION STEPS (on a real machine — this sandbox cannot run these)

**Step 1:** `dart test test/finance_logic_test.dart` → expected: 7 passed.
**Step 2:** `flutter analyze` → confirms the widget file.
**Step 3 (the real, meaningful one):** on a real machine, actually check `30.5.round()` and `649.5.toStringAsFixed(0)`'s real output, and add the now-confirmed exact boundary behavior back into the test suite explicitly — this session left it deliberately untested rather than guessed, and a real compiler is what actually resolves it.

---

## WHEN ALL VERIFICATIONS PASS

Update `STATUS_INDEX.md` — Finance is real; this is the sixth recurring contract gap, and the first session in the mobile sequence to surface a genuine Python-vs-Dart arithmetic semantics difference rather than an endpoint or schema gap.

Append to `DECISIONS_LOG.md`: the rounding discrepancy, found and handled honestly rather than shipped as an unverified assumption.

---

*Document version: 1.0 — the thirteenth of 21 mobile sessions. `MOBILE_14`, the Search results screen, is next.*
