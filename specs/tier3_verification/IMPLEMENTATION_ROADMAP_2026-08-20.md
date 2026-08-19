# QUORUM — Current-State Deep Analysis and Implementation Roadmap

**Prepared:** 2026-08-20. Builds directly on `IMPLEMENTATION_AUDIT_REPORT_2026-08-20.md` (same day) plus new, independent verification performed specifically for this document — see §0.
**Status of this document:** a dated planning snapshot, not a living document. `STATUS_INDEX.md` remains the source of truth for current state; this file is a *plan*, meant to be revisited and re-cut at the start of each real session, not executed unsupervised end to end — consistent with this project's own "one session, explicit approval, then the next" cadence.

---

## 0. What's new here since this morning's audit report

Three findings below were not in the audit report and change its recommended ordering:

1. **The live Cloud Run deployment is stale.** Confirmed by directly curling the real public URL: `GET /tasks` → `404`, `GET /trust` → `404`. The last deploy (`quorum-backend-00003-7lb`) is `DEC-102`'s. Everything from `DEC-106` (`GET /trust`) through `DEC-113` (`DELETE /account`) — nine real, tested backend sessions — has never been redeployed. **This means a real device pointed at the real production URL today cannot reach five of the app's real, tested screens at all**, regardless of anything else being fixed.
2. **Rate limiting is provisioned but unused.** `DEC-010` proved the real Redis key pattern (`ratelimit:*`) locally; nothing in `backend/src` actually calls it. Confirmed by direct search.
3. **Langfuse is provisioned but unused.** Its credentials are live-tested (`DEC-098`); nothing in `backend/src` actually traces a Gate/LLM call through it. Confirmed by direct search.

I also confirmed, by reading `google_oauth.py` directly, that the OAuth scope requested is deliberately narrow (identity only) — no Gmail/Calendar API scope is requested and no Gmail access token is ever persisted. This matters for §2's dependency analysis on Waiting On below.

---

## 1. Verifying and critiquing the pasted plan

Point by point, against what I independently confirmed:

| # | Pasted item | Verdict | Why |
|---|---|---|---|
| 0 | Rotate JWT key + DEC-100 credentials, today, first | **Correct priority, incomplete scope.** | It's right that this goes first — but it needs to be **combined with a redeploy** (finding #1 above), and the two exposure paths are not equally urgent: the JWT default is the more severe one, because it's sitting in this project's own *public* GitHub repo's source code (`main.py`), readable by literally anyone, independent of anything Claude-session-related — while the `DEC-100` exposure is scoped to whoever could see that one chat transcript. Both are cheap to fix; neither should be skipped; but they're not the same severity. |
| 1 | Real demo dataset, then first human E2E run | **Right instinct, wrong granularity.** | Doing this as *one* step risks running the "impressive" demo against a broken home screen (Today has no backend at all) and a stale production deploy (finding #1). §3 below splits this into an early, deliberately minimal *diagnostic* run (catch device-only bugs cheap, before building more on top of them) and a later, full *demo* run (once Today is real and a full dataset exists) — see Phase 2 and Phase 5. |
| 2 | Today screen backend | **Correct, but under-scoped.** | The pasted plan treats this like Track C's endpoints ("wire the backend"). It isn't the same shape of work — `pendingActions`/`negotiations` has **no specified shape anywhere in the spec corpus**, not just an unbuilt endpoint. This needs a real design/schema step before any code, which Track C's items never needed. Flagged explicitly in §3, Phase 3. |
| 3 | Search, Waiting On, Memories, treated as one item | **Needs to be split — these are not comparable-sized tasks.** | I traced each one's real dependency chain (§2). Waiting On is blocked on real Gmail send integration, which doesn't exist and was *deliberately* scoped out of the OAuth work (confirmed above) — this is the deepest, least-scoped gap of the three, not a peer of "add a table." Search needs a net-new embedding-generation pipeline (infra exists, pipeline doesn't). Memories needs an entirely new external service integration from zero. All three are real, but they are not equal effort, and treating them as one line item would make the plan misleading. |
| 4 | The two `DEC-113` nits | **Agree, low priority — but bundle it into the item-0 session rather than leave it a separate future pass.** | Both are small, already fully diagnosed, and cheapest to fix while already touching `account_deletion.py`/`you_screen.dart`-adjacent code, i.e., during the redeploy/security session. |
| 5 | CI/CD hardening, placed last | **Disagree with placement — pull the basic half forward.** | A GitHub Actions job that runs `ruff`+`pytest`+`flutter analyze`+`flutter test` on every PR is cheap, well-scoped, has zero dependency on Today/Search/Memories, and pays for itself on every one of the remaining sessions by catching regressions automatically instead of relying on manually re-running four commands each time. The *full* build→deploy pipeline can stay late (it does depend on the deployment process being settled), but basic PR-gating CI should move to right after item 0. |

Two things the pasted plan didn't surface at all, which I'm adding: the stale-deployment finding (§0.1) and the rate-limiting/Langfuse gaps (§0.2–3). Neither is urgent, but rate limiting specifically is worth doing before any real public demo, since the backend is `--allow-unauthenticated` at the network layer and currently has no protection against a request flood beyond Cloud Run's own `--max-instances=2` hard ceiling (which would just start failing requests, not rate-limit gracefully).

---

## 2. Full state matrix — verified, not assumed

**Fully complete, tested, real:**

| Area | Evidence |
|---|---|
| Router, Gate (all 9 validators + orchestration), 5 domain agents, negotiation pipeline | 151 tests at close, `DEC-072`; re-confirmed present in `backend/src/quorum_backend/{router.py,gate/,agents/,negotiation/}` this session |
| Auth core (access/refresh tokens, PKCE, revocation, theft detection) | CRITICAL-reviewed twice (`DEC-062`, `DEC-101`); real race found and fixed |
| Trace scrubbing, account deletion (code) | `DEC-072`, `DEC-113`; CRITICAL-reviewed |
| Trust, Trust Digest, Tasks, Career Pipeline, Finance/Subscriptions — backend + mobile | `DEC-100`, `DEC-106`–`109`; all real, tested, **but see below — not live in production** |
| User provisioning + per-user data isolation | `DEC-110`, CRITICAL-reviewed |
| Mobile: all 46 original screens, login (PKCE/Google Sign-In), navigation, `flutter analyze`/`flutter test` | 297/297 passing, re-confirmed by me this session |
| Real cloud infra (Supabase, Cloud Run, Upstash, Langfuse, Gemini/Groq/Tavily, Google OAuth) | `DEC-098`, individually live-tested |

**Complete in code, but NOT reflected in the live system — a distinct, real category the log itself never separates out:**

| What | Real gap |
|---|---|
| `GET /trust`, `/tasks`, `/career_pipeline`, `/finance/subscriptions`, `DELETE /account`, real user provisioning | All exist only on `main`, never deployed. Confirmed via live `404`s. |
| The JWT signing key | Code to warn about the default exists (`DEC-097`); no confirmed evidence the *deployed* key was ever set to something real. |

**Partially complete:**

| What | State |
|---|---|
| Today screen | Mobile UI real and composed (`DEC-095`/`096`); zero backend — no schema even specified for `pendingActions`/`negotiations` anywhere in the spec corpus. |
| Negotiation "choose an option" | Screen renders real data; `POST /negotiations/{id}/choose` was never built (`DEC-104` disclosed this explicitly) — a person can see a negotiation but can't act on it. |
| `pii_leak_check` ↔ mobile Privacy Gate | Both sides real independently; never wired together. |
| Sprint 0 / on-device model | Process complete, honest fallback decided (`DEC-111`); no Full-tier candidate has ever actually loaded — capability genuinely unknown, not disproven. |

**Not implemented at all:**

| What | Real blocking dependency |
|---|---|
| Waiting On (backend) | **Blocked on real Gmail send integration**, which doesn't exist and was deliberately scoped out (`google_oauth.py` requests identity-only scope). Building this "properly" means: request Gmail scope → persist Gmail access/refresh tokens (a real, disclosed boundary never crossed, `DEC-101`) → build a real send path through the Email agent → *then* a `sent_messages` table has anything real to populate. A `sent_messages` table alone, without real sends behind it, would be inert. |
| Search (backend) | **Blocked on a net-net embedding-generation pipeline.** `note_embeddings`/`pgvector` infrastructure exists (`DEC-098`); nothing generates or writes an embedding for any real task/expense/application content anywhere in this codebase. The ranking/retrieval logic (`§5.7`'s already-specified contract) is the *smaller* half of this gap; the embedding pipeline is the larger, unbuilt half. |
| Memories (backend) | **Blocked on a real `mem0` integration from zero** — no memory is ever created anywhere in this backend today; `memory_transparency.py` can only read/delete memories that would need to already exist. This is the largest of the three remaining domain gaps: a new external service, a new account/API key, and a real "when does a memory get created" design decision none of the spec corpus answers. |
| Rate limiting on live routes | Infra proven (`DEC-010`), never wired into `main.py`. |
| Langfuse tracing on real Gate calls | Credential live-tested (`DEC-098`), never wired into `gate/orchestration.py`. |
| Real demo dataset | Tracked since `DEC-059`, never built. |
| Full CI/CD (build→test→deploy) | One narrow WIF-auth-proof workflow exists (`DEC-098`); no PR-gating lint/test job, no deploy automation. |

**Needs modification / refinement (working, but with a known, disclosed issue):**

| What | Issue |
|---|---|
| `security/supabase_deletion_store.py` | Purge across two stores isn't fully atomic (`STATUS_INDEX.md` #15) |
| `you_screen.dart` delete flow | No widget test for the error path (`STATUS_INDEX.md` #16) |
| `subscription_detective.py` | Already corrected once (`DEC-112`) — stable, not currently known-wrong, listed here only because it's the module most recently found to have missed a spec |

**Needs testing/verification specifically:**

- A genuine human-completed Google login, on a real device, against a *redeployed* backend — never done.
- A genuine `flutter run` of the main app on a real device/emulator — never done (Sprint 0's separate app did run; the main app never has).
- Whether the live JWT signing key is actually the known default — blocked by this environment's permission boundary, needs direct confirmation.
- Load/concurrency behavior of `--max-instances=2` under real simultaneous requests — never tested.

---

## 3. The roadmap

Ordered by real dependency, not by discovery order. Each phase names what blocks it, what it unblocks, and how to know it's actually done — not just attempted.

### Phase 0 — Security remediation + redeploy (today, one session, ~1–2 hours)

**What:** Generate a real random `JWT_SIGNING_KEY` (e.g., `python -c "import secrets; print(secrets.token_urlsafe(48))"`), rotate it plus the `DEC-100`-exposed credentials (Supabase service key at minimum; the others are lower-urgency but equally cheap — do them all in the same pass), update Cloud Run's env vars, rebuild via Cloud Build, redeploy. While the deployment is already being touched, fold in the two small `DEC-113` nits (the atomicity comment/tracked-limitation write-up is already done; the missing widget test for `you_screen.dart`'s delete error path is a 20-minute add).

**Why it's first:** it's the one item that's both genuinely urgent (public default secret, on a network-open service) and a hard prerequisite for everything downstream that touches a real device — Phase 2's diagnostic run cannot mean anything against a backend that's nine sessions out of date.

**Depends on:** nothing.
**Unblocks:** Phase 2 (needs the real, current backend live), and closes the report's top security finding.
**How to verify done:** re-run this session's own live checks — `curl` the real production URL for `/tasks`/`/trust`/`/account` and confirm they no longer `404`; confirm a freshly-minted token still round-trips through `/auth/token`→`/trust`; confirm `flutter test`/`pytest` are unaffected (pure infra change, zero business logic touched).

### Phase 1 — Basic CI (PR-gating lint + test), in parallel with anything after Phase 0

**What:** One new GitHub Actions workflow: on every PR, run `ruff check backend`, `pytest backend/tests -q` (against a real or a disposable Postgres — needs a decision on which; a disposable service-container Postgres is the lower-risk default so PRs never touch the live Supabase project), `flutter analyze`, `flutter test`.

**Why now, not last:** it's cheap, has zero dependency on any of the remaining feature work, and every session from here on benefits from it catching a regression automatically. Doing it last (as the pasted plan suggested) means every one of Phases 2–6 below runs without this safety net for no real reason.

**Depends on:** nothing beyond Phase 0 being done (don't want CI silently exercising against a service still holding the exposed key).
**Unblocks:** nothing structurally, but de-risks every phase after it.
**Verify:** open a real, throwaway PR with a deliberately failing test; confirm the workflow fails; fix it; confirm green.

### Phase 2 — Diagnostic human end-to-end run (device-only bugs, cheap, before building more)

**What:** On a real Android device or the existing emulator, run the actual main app for the first time ever (`flutter run`), complete a real Google sign-in through the real consent screen, and confirm the already-wired, already-reachable screens (Trust, Tasks — if Today unblocks it, Career Pipeline, Finance, and account deletion via the You tab's "More" section) load real data end to end.

**Why this comes before Today's backend, not after:** the goal here isn't a polished demo — it's catching real, device-only integration bugs (OAuth redirect handling, secure-storage behavior, network config, the custom-scheme callback) as cheaply as possible, before building more screens on top of assumptions that have literally never been exercised on a device. If something's wrong in the login plumbing, you want to find that now, not after also building Today's backend on top of it.

**Depends on:** Phase 0 (a stale or insecure backend makes this run meaningless or misleading).
**Unblocks:** confidence to proceed with Phase 3+ without carrying forward an undiscovered device-level bug.
**Verify:** a real screenshot/log of a successful sign-in and at least one real data screen rendering, plus a note of any bug found — if one is found, it's a real, disclosed fix, same discipline as every other session in this project's history, before moving on.

### Phase 3 — Today screen backend (the app's actual home screen)

**What:** This is design work first, code second — there is no existing spec to build against.
1. Design the real `pendingActions`/`negotiations` schema — check what `TodayScreenData`'s already-built Dart shape (`today_screen.dart`, `MOBILE_22`) actually needs, and what `action_events`/existing Gate output can already supply vs. what genuinely needs new state.
2. Write it into `QUORUM_DATA_CONTRACTS.md` before writing any code (this project's own established discipline — spec, then implement).
3. New migration, new `features/today.py`, new `GET /today` route, mobile wiring.
4. Redeploy.

**Why it matters more than Search/Waiting On/Memories:** it's literally the first screen a person sees. A demo that opens to an empty or broken home screen undercuts every other real, working screen behind it.

**Depends on:** Phase 0 (redeploy pipeline already exercised once, lower-risk to repeat), ideally after Phase 2 (so the schema design isn't done blind to whatever the diagnostic run surfaced about how Today's data actually needs to look on a real screen).
**Unblocks:** a meaningful Phase 5 demo run; Phase 2's diagnostic run's blocked-on-Today items (`fetchTasks`'s drill-through link, `DEC-107`'s own disclosed gap).
**Verify:** live-DB tests mirroring the Track C pattern (insert/query/delete, cross-user isolation — this domain touches per-user data too, so `DEC-110`'s provisioning work applies here from day one, not retrofitted later), then a real device check that the home screen actually renders real content.

### Phase 4 — Search, Waiting On, Memories — NOT one task, sequenced by real dependency depth

Do these in this order, and treat them as three separate efforts, not a shared sprint:

**4a. Search first** (smallest real gap): build a minimal embedding-generation step (on task/expense/application creation or via a batch job, call the already-provisioned embedding model and write to `note_embeddings`), then the already-specified `/search` ranking endpoint. This is the only one of the three whose infrastructure prerequisite (pgvector, the embedding model choice) is already fully resolved — it's genuinely just missing code, not missing design decisions.

**4b. Memories second**: requires a real `mem0` account/integration decision first (hosted vs. self-hosted, what triggers memory creation — this needs your input, it's a real product decision, not a technical one I should make unilaterally) before any code. Once decided, wire memory creation into wherever it makes sense (likely agent-side, when an agent learns a real, durable preference), then the read/delete endpoints `memory_transparency.py` already has are ready to serve real data immediately.

**4c. Waiting On last, and flag it honestly as the deepest gap**: real value here requires actually sending real email through the Email agent, which requires expanding the OAuth scope and persisting Gmail tokens — a real, deliberate boundary this project has held since `IMPL_12`. This is arguably its own multi-session effort (OAuth scope expansion + token persistence + real send integration + the tracking table), not a small addition. Worth an explicit go/no-go conversation before starting: is real Gmail sending actually in scope for this portfolio project, or is a lighter-weight "track pending replies from data already in Quorum's own system" version sufficient? I'd recommend the lighter version unless real Gmail sending is something you specifically want to demo — it avoids a large, real OAuth-scope expansion for a feature whose main value (surfacing what you're still waiting to hear back on) doesn't strictly require Quorum to have sent the email itself, only to know a reply is expected.

**Depends on:** Phase 3 pattern (per-user data isolation from day one, not retrofitted).
**Verify:** each domain gets its own live-DB test suite plus a real device check, same bar as every other domain endpoint before it.

### Phase 5 — Full demo dataset + polished human end-to-end run

**What:** Now that Today, and whichever of Search/Memories/Waiting On landed, are real, build the actual "simulated-and-real hybrid, all five domains" dataset this project has tracked as an open item since `DEC-059`, load it against the real, live database, and do the *demonstration-quality* device run — the one actually worth showing an interviewer.

**Depends on:** Phase 3 at minimum; Phase 4's items to whatever extent you choose to build them.
**Verify:** a real recording or live walkthrough covering sign-in → Today → at least one negotiation or Gate reveal → account deletion's real confirmation counts. This is the actual "is this project done" checkpoint, not a test suite passing.

### Phase 6 — Production hardening (rate limiting, Langfuse tracing, full CI/CD)

**What:** Wire the already-provisioned Redis rate-limit pattern into `main.py`'s routes; wire Langfuse tracing into `gate/orchestration.py`'s real LLM calls (this also gives you real, live cost/latency data worth having for its own sake); extend Phase 1's basic CI into a real build→test→deploy pipeline.

**Why last:** none of it blocks a demo being real and working; all of it is genuine, disclosed, non-blocking "production-shaped, not yet production-hardened" work — exactly the category `STATUS_INDEX.md`'s own open items already describe it as.

**Depends on:** nothing structurally beyond Phase 0; placed last because it has the least payoff-per-effort relative to Phases 2–5 for a portfolio project's actual goal.
**Verify:** a deliberate flood of requests against a non-production test deployment confirms rate limiting actually engages; a real Gate call shows up in the Langfuse dashboard; a full push-to-`main` triggers an automatic, real deploy and you can point to it as evidence of a genuinely production-shaped pipeline.

---

## 4. Dependency graph (text form)

```
Phase 0 (security + redeploy)
  ├─→ Phase 1 (CI)              [parallel with everything below]
  └─→ Phase 2 (diagnostic E2E run)
        └─→ Phase 3 (Today backend)
              └─→ Phase 4a (Search)
              └─→ Phase 4b (Memories)  [needs your product decision first]
              └─→ Phase 4c (Waiting On)  [needs your scope decision first — see 4c]
                    └─→ Phase 5 (demo dataset + polished E2E run)
                          └─→ Phase 6 (rate limiting, tracing, full CI/CD)
```

Phase 1 is the only phase genuinely parallel to the main chain. 4a/4b/4c can run in any relative order among themselves (I've sequenced by dependency depth, not by a required order) or in parallel across sessions if you want to move faster — they don't depend on each other, only on Phase 3's per-user-isolation pattern already existing.

---

## 5. Two decisions only you can make, before Phase 4 specifically

1. **Memories:** hosted `mem0` vs. self-hosted, and what should actually trigger a memory being created.
2. **Waiting On:** real Gmail sending in scope for this project, or a lighter version that doesn't require expanding the OAuth boundary this project has deliberately held since `IMPL_12`.

Everything else in this roadmap I'm confident enough in to proceed on your go-ahead without further input.
