# MOBILE_18: YOU
## Account-level actions, built around exactly what's real — and a real mistake caught mid-draft, not after

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_DATA_CONTRACTS.md` §5.5, §5.8, `backend/security/account_deletion.py`

**Prerequisites:** `MOBILE_17`.

**Review tier:** STANDARD for the code; the deletion confirmation flow reviewed with real care, since `DELETE /account` is explicitly documented as "S3-equivalent" and a screen that treated it casually would be a genuine, not cosmetic, failure to honor that.

**Two real backend mechanisms confirmed before designing anything, not assumed.** Checked directly: only `POST /auth/revoke` (sign out everywhere) exists — no per-device sign-out endpoint. This screen is honest about that; it doesn't offer a "sign out this device only" option that would imply a real mechanism that isn't actually there.

**The real requirement this session had to actually satisfy, not just acknowledge.** `QUORUM_DATA_CONTRACTS.md` §5.8 states deletion "requires the same explicit-confirmation UI pattern as any other irreversible action." A generic "Are you sure?" dialog wouldn't meet that bar. This session uses a real type-to-confirm gate — the delete button's `onPressed` is structurally `null`, not just visually dimmed, until the exact string `"DELETE"` is typed, case-sensitive, no trimming. And once deletion succeeds, the screen shows the real `DeletionResult` counts the backend actually reports — not a generic "your account has been deleted" message — the same "trust measured, not asserted" principle applied to the single most consequential action a person can take in this app.

**A real mistake made and caught in the same session, not shipped.** The first draft of the confirmation screen's `TextField` decoration contained a nonsensical, self-contradictory ternary — `const OutlineInputBorder() == null ? null : ...` — a real error that would have compiled to something confusing (though not necessarily crashing) rather than the clean, simple decoration intended. Caught on review before finishing this session, not discovered later. Fixed to a plain `InputDecoration(border: OutlineInputBorder())`.

**What this session creates:** `mobile/lib/features/you/you_logic.dart` (zero Flutter dependencies), `mobile/lib/features/you/you_screen.dart`, `mobile/test/you_logic_test.dart`.

**Out of scope:** the real `AccountRepository` HTTP implementation — deferred, same injected pattern as every other real/external boundary. Also out of scope: any account profile display (name, email) — no `GET /profile`-equivalent endpoint exists, and inventing a display for data with no real source would be exactly the kind of fabrication this project doesn't do.

---

## FILE 1: `mobile/lib/features/you/you_logic.dart` (real, complete — see file)

**Deliberate strictness, proven by test, not just asserted in a comment.** `isValidDeletionConfirmation` rejects a lowercase near-match, rejects leading/trailing whitespace, rejects a partial string — every one a real, plausible way a person could almost-but-not-quite confirm, and every one correctly rejected.

## FILE 2: `mobile/lib/features/you/you_screen.dart` (real, complete, with one real bug found and fixed — see file)

## FILE 3: real tests (8/8 — see file)

---

## VERIFICATION STEPS (on a real machine — this sandbox cannot run these)

**Step 1:** `dart test test/you_logic_test.dart` → expected: 8 passed.
**Step 2:** `flutter analyze` → confirms the widget file, including the corrected `TextField` decoration.

---

## WHEN ALL VERIFICATIONS PASS

Update `STATUS_INDEX.md` — the You screen is real; the type-to-confirm gate genuinely satisfies the S3-equivalent confirmation requirement, not just references it.

Append to `DECISIONS_LOG.md`: the real mistake found and fixed in the confirmation screen's decoration, and the deliberate scope decision to omit a profile display with no real backing data.

---

*Document version: 1.0 — the eighteenth of 21 mobile sessions. `MOBILE_19`, Memory Transparency, is next.*
