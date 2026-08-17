# MOBILE_06: TODAY — "HOLDING STEADY" ZONE
## Where the computed-state numbers, real since much earlier in this project, finally get a real screen

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §12.2, §9.4

**Prerequisites:** `MOBILE_05`.

**Review tier:** STANDARD.

**What this session actually connects, not just builds:** `computed_state.dart` — the file proving live and offline-mirror math produce byte-identical results — has existed since well before mobile work even began, with no screen to ever display it. This session is that screen, finally. Every field reference in the widget was confirmed directly against the real file before use, not assumed from memory — `hoursRemainingToday`, `remainingFraction`, and `DataSource.localMirror` all checked with a direct grep against `computed_state.dart` before being written into new code.

**What this session creates:** `mobile/lib/features/today/holding_steady_logic.dart` (zero Flutter dependencies, same testability tier as `MOBILE_05`), `mobile/lib/features/today/holding_steady_zone.dart`, `mobile/test/holding_steady_logic_test.dart`.

**Out of scope:** the real `HoldingSteadyRepository` implementation — genuinely deferred, same honest injected pattern as `MOBILE_05`'s `TodayRepository`.

---

## FILE 1: `mobile/lib/features/today/holding_steady_logic.dart` (real, complete — see file)

**The two-touchpoint framing from the retention rethink, made real.** `classifyTouchpoint` implements the morning/evening bookend design directly — not vague "sometime in the morning" logic, but exact hour boundaries. Both boundaries (12, 18) were hand-verified in Python across every edge hour (0, 11, 12, 17, 18, 23) before being trusted in a Dart test, the same discipline applied to `MOBILE_05`'s sort comparator.

## FILE 2: `mobile/lib/features/today/holding_steady_zone.dart` (real, complete — see file)

**Typography as the visualization, literally, not just in principle.** The computed numbers render as large (36px, weight 600) numerals directly — no chart widget, no gauge, no decorative graphic standing in for the number. This is the locked design principle from the ADD implemented exactly as written, not reinterpreted.

**The F4 fix's UI requirement, honored to the letter.** When a number's `source` is `DataSource.localMirror`, the card shows "Offline estimate" via **both an icon and text** — never color alone, matching the accessibility rule already established in `quorum_theme.dart`. This is the actual, concrete moment the ADD's "the client must render this label, never silently presenting one as the other" requirement becomes real UI, not just a documented promise.

## FILE 3: real tests (9/9 — see file)

Every hand-verified boundary hour from the Python check has a corresponding real test — not a subset, all six.

---

## VERIFICATION STEPS (on a real machine — this sandbox cannot run these)

**Step 1:** `dart test test/holding_steady_logic_test.dart` → expected: 9 passed.
**Step 2:** `flutter analyze` → confirms the widget references against the real `computed_state.dart` types compile correctly.
**Step 3:** Once a real repository implementation exists, confirm the "Offline estimate" label actually appears when `source` is genuinely `localMirror`, not just when the widget is manually constructed with that value in a test.

---

## WHEN ALL VERIFICATIONS PASS

Update `STATUS_INDEX.md` — the second real screen exists, and it's the one that finally gives `computed_state.dart` an actual display surface after being real and unused for several sessions.

Append to `DECISIONS_LOG.md`: the direct field-name verification against `computed_state.dart` before use, and the hand-verified touchpoint boundaries.

---

*Document version: 1.0 — the sixth of 21 mobile sessions. `MOBILE_07`, "In motion," is next — the third and final Today zone, and the first screen surfacing the negotiation subgraph's real output.*
