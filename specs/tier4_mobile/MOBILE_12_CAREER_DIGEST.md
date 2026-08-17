# MOBILE_12: COMPANY RESEARCH DIGEST
## A fifth real contract gap, and a genuine distinction preserved rather than collapsed into one generic "empty" state

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_DATA_CONTRACTS.md` §5.11, `backend/features/career_digest.py`

**Prerequisites:** `MOBILE_11`.

**Review tier:** STANDARD.

**A fifth real gap, found by the same check applied a fifth time.** `career_digest.py`'s real `compile_digest()` has existed since well before mobile work began; `CompanyDigest` is documented as internal-only, same as `SentMessage` before it. Fixed as §5.11.

**A genuine state-modeling decision, worth explaining rather than leaving implicit.** Reading `career_digest.py` and `MOBILE_09`'s Career agent design together surfaced a real timing fact: digest compilation only happens once a real interview is detected *and* real search findings have actually returned — and those two events don't happen simultaneously. That means a real client can genuinely ask for a digest before one exists. This session treats that as its own honest state (`DigestNotYetAvailableException`, a specific 404), distinct from both a successfully-loaded digest *and* a digest that exists but happens to have zero summary points. Collapsing "doesn't exist yet" and "exists but empty" into one generic empty-state message would tell the user something false about which is actually true — one means "wait," the other means "there's nothing more coming."

**What this session creates:** `mobile/lib/features/career_digest/career_digest_logic.dart` (zero Flutter dependencies), `mobile/lib/features/career_digest/career_digest_screen.dart`, `mobile/test/career_digest_logic_test.dart`.

**Out of scope:** the real `CareerDigestRepository` HTTP implementation — deferred, same injected pattern as every other feature screen.

---

## FILE 1: `mobile/lib/features/career_digest/career_digest_logic.dart` (real, complete — see file)

**The real, three-way state distinction, proven by test, not just designed for.** `hasNoRealContent` correctly flags a digest with a real `CompanyDigestData` but zero summary points — a state that can only be reached if the fetch itself succeeded, distinguishing it structurally from `DigestNotYetAvailableException`, which is a distinct exception type the repository throws instead of ever returning an empty success. Both states are tested independently, confirming they're genuinely two different things in code, not two branches that happen to render the same way.

**Source-count pluralization, the same discipline already established for Waiting On's day count.** Zero, one, and multiple sources each get correct, distinct phrasing.

## FILE 2: `mobile/lib/features/career_digest/career_digest_screen.dart` (real, complete — see file)

Three distinct real UI states, matching the three distinct real data states: content, "still researching" (the honest 404 case), and "researched, found nothing substantial" (the honest empty-success case). No shared generic empty-state widget standing in for two different real meanings.

## FILE 3: real tests (7/7 — see file)

---

## VERIFICATION STEPS (on a real machine — this sandbox cannot run these)

**Step 1:** `dart test test/career_digest_logic_test.dart` → expected: 7 passed.
**Step 2:** `flutter analyze` → confirms the widget file.

---

## WHEN ALL VERIFICATIONS PASS

Update `STATUS_INDEX.md` — the Company Research Digest screen is real; this is the fifth recurring contract gap, and the first one where the fix required genuinely modeling a real timing edge case (not-yet-compiled) as its own state rather than an afterthought.

Append to `DECISIONS_LOG.md`: the three-state distinction and why collapsing it would have misrepresented real system state to the user.

---

*Document version: 1.0 — the twelfth of 21 mobile sessions. `MOBILE_13`, the Finance screen, is next.*
