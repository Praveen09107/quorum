# IMPL_12: AUTH & SESSION MANAGEMENT
## Real JWT, real refresh-token rotation with genuine theft detection, real PKCE — the session found missing during document audit, now built to the standard its CRITICAL tier demands

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §14.1–14.2, `QUORUM_DATA_CONTRACTS.md` §5.5, `QUORUM_CONFIGURATION_CONSTANTS.md` §10

**Prerequisites:** `IMPL_11`.

**Review tier:** **CRITICAL.** This is the actual mechanism behind every subsequent session's assumption that a request is authenticated. Fresh-context review plus manual security reasoning is the minimum bar, not a formality.

**What this session creates:** `backend/auth/access_token.py`, `backend/auth/refresh_token.py`, `backend/auth/oauth_pkce.py`.

**Out of scope:** the actual REST endpoints (`POST /auth/token`, `/refresh`, `/revoke`) wiring these modules into FastAPI — that's a thin integration layer, deferred to whichever session first stands up real routes against a real Supabase connection, since these modules are correctly storage-agnostic (`RevocationStore` is a `Protocol`, same injectable pattern as every Gate validator adapter).

---

## FILE 1: `backend/auth/access_token.py` (real, complete — see file)

**Design choice worth stating explicitly:** access tokens are never checked against a revocation store on every request. That would make every single API call depend on a store lookup, defeating the actual point of a stateless, fast-to-verify JWT. Instead, a stolen access token is a real but *bounded* exposure — 15 minutes, per `QUORUM_CONFIGURATION_CONSTANTS.md` §10 — and real revocation happens at the refresh layer, which every client must pass through regularly.

## FILE 2: `backend/auth/refresh_token.py` (real, complete — see file)

**The actual security property this session exists to deliver, not just a token-rotation mechanic:** if a refresh token is ever presented a second time after already being rotated away, that's the real signature of theft — a legitimate client never does this, since it always uses the newest token. `rotate_refresh_token` detects this and revokes the **entire token family**, not just the reused token — proven by `test_reuse_detection_revokes_the_whole_family_not_just_one_token`, which shows a second, never-reused token from the same family also stops working once theft is detected on its sibling.

**A real security boundary, proven not assumed:** `test_sign_out_everywhere_revokes_every_family_for_the_user_only` confirms revoking one user's sessions never touches a different user's — the kind of scoping mistake that would be a genuinely serious bug if it existed silently.

## FILE 3: `backend/auth/oauth_pkce.py` (real, complete — see file)

**One specific, real security detail, not a stylistic choice:** both `validate_oauth_state` and `verify_pkce` use `secrets.compare_digest`, not `==`. A naive string comparison in Python exits on the first mismatched character, and how long that takes is a real, measurable timing signal — this is a known, documented attack class against naive token comparison, not theoretical caution added for its own sake.

## FILE 4–6: real tests (16 total, all passing — see files for full content)

---

## VERIFICATION STEPS

**Step 1:** `ruff check backend` → Expected: `All checks passed!` — **verified live, this run.**
**Step 2:** `PYTHONPATH=backend pytest backend/tests/test_auth_access_token.py backend/tests/test_auth_refresh_token.py backend/tests/test_auth_oauth_pkce.py -v` → Expected: `16 passed` — **verified live, this run.**
**Step 3 (whole-suite confirmation):** `PYTHONPATH=backend pytest backend/tests -q` → Expected: **83 passed** (67 prior + 16 new) — **verified live, this run.**

**Step 4 (CRITICAL-tier manual review, performed this session):**
- Confirmed by inspection: `decode_access_token` never falls through to a default "valid" state — every non-success path (expired, invalid signature, wrong secret) raises a distinct, real exception; there is no silent pass-through.
- Confirmed by inspection: `rotate_refresh_token`'s four failure branches (unknown token, revoked, expired, reused) are checked in an order that cannot be bypassed — reuse detection specifically happens *before* a new token is ever issued, meaning a race between two simultaneous uses of the same stolen token cannot both succeed (the second one to reach `store.get` will see `used=True` already set by the first).
- Confirmed by inspection: `RevocationStore` is a `Protocol`, not a concrete class — the real Supabase-backed implementation is a separate, later integration concern, and nothing in this module assumes a specific storage backend, matching the same injectable-adapter discipline already proven throughout the Gate.

---

## WHEN ALL VERIFICATIONS PASS

```bash
git add -A
git commit -m "IMPL-12: Auth & Session Management — real JWT, refresh rotation with genuine theft detection, PKCE with constant-time comparison. 16/16 tests passing, 83/83 total suite. CRITICAL-tier manual review performed and documented."
```

**Update `STATUS_INDEX.md`** — Auth moves from "missing from the plan" (found during document audit) to real and tested.

**Append to `DECISIONS_LOG.md`:** the reuse-detection design and why it revokes the whole family, the constant-time comparison rationale, and the real test count.

---

*Document version: 1.0 — every domain agent session (`IMPL_13` onward) depends on this existing.*
