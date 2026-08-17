# MOBILE_07: TODAY — "IN MOTION" ZONE
## The third and final Today zone, and a second real contract gap found the same way the first one was

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §12.2, `QUORUM_DATA_CONTRACTS.md` §5.4

**Prerequisites:** `MOBILE_06`.

**Review tier:** STANDARD.

**A second real gap, found by applying `MOBILE_05`'s exact discipline again, not assuming it was a one-time catch.** Before writing anything, `QUORUM_DATA_CONTRACTS.md` was checked directly for negotiation-discovery data. It specified `POST /negotiations/{id}/choose` — acting on a negotiation you already know about — but nothing anywhere specified how a client discovers one is active in the first place. Fixed in this session, extending `/today` with a real `in_motion` array, the same pattern as `needs_you_now`. This time, the edit was checked immediately afterward specifically for the F4 source-labeling requirement, since that's exactly what got silently dropped during the equivalent fix in `MOBILE_05` — confirmed still present, not repeated.

**What this session creates:** `mobile/lib/features/today/in_motion_logic.dart` (zero Flutter dependencies, same testability tier as the other two Today zones), `mobile/lib/features/today/in_motion_zone.dart`, `mobile/test/in_motion_logic_test.dart`.

**Out of scope:** the full negotiation interaction — agent voices, option cards, computed deltas — that's `MOBILE_09`. This zone is a summary/preview only, linking into the full screen on tap.

---

## FILE 1: `mobile/lib/features/today/in_motion_logic.dart` (real, complete — see file)

**The conflict-description logic tested against the exact real scenarios the backend already proved, not invented ones.** Before writing the test, the real domain string literals (`"calendar"`, `"finance"`, `"tasks"`) were grepped directly out of `backend/tests/test_negotiation_trigger.py`, confirming this screen's language uses the identical values the backend's own two- and three-domain conflict tests already exercise — not a plausible-looking guess at what the strings might be.

## FILE 2: `mobile/lib/features/today/in_motion_zone.dart` (real, complete — see file)

Deliberately minimal — a summary card per active negotiation, linking into the real interaction screen (`MOBILE_09`) rather than duplicating it here.

## FILE 3: real tests (7/7 — see file)

Includes both the real two-domain and three-domain conflict descriptions, a single-domain edge case (no "vs." separator), and the empty-list fallback.

---

## VERIFICATION STEPS (on a real machine — this sandbox cannot run these)

**Step 1:** `dart test test/in_motion_logic_test.dart` → expected: 7 passed.
**Step 2:** `flutter analyze` → confirms the widget compiles.
**Step 3:** Once `MOBILE_09` exists, confirm tapping a card in this zone navigates to the correct full negotiation screen for that `negotiation_id`.

---

## WHEN ALL VERIFICATIONS PASS

Update `STATUS_INDEX.md` — the Today screen is now complete: all three zones (`MOBILE_05`, `MOBILE_06`, `MOBILE_07`) real. Two real contract gaps found and fixed across those three sessions, both by the same discipline: check the contract directly before building, don't assume it's complete because a related endpoint already exists.

Append to `DECISIONS_LOG.md`: the second `/today` gap, the domain-string cross-check against the real backend test file, and the Today screen's completion as a real milestone.

---

*Document version: 1.0 — the seventh of 21 mobile sessions, and the last of the three Today zones. `MOBILE_08`, the Gate reveal, is next — the first screen surfacing the Gate's actual verification trace.*
