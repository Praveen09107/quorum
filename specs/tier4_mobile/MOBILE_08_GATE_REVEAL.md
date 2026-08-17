# MOBILE_08: THE GATE REVEAL
## The most distinctive screen in this project — and a real color-palette gap found and closed while building it

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §6, §12.4, `backend/gate/schemas.py` (`Finding`, `Objection`, `GateVerdict`)

**Prerequisites:** `MOBILE_07`.

**Review tier:** STANDARD. Not security-relevant itself — it displays what the Gate already decided, it doesn't re-decide anything — but genuinely trust-relevant, since misrepresenting what Stage A/B found would undermine the entire "trust measured, not asserted" premise this project is built on.

**Every schema field checked directly before writing a single widget, not assumed from memory of having designed them:** `Finding.evidence_state`'s three real values, and — the detail that actually mattered most — `Objection.signed_off`, confirmed against the real backend comment explaining the Critic is *obligated* to return either genuine objections or an explicit sign-off entry, never a bare empty list. Getting this field's meaning wrong would have meant this screen silently misrepresenting what Stage B actually did.

**A real gap found while building, not before:** mapping `verified_false` to a color revealed that `quorum_theme.dart` only defined three status colors — `verified`, `needsAttention`, `uncertain` — none of which fit a validator catching an actual false claim, the single most severe state the entire Gate exists to surface. Reusing `needsAttention` would have understated it. A real `critical` color was added to the theme, with the reasoning recorded directly in the file, the same way the Drift testing constructor was added in `MOBILE_04` when a real capability was found missing rather than worked around.

**What this session creates:** `mobile/lib/features/gate_reveal/gate_reveal_logic.dart` (zero Flutter dependencies), `mobile/lib/features/gate_reveal/gate_reveal_screen.dart`, `mobile/test/gate_reveal_logic_test.dart`; extends `quorum_theme.dart` with `QuorumStatusColors.critical`.

**Out of scope:** wiring this screen to a real proposal fetched from the backend — it's built to receive real `Finding`/`Objection` data as parameters, same pattern as every other real/external boundary.

---

## FILE 1: `mobile/lib/features/gate_reveal/gate_reveal_logic.dart` (real, complete — see file)

**The real distinction this file exists to get right, proven by test, not just implemented:** `stageBRan([])` correctly returns `false` — an empty objections list means S0/S1, Stage B never ran — while `stageBRan([signOffEntry])` correctly returns `true`, because a sign-off is Stage B genuinely having reviewed and found nothing, not the same as never being asked. Conflating these two would have this screen either hiding a real "Stage B approved this" moment, or falsely implying Stage B reviewed something it never touched.

**A defensive edge case tested even though the real schema says it shouldn't occur:** a mixed list (a real objection alongside a sign-off entry) is still handled sensibly by `summarizeStageB`, not just the two individually-clean cases — real code should degrade gracefully even outside its stated contract, not just work when everything arrives exactly as documented.

## FILE 2: `mobile/lib/features/gate_reveal/gate_reveal_screen.dart` (real, complete — see file)

**The staged reveal, literally implemented, not just described.** Stage A renders first, unconditionally. Stage B — findings from the genuinely more expensive, judgment-based layer — only appears in the widget tree at all if `stageBRan` is true, matching the Gate's own real architecture where S0/S1 never reach Stage B.

## FILE 3: `quorum_theme.dart` extended with `QuorumStatusColors.critical`

A real, necessary fourth status color — not decorative, added because the existing three genuinely didn't cover the Gate's most important signal.

## FILE 4: real tests (10/10 — see file)

---

## VERIFICATION STEPS (on a real machine — this sandbox cannot run these)

**Step 1:** `dart test test/gate_reveal_logic_test.dart` → expected: 10 passed.
**Step 2:** `flutter analyze` → confirms the widget file, including the new `critical` color reference.
**Step 3:** Manually construct a real `GateVerdict` from a live backend response (once deployed) and confirm the screen correctly shows Stage A only for an S1 action, and both stages for an S3 action with real Critic objections.

---

## WHEN ALL VERIFICATIONS PASS

Update `STATUS_INDEX.md` — the Gate reveal is real; the most distinctive UI moment in this project now has actual code behind it, not just architecture describing one.

Append to `DECISIONS_LOG.md`: the `signed_off` handling decision and why getting it wrong would have mattered, and the real color-palette gap found and closed.

---

*Document version: 1.0 — the eighth of 21 mobile sessions. `MOBILE_09`, the full negotiation screen (agent voices, option cards, computed deltas), is next — the second of this project's two most distinctive real UI moments.*
