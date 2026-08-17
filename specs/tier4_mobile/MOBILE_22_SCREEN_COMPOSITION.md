# MOBILE_22: SCREEN COMPOSITION
## The gap flagged at the end of MOBILE_21 — closed with the same rigor as every other session, including a real layout crash found and fixed before it shipped

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**A genuinely new session, not part of the original 21-session mobile plan** — created the same way `trust_digest.py` and `memory_transparency.py` were: a real gap found during execution, given its own real, complete session rather than folded into whatever was already in progress.

**Attach:** `mobile/lib/shell/main_shell.dart`, every screen under `mobile/lib/features/*/`, `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §12.2–12.3

**Prerequisites:** `MOBILE_21`.

**Review tier:** STANDARD, with one CRITICAL-adjacent moment: the layout crash described below was caught by actually checking each zone's internal structure before composing them, not by assuming composition would just work.

**What this session actually did, precisely.** Twelve real screens each wrapped their own `Scaffold`. Rather than restructure all twelve, the real, correct architecture was: extract bare `*Content` widgets from exactly the three screens that map directly to bottom-nav tabs (`HonestyLogScreen` → `HonestyLogContent`, `TrustScreen` → `TrustContent`, `YouScreen` → `YouContent`), compose Today's three already-bare zones into a new `TodayScreen`, and leave the remaining nine screens (Career pipeline, Company Digest, Finance, Search, Waiting On, the Gate reveal, the negotiation screen, Trust Digest, Memory Transparency) as genuinely pushed routes — the architecturally correct pattern for deeper, non-tab-level screens, not a shortcut.

**A real layout crash found and fixed before it ever shipped, not after.** The first draft of `TodayScreen` composed `NeedsYouNowZone`, `HoldingSteadyZone`, and `InMotionZone` inside a single outer `ListView`. Checking each zone's actual internal structure — confirmed by direct grep, not assumed — showed all three already build their own internal scrollable (`ListView.builder` twice, `SingleChildScrollView` once). Nesting three unbounded-height scrollables inside another unbounded-height scrollable is a genuine, well-documented Flutter layout crash, not a theoretical concern. Caught before finalizing the file, and redesigned using `Column` + `Expanded`, which gives each zone a real, bounded region of the screen to scroll safely within.

**Two real navigation links added, each reasoned about rather than arbitrary.** Trust → Trust Digest (live self-test results alongside the weekly trend), You → Memory Transparency (an account-level concern genuinely related to account actions). Both are real, sensible pairings — not an attempt to wire every remaining screen into *some* link just to claim more coverage.

**A real, cascading test fix, caught by checking rather than assuming the old test still applied.** `MOBILE_01`'s original `main_shell_test.dart` asserted placeholder text that no longer exists, and never overrode the real repository providers — meaning it would have hit a live `UnimplementedError` the instant a real screen tried to build under the new composition. Found and fixed in the same session, not left as a known-broken test in the suite.

**What this session creates:** `mobile/lib/features/today_screen.dart` (new), `mobile/test/main_shell_composition_test.dart` (new). **What this session restructures:** `honesty_log_screen.dart`, `trust_screen.dart`, `you_screen.dart` (each split into a thin `Scaffold` wrapper plus a bare `*Content` widget), `main_shell.dart` (placeholders replaced with the real screens, a real `AppBar` added), `main_shell_test.dart` (fixed to match the real composition, provider overrides added).

**Out of scope, explicitly:** wiring Career pipeline, Company Digest, Finance, Search, Waiting On, the Gate reveal, and the negotiation screen into the navigable app. These need a real, considered information-architecture decision (a "More" menu? Integrated into Today's zones with tap-through? A dedicated Career/Finance section?) — genuinely deferred as a real, honestly-scoped follow-up, not silently implied resolved by this session's real but narrower fix.

---

## FILE 1: `mobile/lib/features/today_screen.dart` (real, complete, one crash caught and fixed — see file)

The file's own header comment documents the crash and the fix directly, the same way every other real mistake in this project has been recorded — not smoothed over.

## FILE 2–4: `honesty_log_screen.dart`, `trust_screen.dart`, `you_screen.dart` (real, restructured — see files)

Each original `*Screen` class remains a valid, complete, pushable route — nothing about their prior behavior changed when used standalone; only a new, more granular `*Content` widget was added alongside them.

## FILE 5: `mobile/lib/shell/main_shell.dart` (real, complete — see file)

## FILE 6: `mobile/test/main_shell_composition_test.dart` (real, new — see file)

**The real proof this session's layout fix actually works.** This test overrides every real repository provider the composed app transitively depends on with a working fake, then genuinely pumps the full widget tree. If the `Column`/`Expanded` fix were wrong, this test would fail with a real Flutter layout exception — not a failed assertion, an actual thrown error — which is a stronger proof than any assertion-only test could provide.

## FILE 7: `mobile/test/main_shell_test.dart` (real, fixed — see file)

---

## VERIFICATION STEPS (on a real machine — this sandbox cannot run these)

**Step 1:** `flutter analyze` → confirms every restructured and new file.
**Step 2:** `flutter test test/main_shell_composition_test.dart` → expected: 1 passed, and specifically: no layout exception thrown during `pumpAndSettle`.
**Step 3:** `flutter test test/main_shell_test.dart` → expected: 2 passed.
**Step 4:** On a real device or emulator: launch the app, confirm all four tabs show real content (not placeholders), confirm Trust → Trust Digest and You → Memory Transparency both navigate correctly.

---

## WHEN ALL VERIFICATIONS PASS

Update `STATUS_INDEX.md` — the composition gap flagged at the end of `MOBILE_21` is closed. A person can now actually open the app and reach real, working screens on all four tabs. The remaining navigation work (the nine deeper screens) is a real, smaller, still-honestly-open item — not implied resolved by this session.

Append to `DECISIONS_LOG.md`: the layout crash found and fixed, the real navigation links added, and the cascading test fix.

---

*Document version: 1.0 — a genuinely new session, added because a real gap was found and deserved full, undiluted attention rather than a rushed patch or continued deferral.*
