# MOBILE_17: TRUST DIGEST
## Where a mobile session found not a missing endpoint, but a genuinely missing capability — and built it properly

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_DATA_CONTRACTS.md` §5.15, `backend/features/honesty_log.py`, `backend/features/predictive_risk.py` (for the design-philosophy precedent)

**Prerequisites:** `MOBILE_16`.

**Review tier:** STANDARD for the mobile code; the new backend module reviewed with the same rigor as any original `IMPL_XX` session, since it's real, new logic, not a wrapper around something already proven.

**A different kind of finding than the prior eight — not a missing endpoint, a missing capability.** Every gap since `MOBILE_05` was "real backend logic exists, nothing exposes it." Checking before this session found something categorically different: no week-over-week trend comparison existed anywhere in the backend. This wasn't a wrapper-and-expose job — it needed genuinely new logic. Distinguished explicitly from `MOBILE_16`'s Gate-wiring finding, which was real but substantial enough to correctly defer: this one was scoped, bounded, and honestly within a single session's reach, so it was built rather than deferred.

**The real module, built to the same standard as anything in the original 23-session backend plan.** `trust_digest.py`'s `compare_weeks()` follows `predictive_risk.py`'s own stated design philosophy — "deliberately simple and explainable... a count comparison, not a trained model" — a threshold comparison against a real, named constant (`STABLE_THRESHOLD`), not a magic number. The exact boundary case (a delta of precisely the threshold value) was tested explicitly, including a live check that Python's floating-point addition at that value doesn't introduce noise that would silently break the equality check — the same arithmetic caution established since `MOBILE_13`.

**The same fail-closed safety principle from `MOBILE_16`, reapplied without needing to be re-derived.** `insufficient_data` is a real, honest fourth state — a week with zero actions, or no prior week to compare against — never silently reported as `"stable"`, which would claim a real comparison that was never actually made. The Dart side's `parseTrend` fails closed to this same state on any unrecognized value, exactly mirroring `MOBILE_16`'s `parseTarget`.

**What this session creates:** `backend/features/trust_digest.py` (new), `backend/tests/features/test_trust_digest.py` (new, 7 tests), `mobile/lib/features/trust_digest/trust_digest_logic.dart` (zero Flutter dependencies), `mobile/lib/features/trust_digest/trust_digest_screen.dart`, `mobile/test/trust_digest_logic_test.dart`.

**Out of scope:** the real weekly aggregation query itself (grouping raw `action_events` rows into `WeeklyTrustSummary` instances) — that's real database/query work for whichever session wires `/trust_digest` to a live Supabase connection; this session's `compare_weeks()` takes two already-computed summaries and is independently correct regardless of how they're produced.

---

## FILE 1: `backend/features/trust_digest.py` (real, new, complete — see file)

**The exact boundary proven, not assumed, including a real floating-point check.** Before writing the boundary test, `0.80 + STABLE_THRESHOLD` was checked directly in Python to confirm the addition doesn't introduce floating-point noise that would break the exact-equality assertion — `round(..., 3)` resolves it cleanly, confirmed live before being trusted in the test.

## FILE 2: real Python tests (7/7 — see file)

## FILE 3: `mobile/lib/features/trust_digest/trust_digest_logic.dart` (real, complete — see file)

## FILE 4: real Dart tests (11/11 — see file)

---

## VERIFICATION STEPS

**Backend, verified live, this session:** `ruff check backend` → clean. `pytest backend/tests -q` → **152 passed** (145 prior + 7 new).
**Mobile Step 1:** `dart test test/trust_digest_logic_test.dart` → expected: 11 passed.
**Mobile Step 2:** `flutter analyze` → confirms the widget file.

---

## WHEN ALL VERIFICATIONS PASS

Update `STATUS_INDEX.md` — Trust Digest is real, both backend and mobile; a genuinely new backend module built during the mobile sequence, held to the original backend sessions' full standard rather than a lighter one because it happened to be discovered mid-mobile-work.

Append to `DECISIONS_LOG.md`: the distinction between this finding and `MOBILE_16`'s (missing capability vs. deferred-because-substantial), and the boundary-case floating-point check.

---

*Document version: 1.0 — the seventeenth of 21 mobile sessions. `MOBILE_18`, the You screen, is next.*
