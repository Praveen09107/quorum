# IMPL_22: TRACE-SCRUBBING + DELETE-ACCOUNT
## The last backend session — and the entire backend decision-making core is now real

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §14.6–14.7, `QUORUM_CONFIGURATION_CONSTANTS.md` §10.1

**Prerequisites:** `IMPL_12` (needs the real `revoke_all_for_user`).

**Review tier:** STANDARD for trace-scrubbing; the account-deletion path touches real user data destruction, reviewed with the same care as Auth itself, though it composes entirely from already-CRITICAL-reviewed logic rather than introducing new security-sensitive code.

**A real gap closed before any code was written:** the ADD requires trace-scrubbing to reuse "the Privacy Gate's own rule-layer detectors... not a separately maintained pattern set" — but the Privacy Gate (`MOBILE_03`) doesn't exist yet, and it's Dart, not Python; the two can never literally share code. The real fix: `QUORUM_CONFIGURATION_CONSTANTS.md` §10.1 now holds the actual pattern definitions as the single source of truth, with `MOBILE_03` explicitly required to match this table exactly when it's built, rather than each platform inventing its own list that could quietly drift apart.

**What this session creates:** `backend/security/trace_scrubbing.py`, `backend/security/account_deletion.py`; adds §10.1 to `QUORUM_CONFIGURATION_CONSTANTS.md`.

**Out of scope:** the real Postgres/pgvector/mem0 deletion queries themselves — `DeletionStore` is injected, same real/external boundary pattern as everywhere else in this project.

---

## FILE 1: `backend/security/trace_scrubbing.py` (real, complete — see file)

**A real behavior confirmed rather than assumed:** the OTP pattern captures a group, but since the replacement string doesn't reference it, the *entire* matched phrase — "OTP: 482913," not just the digits — gets replaced. `test_otp_code_is_redacted_including_the_full_labeled_phrase` checks this exact, sometimes-surprising regex behavior directly, rather than trusting it from reading the pattern alone.

## FILE 2: `backend/security/account_deletion.py` (real, complete — see file)

**Deliberately reuses, rather than reimplements, already-CRITICAL-reviewed logic.** Session revocation calls `IMPL_12`'s real `revoke_all_for_user` directly — the exact same "sign out everywhere" mechanism, applied here because the account no longer exists at all, not duplicated as separate deletion-specific revocation code that could drift from the original's correctness.

**The same boundary discipline already proven for domain authorization, applied here too.** `test_deleting_one_user_never_touches_a_different_users_real_session` is the account-deletion equivalent of the five-domain authorization matrix — a real, live proof that a second user's session keeps working after a different user's account is deleted, not an assumption inherited from `revoke_all_for_user`'s own tests alone.

## FILE 3: `QUORUM_CONFIGURATION_CONSTANTS.md` §10.1 (new)

The shared pattern table — real regexes, not placeholders, with an explicit requirement that `MOBILE_03` match them exactly.

## FILE 4–5: real tests (5/5 + 3/3 passing — see files)

---

## VERIFICATION STEPS

**Step 1:** `ruff check backend` → `All checks passed!` — **verified live.**
**Step 2:** `PYTHONPATH=backend pytest backend/tests/test_trace_scrubbing.py backend/tests/test_account_deletion.py -v` → `8 passed` — **verified live.**
**Step 3 (whole-suite confirmation — the entire backend):** `PYTHONPATH=backend pytest backend/tests -q` → Expected: **143 passed** (135 prior + 8 new) — **verified live, this run.**

---

## WHEN ALL VERIFICATIONS PASS

```bash
git add -A
git commit -m "IMPL-22: Trace-scrubbing + delete-account. Shared pattern table established as single source of truth ahead of MOBILE_03. Delete-account reuses IMPL_12's revoke_all_for_user rather than reimplementing it. 8/8 tests passing, 143/143 total suite. THE ENTIRE BACKEND IS NOW REAL."
```

**Update `STATUS_INDEX.md`** — the backend decision-making core (Router, Gate — all 9 validators + orchestration, all 5 domain agents, negotiation, auth, trace-scrubbing, account deletion) is entirely complete. The mobile sequence (`MOBILE_01` onward) begins next.

**Append to `DECISIONS_LOG.md`:** the shared pattern table as the real fix for the "not separately maintained" requirement, and the milestone — every backend session in the original 23-session plan is now real.

---

*Document version: 1.0 — the last backend session. `MOBILE_01`, the Flutter scaffold, is next: the first mobile session, and the first genuinely new platform this project touches.*
