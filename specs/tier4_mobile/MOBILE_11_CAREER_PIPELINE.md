# MOBILE_11: CAREER PIPELINE
## A fourth real contract gap, and a screen built to handle a genuinely open vocabulary rather than assume a fixed pipeline

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_DATA_CONTRACTS.md` §5.10, `backend/migrations/001_initial_schema.sql` (`applications`, `interviews`)

**Prerequisites:** `MOBILE_10`.

**Review tier:** STANDARD.

**A fourth real gap, found by continuing to apply the check as a default, not an occasional habit.** `applications` has existed as a real table since infrastructure work; no endpoint ever exposed it. Fixed as §5.10, before any widget code.

**A second, genuinely important finding from the same check — not just "the endpoint was missing," but a fact about the data itself.** Reading the real schema directly (not recalled from having written it) showed `applications.status` carries no `CHECK` constraint, unlike `interviews.status`, which does. The real status vocabulary is open. Cross-checking the codebase further confirmed only `"applied"` and `"interview_scheduled"` are actually exercised anywhere today — `"offer"` and `"rejected"` are plausible, expected future values, not yet real anywhere. Building this screen around an assumed fixed four-stage pipeline would have been a genuine, real correctness bug waiting for the first application to arrive with a status nobody anticipated.

**What this session creates:** `mobile/lib/features/career/career_pipeline_logic.dart` (zero Flutter dependencies), `mobile/lib/features/career/career_pipeline_screen.dart`, `mobile/test/career_pipeline_logic_test.dart`.

**Out of scope:** the real `CareerPipelineRepository` HTTP implementation — deferred, same injected pattern as every other feature screen.

---

## FILE 1: `mobile/lib/features/career/career_pipeline_logic.dart` (real, complete — see file)

**The actual property this session was built to guarantee, proven by test, not just designed for.** `orderedStatusKeys` places known statuses first in a sensible order, then appends any genuinely unrecognized status afterward — alphabetically, deterministically — rather than dropping it or crashing. `statusLabel` produces a real, readable fallback (de-snaked, capitalized) for anything outside the four known values, rather than showing a raw `phone_screen_pending` string or failing silently.

**Deterministic ordering for the unknown case specifically, not left to map-iteration chance.** Two unrecognized statuses in the same data set sort alphabetically against each other — a real, small detail that matters because Dart map iteration order isn't something this screen should ever depend on for a user-visible list's stability across rebuilds.

## FILE 2: `mobile/lib/features/career/career_pipeline_screen.dart` (real, complete — see file)

## FILE 3: real tests (11/11 — see file)

---

## VERIFICATION STEPS (on a real machine — this sandbox cannot run these)

**Step 1:** `dart test test/career_pipeline_logic_test.dart` → expected: 11 passed.
**Step 2:** `flutter analyze` → confirms the widget file.

---

## WHEN ALL VERIFICATIONS PASS

Update `STATUS_INDEX.md` — Career pipeline is real; this is the fourth contract gap in this recurring pattern, and the first one where the fix also required genuinely re-reading the schema for an assumption (a closed status vocabulary) that turned out to be false.

Append to `DECISIONS_LOG.md`: the open-vocabulary finding, and why building around an assumed fixed pipeline would have been a real bug.

---

*Document version: 1.0 — the eleventh of 21 mobile sessions. `MOBILE_12`, the Company Research Digest screen, is next.*
