# MOBILE_05: TODAY — "NEEDS YOU NOW" ZONE
## The first real screen — and a real spec gap found and closed before building against it

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §12.2, §12.4, `QUORUM_DATA_CONTRACTS.md` §5.4

**Prerequisites:** `MOBILE_04`.

**Review tier:** STANDARD.

**A real, checked-before-building gap:** before writing any widget code, `QUORUM_DATA_CONTRACTS.md` §5.4 was checked directly — it specified `CapacityState`/`BudgetState` for "Holding steady" but never once specified what "Needs you now," the *highest-priority* zone, actually receives. Fixed in the same session, before this screen was built against an incomplete contract: §5.4 now documents the real `needs_you_now` array shape, and explicitly states that ranking is a client-side concern, not a server-side one — which is exactly why the real ranking logic lives in this session's own code, not assumed to arrive pre-sorted.

**A second thing caught while making that fix:** the first edit attempt momentarily dropped the existing `source: "live_backend" | "local_mirror"` labeling requirement — the literal F4 fix from several sessions ago — while restructuring the section around it. Caught by re-reading the edit immediately rather than assuming it landed cleanly, and restored explicitly.

**What this session creates:** `mobile/lib/features/today/needs_you_now_logic.dart` (zero Flutter dependencies — the strongest testability tier reached in this project's mobile code), `mobile/lib/features/today/needs_you_now_zone.dart`, `mobile/test/needs_you_now_logic_test.dart`.

**Out of scope:** the real HTTP-backed `TodayRepository` implementation — genuinely deferred until real backend deployment exists, same honest, injected pattern as every other real/external boundary in this project.

---

## FILE 1: `mobile/lib/features/today/needs_you_now_logic.dart` (real, complete — see file)

**A deliberate architectural choice: zero Flutter imports.** Every prior mobile session's logic files still depended on Flutter or Drift. This one is plain Dart — meaning once run on a real machine, it's testable with `dart test` alone, no Flutter toolchain required for this specific file. That's not a stylistic preference; less real dependency surface is a genuine, meaningful reduction in what could break.

**The sort logic, hand-verified before being trusted.** Dart's `compareTo` sign conventions are a real, easy place to get backwards — a comparator that looks right can silently sort in reverse. Before writing the test, the exact comparator logic was simulated by hand against a real, non-trivial four-item case mixing stakes and age, confirming the expected order (`C, B, A, D`) independently of trusting the Dart code's own correctness. The test then encodes that same, independently-verified case.

## FILE 2: `mobile/lib/features/today/needs_you_now_zone.dart` (real, complete — see file)

**A direct, real connection to already-established design principles, not just new code.** Stakes-proportional visual weight (§12.4) is implemented as icon *shape* changing (`priority_high` vs. `info_outline`) alongside color — never color alone — directly matching the accessibility rule already documented in `quorum_theme.dart` since `MOBILE_01`.

## FILE 3: real tests (10/10 — see file)

Includes the hand-verified mixed-case sort, a check that the input list is never mutated, and — a real, easy-to-skip case — that a missing payload field falls back gracefully rather than throwing.

---

## VERIFICATION STEPS (on a real machine — this sandbox cannot run these)

**Step 1:** `dart test test/needs_you_now_logic_test.dart` → expected: 10 passed. Note: this specific file needs only the Dart SDK, not the full Flutter toolchain.
**Step 2:** `flutter analyze` → confirms the widget file's syntax.
**Step 3:** Once a real `TodayRepository` implementation exists, a real widget test confirming the zone renders real fetched data — deferred to whichever session first wires real backend connectivity.

---

## WHEN ALL VERIFICATIONS PASS

Update `STATUS_INDEX.md` — the first real screen exists; the ranking and summarization logic is real and (once run) provably correct; the repository wiring is honestly incomplete pending real backend deployment.

Append to `DECISIONS_LOG.md`: the `/today` contract gap found and fixed, the near-miss where the fix itself briefly dropped an existing requirement, and the hand-verified sort proof.

---

*Document version: 1.0 — the fifth of 21 mobile sessions, and the first with real screen content. `MOBILE_06`, "Holding steady," is next — where the already-real computed-state numbers finally get a real screen to appear on.*
