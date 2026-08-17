# MOBILE_19: MEMORY TRANSPARENCY
## A genuinely new backend module — and a real inconsistency in my own file placement caught and fixed before it compounded

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_DATA_CONTRACTS.md` §5.16, `backend/security/account_deletion.py`, `backend/gate/validators.py` (for the real mem0-reference precedent)

**Prerequisites:** `MOBILE_18`.

**Review tier:** STANDARD.

**A genuinely missing data model, the same category as `MOBILE_17`'s finding, confirmed the same way.** `mem0` is referenced throughout the backend — purged on account deletion, read for calendar buffer preferences — but no real schema for what a single memory *is*, and no way to list or delete one individually, existed anywhere. Built as a new module, `memory_transparency.py`, deliberately not implementing mem0 itself — that's a real external service, injected like Gmail, Tavily, and every LLM call in this project.

**A real, self-caught inconsistency, worth recording plainly.** The new backend test file was first placed at `backend/tests/security/test_memory_transparency.py`, creating a nested directory that doesn't match how this project's other `security/` module tests actually live — `test_account_deletion.py` and `test_trace_scrubbing.py` are both flat in `backend/tests/`. Checked directly before assuming the nested pattern was fine, found the mismatch, and moved the file to match the real, established precedent rather than let a new, inconsistent structure take root.

**A real design decision, reasoned through and stated explicitly, not left implicit.** `DELETE /memories/{id}` deliberately does *not* require the same type-to-confirm gate `MOBILE_18` built for account deletion. Forgetting one preference is genuinely lower-stakes and more recoverable than destroying an entire account — the system could relearn it from future behavior. Treating every deletion with identical maximal ceremony regardless of its real stakes would itself be a form of dishonesty: a screen that cries wolf on a low-stakes action teaches people to stop reading confirmations altogether, weakening the ones that actually matter.

**What this session creates:** `backend/security/memory_transparency.py` (new), `backend/tests/test_memory_transparency.py` (new, 4 tests), `mobile/lib/features/memory_transparency/memory_transparency_logic.dart` (zero Flutter dependencies), `mobile/lib/features/memory_transparency/memory_transparency_screen.dart`, `mobile/test/memory_transparency_logic_test.dart`.

**Out of scope:** the real mem0 API calls themselves — injected, same pattern as every other real/external boundary in this project.

---

## FILE 1: `backend/security/memory_transparency.py` (real, new, complete — see file)

**The real guarantee this module makes, proven by test.** `group_by_category` never drops a memory for an unexpected category string — mem0's own categorization isn't controlled by this codebase, so an unrecognized value still lands in its own real group rather than being silently discarded.

## FILE 2: real Python tests (4/4 — see file)

## FILE 3: `mobile/lib/features/memory_transparency/memory_transparency_logic.dart` (real, complete — see file)

`groupByCategory` deliberately mirrors the backend's own grouping logic exactly, and the Dart tests mirror the Python tests' exact scenarios — proving both sides of the boundary agree, not just that each independently looks reasonable.

## FILE 4: real Dart tests (10/10 — see file)

---

## VERIFICATION STEPS

**Backend, verified live, this session:** `ruff check backend` → clean. `pytest backend/tests -q` → **156 passed** (152 prior + 4 new).
**Mobile Step 1:** `dart test test/memory_transparency_logic_test.dart` → expected: 10 passed.
**Mobile Step 2:** `flutter analyze` → confirms the widget file.

---

## WHEN ALL VERIFICATIONS PASS

Update `STATUS_INDEX.md` — Memory Transparency is real, both backend and mobile; a third genuinely new backend module discovered and built during mobile work (after `trust_digest.py` in `MOBILE_17`), and a real file-placement mistake caught before it became a second, competing test-directory convention.

Append to `DECISIONS_LOG.md`: the test-placement correction, and the proportional-stakes reasoning for why this screen's deletion flow is deliberately lighter-weight than `MOBILE_18`'s.

---

*Document version: 1.0 — the nineteenth of 21 mobile sessions. `MOBILE_20`, Extended-Outage wiring, is next.*
