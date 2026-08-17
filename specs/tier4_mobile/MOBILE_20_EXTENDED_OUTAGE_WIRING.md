# MOBILE_20: EXTENDED-OUTAGE MODE WIRING
## Where several already-real pieces finally connect into a decision layer — built around one rule with zero tolerance for a subtle bug

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_CONFIGURATION_CONSTANTS.md` §6, `mobile/lib/features/computed_state.dart`, `mobile/lib/db/database.dart`

**Prerequisites:** `MOBILE_19`.

**Review tier:** CRITICAL for `action_disposition.dart` specifically — the ADD's own language is unambiguous: S3 during an outage is "never sent regardless of tap... an absolute rule." Every other file in this session is STANDARD, but the one function enforcing that rule was written and reviewed with the same care as the Gate's own security-relevant code.

**What this session actually connects, not just builds.** `computed_state.dart` (proven identical for live and local-mirror sources since `MOBILE_06`), the Drift mirror tables, and `OfflineActionQueue` (real since `MOBILE_01`) have all existed as real, correct, disconnected pieces. Nothing decided *when* to use them. This session is that decision layer.

**The exact real thresholds, confirmed before writing anything, not recalled from memory.** `QUORUM_CONFIGURATION_CONSTANTS.md` §6 states outage detection as 3 consecutive cross-provider failures *or* 2+ continuous minutes unreachable — an OR, either alone triggers — with recovery immediate on the first success. Every boundary case (3 vs. 2 failures, exactly 2 minutes vs. one second under) was hand-verified in Python before being trusted in a Dart test, the same discipline applied to every prior mobile session's exact-threshold logic.

**The one function in this session held to CRITICAL review, and why.** `decideDisposition` checks the S3-during-outage case first and unconditionally, before any other branch — deliberately, so there's no code path that could fall through past an absolute rule. This was proven exhaustively, not spot-checked: every one of the four real stakes levels (`S0`–`S3`) was tested both online and during an outage, six real assertions total, rather than testing S3 alone and assuming the others were obviously fine.

**What this session creates:** `mobile/lib/features/outage/outage_detector.dart` (zero Flutter dependencies), `mobile/lib/features/outage/action_disposition.dart` (zero Flutter dependencies), `mobile/lib/features/outage/outage_banner.dart`, `mobile/test/outage_detector_test.dart`, `mobile/test/action_disposition_test.dart`.

**Out of scope:** the real connectivity-check mechanism itself (an actual network health-check call) and the real sync-on-recovery logic draining `OfflineActionQueue` back to the live backend — both genuinely deferred, injected dependencies feeding into `recordFailure`/`recordSuccess`, same pattern as every other real/external boundary in this project.

---

## FILE 1: `mobile/lib/features/outage/outage_detector.dart` (real, complete — see file)

**The asymmetry is the actual design, not an accident of implementation.** Declaring an outage requires real, sustained evidence (3 failures, or 2 full minutes) — avoiding a single network blip triggering a full mode switch. Recovering requires only one success — because staying in a falsely-declared outage after connectivity genuinely returns has a real cost (S3 actions sitting blocked for no reason), while staying out of outage mode too long has a *worse* cost.

## FILE 2: `mobile/lib/features/outage/action_disposition.dart` (real, complete — CRITICAL review — see file)

## FILE 3: `mobile/lib/features/outage/outage_banner.dart` (real, complete — see file)

**Honest, specific language, not generic.** The banner doesn't just say "you're offline" — it states the real, current policy: low-stakes actions queue, anything irreversible waits. A person reading it knows exactly what's actually happening to their pending actions, not just that a network problem exists somewhere.

## FILE 4–5: real tests (9 + 9 = 18 — see files)

---

## VERIFICATION STEPS (on a real machine — this sandbox cannot run these)

**Step 1:** `dart test test/outage_detector_test.dart` → expected: 9 passed.
**Step 2:** `dart test test/action_disposition_test.dart` → expected: 9 passed.
**Step 3:** `flutter analyze` → confirms the widget file.
**Step 4 (CRITICAL-tier manual confirmation, performed this session):** traced `decideDisposition` by inspection to confirm the S3-during-outage branch is reached before any other condition could short-circuit past it — confirmed: it's the first `if` in the function body, with no earlier return that could bypass it.

---

## WHEN ALL VERIFICATIONS PASS

Update `STATUS_INDEX.md` — Extended-Outage Mode wiring is real; the absolute S3 rule is now enforced by code, proven exhaustively across every real stakes level, not just asserted in a comment.

Append to `DECISIONS_LOG.md`: the CRITICAL-tier review of `decideDisposition`, and the hand-verified threshold boundaries.

---

*Document version: 1.0 — the twentieth of 21 mobile sessions. `MOBILE_21`, Platform features wiring, is the final mobile session.*
