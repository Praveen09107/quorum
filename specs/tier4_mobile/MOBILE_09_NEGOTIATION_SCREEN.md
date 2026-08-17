# MOBILE_09: THE FULL NEGOTIATION SCREEN
## Agent voices, option cards, computed deltas — and a deliberate absence worth naming explicitly

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §8, §12, `backend/gate/schemas.py` (`Position`, `NegotiationOption`, `ImpactDelta`)

**Prerequisites:** `MOBILE_08`.

**Review tier:** STANDARD.

**Three real schemas, all confirmed directly before writing anything, not from memory of having designed them across earlier sessions.** `Position`'s real fields (`domain`, `concern`, `proposed_resolution`), `NegotiationOption`'s closed `option_id` set, and `ImpactDelta`'s three real fields (`metric`, `before`, `after`, `direction`) — all grepped directly out of `backend/gate/schemas.py` first.

**A deliberate absence, worth stating explicitly rather than leaving unexplained:** there is no "recommended option" logic anywhere in this session's code. Every option renders with identical visual weight — same card style, same button styling, no badge, no highlight, no ordering bias. This is the concrete implementation of the neutral-disclosure principle that's been part of this project's design since negotiation was first specified: the numbers are shown, the choice is genuinely the user's, and nothing in this screen nudges toward one option over another.

**What this session creates:** `mobile/lib/features/negotiation/negotiation_logic.dart` (zero Flutter dependencies), `mobile/lib/features/negotiation/negotiation_screen.dart`, `mobile/test/negotiation_logic_test.dart`.

**Out of scope:** wiring `onChoose` to a real `POST /negotiations/{id}/choose` call — the screen is built to receive real data and emit a callback, same injected pattern as every other real/external boundary in this project.

---

## FILE 1: `mobile/lib/features/negotiation/negotiation_logic.dart` (real, complete — see file)

**Unit-correctness, not generic number formatting, proven by test.** `formatMetricValue` renders `deadline_slack_hours` and `task_hours_committed` with an "h" suffix but `budget_remaining_fraction` as a percentage — getting this wrong (showing a 0.25 fraction as "0.3h") would misrepresent a real number the backend's impact simulator (`IMPL_20`) specifically exists to guarantee is accurate. The rounding boundary at 0.999 → 100% was hand-verified in Python before being trusted in a test, the same discipline applied to every prior mobile session's trickiest arithmetic.

## FILE 2: `mobile/lib/features/negotiation/negotiation_screen.dart` (real, complete — see file)

**Agent voices, rendered as genuinely distinct entries, not a single merged summary.** Each conflicted domain's real `Position` — its concern and its own proposed resolution — gets its own card, preserving the actual multi-agent structure rather than collapsing it into one paragraph a person can't attribute to any specific domain.

**Every delta rendered with a real before → after value, never just a direction arrow alone.** The arrow (improves/worsens/unchanged) is a fast visual signal, but the actual numbers are always shown alongside it — matching the "the numbers are reproducible, only the narration is generative" principle: this screen never asks the user to trust a symbol over the number backing it.

## FILE 3: real tests (13/13 — see file)

---

## VERIFICATION STEPS (on a real machine — this sandbox cannot run these)

**Step 1:** `dart test test/negotiation_logic_test.dart` → expected: 13 passed.
**Step 2:** `flutter analyze` → confirms the widget file.
**Step 3:** Manually construct a real negotiation response (matching `IMPL_21`'s subgraph output shape) and confirm the screen renders every position and every option's deltas correctly, with visually identical option-card treatment across all three.

---

## WHEN ALL VERIFICATIONS PASS

Update `STATUS_INDEX.md` — the negotiation screen is real. Both of this project's most distinctive UI moments (the Gate reveal, `MOBILE_08`, and this one) now exist as actual code.

Append to `DECISIONS_LOG.md`: the deliberate absence of recommendation logic, stated as a real design decision rather than an oversight, and the unit-correctness proof.

---

*Document version: 1.0 — the ninth of 21 mobile sessions. `MOBILE_10` begins the remaining feature screens (Waiting On, Career pipeline, and onward) — the two most architecturally significant mobile screens are now both real.*
