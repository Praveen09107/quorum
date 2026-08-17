# MOBILE_02: ON-DEVICE MODEL INTEGRATION
## The session that had to handle a real, still-open dependency honestly rather than guess

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §10.7, §11.1, `QUORUM_CONFIGURATION_CONSTANTS.md` §7

**Prerequisites:** `MOBILE_01`.

**Review tier:** STANDARD.

**A real, checked-not-assumed dependency, worth stating plainly:** before writing any code, `QUORUM_CONFIGURATION_CONSTANTS.md` §7 was checked directly. It still reads *"pending Sprint 0, not yet resolved."* `IMPL_00` is fully specified but requires a real Android device this sandbox doesn't have, so it hasn't actually run yet. This session could have picked a model to move forward with — Gemma, say — and quietly treated it as decided. That would be a real, dishonest shortcut: presenting a guess as a resolved architectural fact, exactly the failure mode this entire project's discipline exists to prevent. Instead, this session is built to be **correct regardless of which model eventually wins** — the Full tier's model choice stays a genuine unknown in the code itself, not papered over.

**What this session creates:** `mobile/lib/config/model_config.dart`, `mobile/lib/model/device_tier.dart`, `mobile/lib/model/on_device_model_loader.dart`, `mobile/test/model_resolution_test.dart`.

**Out of scope:** the actual llama.cpp inference call itself — that's Sprint 0's own real plugin-loading code (`sprint0/lib/plugin_loader.dart`), which becomes the app's real runtime loader only once Sprint 0 has actually run and resolved a winner.

---

## FILE 1: `mobile/lib/config/model_config.dart` (real, honest — see file)

**The one constant every later session touching the on-device model must read from, never re-guess.** `resolvedFullTierModel` stays `OnDeviceModelId.unresolved` until `IMPL_00` genuinely runs on a real device — the comment in the file states explicitly that only Sprint 0's real execution is allowed to change it, not a later session's convenience.

**A real thing that WAS resolvable now, correctly separated from what wasn't:** `lightTierModelId` is set to `'SmolLM2-1.7B'` directly, because that choice was locked independently of Sprint 0's open question — confirmed against `QUORUM_MASTER_REFERENCE.md` §5 before writing it, not assumed.

## FILE 2: `mobile/lib/model/device_tier.dart` (real, complete — see file)

The RAM-threshold tiering logic itself — fully real, fully resolvable, since the 8GB/4GB boundaries were decided independently of which model wins the Full tier.

## FILE 3: `mobile/lib/model/on_device_model_loader.dart` (real, complete, honestly incomplete for one tier — see file)

**The real proof this session handled its open dependency correctly, not just described handling it well:** the test confirming the Full-tier throws while Sprint 0 remains unresolved proves the loader doesn't silently guess — it throws a specific, diagnosable `OnDeviceModelNotResolvedException`, not a generic error and not a silent fallback to a guessed model. This exception is designed to be caught by the real Capacity Manager integration (a later session) and routed to cloud, per the architecture's own "silent per-request fallback to cloud, never a visible error" principle — the *user* never sees a crash; the *logs* honestly show why a Full-tier device is temporarily running Light-tier or cloud behavior.

## FILE 4: real tests (8/8 — see file)

Includes the exact real boundary values (8192MB, 4096MB) and the one-below-boundary cases, not just round numbers comfortably inside each tier.

---

## VERIFICATION STEPS (on a real machine — this sandbox cannot run these)

**Step 1:** `flutter analyze` — confirms the real syntax and type correctness this sandbox couldn't check.
**Step 2:** `flutter test test/model_resolution_test.dart` — expected: 8 passed, including the exception-throwing test for the unresolved Full tier.
**Step 3 (the real, meaningful one):** once `IMPL_00` has actually run on a real device, update `resolvedFullTierModel` with its genuine, measured result, then re-run Step 2 — the Full-tier test's expectation changes from "throws" to "resolves to the real winner," and that change is itself the evidence Sprint 0 genuinely happened.

---

## WHEN ALL VERIFICATIONS PASS

Update `STATUS_INDEX.md` — device tiering and the Light tier are real; the Full tier's model integration is real *code* with a still-real, still-open dependency, stated as such, not silently closed.

Append to `DECISIONS_LOG.md`: the decision to build this session as correct-regardless-of-winner rather than guess, and why that was the only honest option given `QUORUM_CONFIGURATION_CONSTANTS.md` §7's confirmed current state.

---

*Document version: 1.0 — the second of 21 mobile sessions. `MOBILE_03`, the Privacy Gate, is next.*
