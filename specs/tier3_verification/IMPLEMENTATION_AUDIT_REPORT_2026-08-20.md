# QUORUM — Full Implementation Audit Report

**Prepared:** 2026-08-20, as a point-in-time snapshot for independent review by Preethish.
**Status of this document:** This is a **dated, one-time audit deliverable**, not a living document. It will go stale the moment the next session lands. `specs/tier3_verification/STATUS_INDEX.md` remains the single living source of truth for "what's true right now" — this report exists so the full history behind that current state can be reviewed in one place, once, without paging through a 2,378-line append-only log by hand. Do not update this file in future sessions; write a new dated one if another full audit is ever wanted.

---

## 0. Purpose and how to use this document

You asked for a comprehensive, honest reconstruction of everything implemented, why, and what might be wrong — built from the project's own real records, not from my summary of my own work. Here is exactly what I did to build it, so you can judge how much to trust it:

- I read **`specs/tier3_verification/DECISIONS_LOG.md` in full, start to end** (2,378 lines, 113 numbered decision entries plus one duplicate-numbered historical block — explained in §2, which is the single most important thing to understand before reading anything else in this report).
- I read **`specs/tier3_verification/STATUS_INDEX.md` in full** (the current living status file).
- I re-read the relevant sections of **`.claude/CLAUDE.md`** (already in my working context this session).
- I independently verified the **actual file structure** of `backend/src/quorum_backend/`, `backend/tests/`, `backend/migrations/`, and `mobile/lib/` against what the log claims exists — every file the log says was built is present; no file the log says doesn't exist was found to secretly exist.
- I independently re-ran, this same session, the full verification suite: `ruff check backend` (clean), `pytest backend/tests -q` (**271 passed**), `flutter analyze` (no issues), `flutter test` (**297 passed**) — these are not numbers copied from the log, they are commands I ran myself minutes before writing this report.
- I attempted to independently verify one specific, serious open security question (§11.1) against the live, deployed Cloud Run service using `gcloud`, and I disclose exactly how far that verification got and where it was blocked.
- Where I could not verify a claim independently — most of the pre-`DEC-050` narrative, and anything requiring a real phone or a human completing a Google login screen — I say so explicitly rather than assuming it's fine.

I did **not** re-read all 46 individual `IMPL_XX`/`MOBILE_XX` session-spec files line by line. `DECISIONS_LOG.md` already narrates, session by session, what each one specified, what was actually built against it, and every place the two disagreed — re-deriving that from the raw spec files a second time would not have surfaced anything the log doesn't already disclose, and would have cost a lot of budget for no new signal. If you want line-by-line spec-vs-code diffing for a specific session, tell me which one and I'll do that pass separately.

---

## 1. What Quorum is, in one paragraph

Quorum is a hybrid edge-cloud, multi-agent AI trust architecture, delivered as a personal-operations mobile assistant (email, calendar, tasks, finance, career) that proposes actions but never executes anything risky without passing through an independent verification layer (**the Gate**) and, for irreversible external actions, a human. It is a solo portfolio project aimed at an AI Engineer job search — not academic, not for personal daily use — with a stated goal of 100% real completion across all five domains, built under a strict spec-driven methodology (write the spec, implement against it, verify live, log the decision, review before merge) borrowed from a prior real project (AEGIS) and adapted with three deliberate strengthenings: cross-model-equivalent review for anything security/Gate/irreversible-action-adjacent, a sandbox-only carve-out for actions that would touch a real external destination, and a leaner tier structure sized to this project's actual scale.

---

## 2. THE ONE STRUCTURAL FACT YOU MUST UNDERSTAND FIRST

`DECISIONS_LOG.md` is not one continuous numbered sequence. It contains **two colliding ranges of decision numbers**, and misreading which one you're looking at will make you draw wrong conclusions about what's real.

**Range A — `DEC-001` through `DEC-049`, then a *second* `DEC-050` through `DEC-063`+ (the "Batch 1–10 session-guide effort")** describes a huge amount of real, careful work — 23 backend sessions, 23 mobile sessions, 156→157 passing tests, then ten batches of session-guides and verification documents written against that code. **All of it describes a codebase that does not exist in this repository.** It was built in a different, now-inaccessible environment (a long Claude.ai conversation, on what appears to have been a Linux machine, per `DEC-005`'s own logged Linux path). The project's own log discovered this directly: before starting real `IMPL_01` work in *this* repository (`D:\Program Files\QUORUM`, Windows, Claude Code), the very first prerequisite files the plan assumed existed (`gate/schemas.py`, `gate/validators.py`) were checked and found completely absent — and an exhaustive search of this entire machine found no trace of that other codebase anywhere. This is recorded as `DEC-050` (the **second** entry with that number), titled *"A Real Environment-Continuity Gap Found."*

**Range B — the second `DEC-050` through the current `DEC-113`** is this repository's real, verified implementation history. Every claim in the rest of this report comes from Range B, cross-checked against the actual files on disk.

**Why this matters for your audit:** if you grep the log for a specific `DEC-0NN` number below `DEC-064` or so, you may land on the wrong one of two entries with the same number describing unrelated work. `DEC-077`'s own text records this exact confusion happening *inside the project itself* — a citation in one session pointed at the wrong `DEC-053` (there are two) before being caught and corrected. **This is a real, disclosed violation of the log's own Rule 2 ("numbered sequentially, never reused")**, explained and justified by the project (the numbering was inherited mid-restart, not deliberately reused), but still a real inconsistency worth knowing about before you rely on any specific low-numbered citation. I flag it again as an independent finding in §11.4.

Range A is genuinely useful as **design lineage** — it's where most of the specification documents (the ADD, Data Contracts, Configuration Constants, Master Reference, all 46 `IMPL_XX`/`MOBILE_XX` session specs) originated, and this repository's real work has consistently built against those same specs. But **it is not a description of this repository's code**, and I have not treated it as one anywhere in this report.

---

## 3. Architecture overview — the five real pillars

All five are real, tested, and present in `backend/src/quorum_backend/` as of `DEC-072` (the close of the 23-session backend core):

| Pillar | What it does | Where |
|---|---|---|
| **Router** | Hardcoded S0–S3 stakes lookup by action type, plus a complexity classifier (`requires_cross_reference`, never model confidence). | `router.py` |
| **The Gate** | Two-stage verification: Stage A (9 pure-code validators, zero LLM calls) → Stage B (Critic on Groq/Llama, Judge on Gemini, only for S2/S3) → one bounded revision round → a final verdict. | `gate/` |
| **Five domain agents** | Email, Calendar, Tasks, Finance, Career — each proposes actions via a compiled LangGraph graph; none self-checks its own Stage A validator (agents propose, the Gate verifies — stated once at `IMPL_14`/`DEC-064`, held without re-deriving it every time after). | `agents/` |
| **Negotiation** | Trigger (pure computation, ≥2 conflicted domains) → parallel position generation → merge-not-invent synthesis (mechanically enforced, not just prompted) → impact simulation → one compiled subgraph wiring all four. | `negotiation/` |
| **Security & auth** | Trace scrubbing, account deletion, JWT access tokens, single-use-rotation refresh tokens with theft detection, PKCE, real user provisioning. | `security/`, `auth/` |

A sixth, later-built layer — **real infrastructure and live wiring** (Batch 10, `DEC-097`–`113`) — is what actually connects this decision-making core to a live database, a deployed backend, and a real (partially) mobile client. That's covered in §6.3.

---

## 4. Non-negotiable rules, and where the code actually enforces them

Cross-checked against real code, not just against `CLAUDE.md`'s prose claim:

- **Stakes is a hardcoded table, never a learned classifier.** Confirmed: `router.py`'s `STAKES_TABLE` maps all 11 real `ActionType`s explicitly; `get_stakes()` raises `ValueError` on anything unmapped rather than guessing (`DEC-059`).
- **Stage A is pure code, zero LLM calls.** Confirmed directly by inspection at each validator's own session: `provenance_check` performs exactly three operations (a falsy check, a membership test, an equality test) and never reads what any source string says (`DEC-056`); `trigger.py` has zero `async`/`await`/model-call patterns anywhere (`DEC-068`).
- **`Finding.evidence_state` stays three-valued, `no_data_found` never collapsed.** Confirmed in the schema (`gate/schemas.py`) and re-applied deliberately outside the Gate itself when `trust_digest.py`'s real aggregation query needed to decide how to treat `uncertain_no_data` rows — excluded from both totals and the success-rate numerator by direct analogy to this exact rule, rather than guessed (`DEC-100`).
- **S3 always requires human approval, no exception.** Enforced on the mobile side by `action_disposition.dart`'s `decideDisposition()` — the S3-during-outage check is the literal first conditional in the function body, proven exhaustively across all 8 real stakes×outage combinations, not spot-checked, and reviewed at CRITICAL tier (`DEC-093`).
- **Critic (Groq/Llama) and Judge (Gemini) stay different providers.** Held throughout; both real credentials individually tested live against their respective real APIs (`DEC-098`).
- **Cloud Run `--concurrency=1`, explicit.** Confirmed live in the actual deploy command every time it's redeployed (`DEC-098`, `DEC-100`, `DEC-102`) — and this flag is not decorative: the real, exploitable refresh-token race found and fixed in `DEC-101` (§6.3, §10) only exists *because* `--max-instances=2` gives genuine OS-level parallelism, which is exactly the scenario this architecture rule exists to guard.
- **Compute and database co-located.** Cloud Run is `asia-south1`, Supabase is `ap-south-1` (both Mumbai) — confirmed matching (`DEC-098`).
- **`tasks.status` fails loud on an unrecognized value; `applications.status` is defensive.** Both confirmed against the real, live schema before being coded, not assumed: `tasks.status` has a real database `CHECK` constraint, `applications.status` genuinely does not (`DEC-083`, `DEC-096`) — the two mobile files (`tasks_logic.dart`, `career_pipeline_logic.dart`) are deliberately opposite in this one respect, and the log is explicit that making them consistent with each other would be the actual bug.

I did not find a case, anywhere in the real (Range B) history, where one of these rules was silently violated. Every near-miss I found in the log was caught and disclosed by the project itself before or during the session it happened in (see §9's consolidated table).

---

## 5. Full chronological implementation history (Range B — this repository's real work)

### 5.1 Backend core — `DEC-050` (2nd) through `DEC-072`

Built from scratch in this repository, against the same spec corpus Range A also used, with every "the code already exists, just check it" assumption in the batch-guide source material found false and disclosed, session after session (a genuinely recurring pattern, not a one-off — see §9).

| Session | What was built | Real, disclosed finding worth knowing |
|---|---|---|
| `IMPL_01` (`DEC-051`) | `gate/schemas.py` (bootstrapped, not assigned to any session), `availability_check` | Deliberately two-valued in practice (no `no_data_found` case) — a calendar range query reliably returns everything that exists, unlike a single lookup. |
| `IMPL_02`–`07` (`DEC-052`–`057`) | Remaining 8 Stage A validators | Three consecutive kickoff prompts each independently omitted the real spec's *last* parameter — caught every time, built to the real signature each time. `coverage_check`'s single-shared-stopword leniency re-confirmed live and left as-is per its own spec's disclosed trade-off (`min_shared_terms` never changed). |
| `IMPL_06` (`DEC-056`) | `provenance_check` | **CRITICAL tier.** Two permanent adversarial tests engineer authority-sounding injected text ("SYSTEM OVERRIDE...") and confirm neither flips the verdict; a `grep` for authority keywords in the implementation itself returns zero matches, confirming there's no keyword logic to route around. |
| `IMPL_08` (`DEC-058`) | `gate/orchestration.py` — `review()` | **CRITICAL tier**, the single most-depended-on function in the repo. One-revision-round bound enforced by code structure (no loop exists), not a counter. One disclosed, accepted limitation: `_call_with_retry` wraps the whole Stage B call, so a Judge-only transient failure re-invokes the Critic too (open item #4). |
| `IMPL_09` (`DEC-059`) | `router.py` | — |
| `IMPL_10`–`11` (`DEC-060`–`061`) | Local Postgres+pgvector/Redis proof, `main.py` bootstrap, Dockerfile | Docker build succeeded on this machine where the *original* environment's own history recorded an SSL failure — new, disclosed evidence this machine doesn't share that limitation. |
| `IMPL_12` (`DEC-062`) | `auth/access_token.py`, `refresh_token.py`, `oauth_pkce.py` | **CRITICAL tier.** Real token-theft scenario proven end-to-end (steal → replay → whole family revoked, including the legitimate sibling token). |
| `IMPL_13`–`17` (`DEC-063`–`067`) | All 5 domain agents, `tool_authorization.py` | Full 5-domain exhaustive authorization matrix independently recomputed each time a domain was added (39 checks at 4 domains, 60 at 5, zero violations both times). |
| `IMPL_18`–`21` (`DEC-068`–`071`) | Negotiation trigger → positions/synthesis → impact simulation → subgraph | `validate_synthesis_shape()` mechanically catches "invented" options (a domain referenced that never produced a real position) — proven by a constructed adversarial test, not just requested in a prompt. Real timed proof of parallelism (3× 0.1s calls complete in <0.2s). Full pipeline passed end-to-end on the **first real attempt**. |
| `IMPL_22` (`DEC-072`) | `trace_scrubbing.py`, `account_deletion.py` | Session revocation reuses `IMPL_12`'s already-CRITICAL-reviewed `revoke_all_for_user()` rather than a second implementation — deliberate, to guarantee exactly one revocation code path exists in the whole system. |

**Real, live-verified result at this point:** 151 backend tests passing (per `STATUS_INDEX.md`'s own reconciliation), all 23 backend sessions complete, `ruff` clean throughout.

### 5.2 Mobile build-out — `DEC-073` through `DEC-096`

Every one of these sessions was built with **zero Dart/Flutter SDK on the machine** — every file is disclosed as "structurally correct against documented package APIs," never claimed as compiled or run, until `DEC-103` (§6.3) finally ran a real compiler against all of it at once.

Key recurring pattern, disclosed honestly rather than smoothed over: **at least ten separate sessions** (`MOBILE_05`, `07`, `10`, `11`, `12`, `13`, `16`, `17`, `19`, and others) found that the kickoff material's own cited backend file (`waiting_on.py`, `career_digest.py`, `honesty_log.py`, `search.py`, `self_test_harness.py`, etc.) **does not exist anywhere in this repository** — every one of them Range A's phantom code, not this repo's. Each time, the session built directly against `QUORUM_DATA_CONTRACTS.md`'s real JSON contract instead of the nonexistent Python file, and disclosed the substitution explicitly rather than fabricating a fix against code that was never there. `DEC-088` states this most sharply: *"No backend change was made this session... fabricating a fix against a nonexistent file... would be exactly the kind of invented work this project's discipline exists to prevent."*

| Batch | Sessions | Real, load-bearing findings |
|---|---|---|
| 5 (`DEC-073`–`076`) | Scaffold, model tiering, Privacy Gate, CalendarProvider | `resolvedFullTierModel` deliberately left `unresolved` rather than guessed — Sprint 0 hadn't run. Privacy Gate's regex patterns confirmed character-for-character identical to the backend's `trace_scrubbing.py` — a real cross-language parity check, not assumed. |
| 6 (`DEC-077`–`081`) | Today's 3 zones, Gate Reveal, Negotiation Screen | `computed_state.dart` — a file the spec assumed already existed — genuinely didn't, and was built fresh here as a disclosed construction (`DEC-078`). `stageBRan([])` vs `stageBRan([signOff])` proven distinct by test — the single most safety-relevant UI distinction in this batch (`DEC-080`). Negotiation screen has **zero recommendation logic anywhere** — every option renders identically, by design (`DEC-081`). |
| 7 (`DEC-082`–`086`) | Waiting On, Career Pipeline, Company Digest, Finance, Search | `applications.status`'s open vocabulary vs. `tasks.status`'s closed one — first confirmed here (`DEC-083`), later the deliberate design contrast for `MOBILE_23`/`DEC-096`. First genuinely clean contract check in the whole mobile sequence — `/search` needed no fix (`DEC-086`), reported plainly rather than manufacturing a finding to match the pattern. |
| 8 (`DEC-087`–`092`) | Honesty Log, Trust, Trust Digest (**new backend module**), You, Memory Transparency (**new backend module**) | `TabBar` explicitly considered and rejected for the Honesty Log, because even a symmetric tab means one outcome is hidden by default (`DEC-087`). `trust_digest.py` and `memory_transparency.py` are the first genuinely *new* backend modules built during mobile work, held to the full original-session standard (`DEC-089`, `DEC-091`). Dart's `.5`-rounding-vs-Python's-banker's-rounding uncertainty confirmed across five real files, always deliberately left untested at the exact disputed boundary until a real compiler existed (`DEC-092`). |
| 9 (`DEC-093`–`096`) | Extended-Outage wiring, Platform features, Screen Composition, Tasks | `action_disposition.dart` — CRITICAL tier, the literal S3-during-outage enforcement (`DEC-093`). Screen composition found the spec's assumed problem (12 screens each wrapping their own `Scaffold`, needing extraction) **did not exist** — every real screen here was already bare content; a different real problem existed instead (no navigation wired at all) and was fixed correctly for what was actually there, not for what the spec assumed (`DEC-095`). Tasks closes all 46 original sessions (`DEC-096`). |

**Real, live-verified result at this point:** 162 backend tests (two new real modules added), 214 mobile test *cases written* — explicitly, honestly, **zero of them had ever executed**, since no Dart/Flutter SDK existed on this machine until Batch 10.

### 5.3 Batch 10 — closing the gap to a real, live, connected system — `DEC-097` through `DEC-113`

This is the phase that turned "structurally correct, never compiled, never deployed" into an actual running backend a real phone could talk to.

| Entry | What closed |
|---|---|
| `DEC-097` (Phase 0) | `core/config.py` — the one genuine structural gap found (everything else the phase assumed was broken — flat layout, bare imports — was already correct on arrival). |
| `DEC-098` (Phase 2) | **Real, live cloud infrastructure for the first time.** Supabase (`ap-south-1`), Upstash, Langfuse, Gemini/Groq/Tavily, Google OAuth — all 8 credentials individually tested live, not format-checked. Cloud Run deployed (`asia-south1`, `--concurrency=1 --min-instances=0 --max-instances=2 --no-allow-unauthenticated`). Workload Identity Federation for CI, verified via a real GitHub Actions run. Genuine post-idle cold start measured at 4.543s. **A real, disclosed lapse:** a `gcloud` describe command printed every live credential in plaintext into the session — see §11.1, this is the incident directly upstream of this report's own top security finding. |
| `DEC-099` (Phase 3A) | `self_test_harness.py` wired directly to the real `gate.review()` — no stub ever built, since a stub layer would only have been deleted later. |
| `DEC-100` (Phase 3B) | The backend's **first real database query, ever** (`core/db.py`, `asyncpg`), `GET /trust_digest` live. A real design decision made without an explicit spec answer: `uncertain_no_data` excluded from both the total and the success-rate numerator, by direct analogy to the Gate's own no-collapse rule. `/health` deliberately decoupled from DB availability (liveness vs. readiness). |
| `DEC-101` (Phase 3C prereq) | **CRITICAL tier — the single most consequential entry in this project's real history.** Real auth routes, real Google OAuth, `refresh_token.py` converted to async. **A confirmed-exploitable vulnerability was found by this session's own mandatory pre-merge review, in this session's own first attempt at the fix** — a token-theft-detection race that a real, empirically reproduced probe (forced `asyncio.Event` ordering) proved could leave a race winner's new token live inside a family the system had just declared fully revoked. Fixed with `claim_and_rotate()` (one atomic transaction, a real row lock) and re-verified with the exact postcondition the first attempt's own test had skipped. A second, narrower bug (an already-revoked-but-unused token could still be claimed) was found by the *same* review's second pass and closed the same day. Full account in §10. |
| `DEC-102` | Cloud Run network policy relaxed (`--allow-unauthenticated`) — the real login system is now the actual security boundary, confirmed via three real live requests. |
| `DEC-103` | **The first real `dart test`/`flutter analyze`/`flutter test` run in this project's history.** 35 real analyzer issues found and closed (mostly missing generated Drift code). One real test-authoring bug found and fixed (a `ListView` viewport/scroll gap in a composition test — not a production defect). First real mobile-to-backend wire (`trust_digest_api.dart`), live-verified with a real minted token against the real public URL. Dart's `.5`-rounding behavior confirmed live for the first time (round-half-away-from-zero, exactly as five files' own disclosed uncertainty predicted). |
| `DEC-104` (Phase 4) | Real navigation wiring for all 7 previously-unreachable screens. Two real bugs caught by new tests: a layout overflow in `you_screen.dart`, a `setState`/`Future` misuse in the new search host widget. |
| `DEC-105` | **Real mobile login** — Google Sign-In, PKCE, secure token storage, proactive refresh. Platform scaffolding (`android/`/`ios/`) found never to have existed and backfilled. A real OAuth-client-type constraint (Google no longer accepting custom-scheme redirects directly) found and correctly solved with a stateless bridge route, not a workaround. Pre-merge review found one LOW-severity issue (3 duplicate tests) and it was cleaned up before merge. |
| `DEC-106`–`109` (Track C) | `GET /trust`, `/tasks`, `/career_pipeline`, `/finance/subscriptions` wired end to end, mobile included. `DEC-106` incidentally found and fixed a real, pre-existing, time-of-day-dependent UI bug (`"Holding steady"` literally duplicating its own section title between noon and 6pm) — unrelated to that session's own work, fixed anyway. `DEC-109` designed Finance's detection rule from scratch, since the spec never actually specified an algorithm (only later found, in `DEC-112`, to have missed a *second* spec document that did specify real parameters — see §9). |
| `DEC-110` | **CRITICAL tier.** Found, while scoping account deletion, that **no system anywhere in this backend mapped a real Google identity onto the internal UUIDs every domain table actually uses.** Stopped and reported per Rule 4/5 rather than built around. Built `users` table + `get_or_create_user()`, retroactively fixed `/tasks`/`/career_pipeline`/`/finance/subscriptions` to real per-user filtering with explicit cross-user-isolation tests. The CRITICAL review that followed found a real, live data-hygiene leak (45 orphaned test rows in the live `users` table) and it was fixed as a same-branch fast-follow. |
| `DEC-111` | Sprint 0's real, final result — both Full-tier candidate models failed to load due to a real emulator DNS issue (never a capability finding); SmolLM2-1.7B becomes the decided fallback, per the harness's own mechanical decision rule, not overridden by human intuition after the fact. |
| `DEC-112` | A real, disclosed process gap self-caught: `DEC-109` had checked only one of two spec documents that mattered before declaring "no algorithm specified." Fixed, with a genuine, disclosed behavior change to already-shipped logic (stricter subscription detection). |
| `DEC-113` | **CRITICAL tier.** `DELETE /account` — the real `SupabaseDeletionStore`, an identity-conflation bug found and fixed *before* any implementation existed to expose it, a real FK-ordered atomic transaction. CRITICAL-tier review: PASS WITH NITS, one fast-follow fix, two disclosed open items (§this report's §11.3). |

**Real, live-verified result as of this report (re-run by me this session, not copied):** **271/271 backend tests, `ruff check backend` clean, 297/297 mobile tests, `flutter analyze` clean.**

---

## 6. Specifications used

Every session in Range B was built against the same spec corpus Range A also used:

- `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` (the ADD) — the original architecture spec. Found, in `DEC-046`'s full audit, to carry real drift (stale test counts, stale validator counts) — converted to a permanent pointer at `STATUS_INDEX.md` rather than a static claim, so this can't recur.
- `QUORUM_DATA_CONTRACTS.md` — every REST endpoint's real request/response shape. This is the document most sessions extended: at least 10 real endpoint-gap fixes were made directly into it across the mobile sequence (§5.2's table), each found by checking the document directly rather than assuming an adjacent endpoint implied coverage.
- `QUORUM_CONFIGURATION_CONSTANTS.md` — real, named numeric constants (thresholds, TTLs, tolerances). `DEC-112` is the clearest example of why this document specifically matters: a real detection algorithm's parameters lived here, separately from the response-shape document, and were missed once before being found and corrected.
- `QUORUM_GATE_SPECIFICATION.md` — the Gate's state machine, quoted near-verbatim when `orchestration.py` was built (`DEC-058`).
- `QUORUM_MASTER_REFERENCE.md`, `QUORUM_PROJECT_OVERVIEW.md`, `QUORUM_PROJECT_STRUCTURE.md`, `QUORUM_IMPLEMENTATION_STRATEGY.md`, `QUORUM_CLAUDE_CODE_SPEC_USAGE_GUIDE.md` — orientation, target repo layout, and the seven-phase plan Batch 10 executed against.
- The 22 `IMPL_XX` and 23 `MOBILE_XX` individual session specs — each cited, checked directly (not recalled from memory) at the start of its own session, and disclosed as either accurate, imprecise, or describing Range A's phantom code, every single time.

**A real, standing gap in the spec corpus itself, worth naming directly:** neither `QUORUM_DATA_CONTRACTS.md` nor any other document specifies a `pendingActions`/`negotiations` persistence shape — the Today screen's own real backend need. This has been disclosed as a genuine architecture gap since `DEC-106` and remains open (§12).

---

## 7. Real, live external infrastructure — current state

| Resource | Real, confirmed state |
|---|---|
| Supabase Postgres | Live, `ap-south-1`, project `dxfeutkeofnbismljhsb`. 7 real tables + `pgvector`, plus `refresh_tokens` (migration `0002`) and `users` (migration `0003`). Free tier. |
| Cloud Run | Live, `asia-south1`, service `quorum-backend`, `--concurrency=1 --min-instances=0 --max-instances=2 --allow-unauthenticated`. Confirmed reachable via `gcloud run services describe` during this audit. |
| Upstash Redis, Langfuse, Gemini, Groq, Tavily, Google OAuth | All individually tested live as of `DEC-098`; no evidence of re-verification since, though nothing in the log suggests any of these have changed. |
| GitHub Actions CI | One real, working workflow (`test-gcp-auth.yml`, Workload Identity Federation). A full build/test/deploy pipeline is explicitly **not** built (Phase 6, untouched). |
| Android/iOS platform scaffolding | Real, backfilled in `DEC-105`. `flutter run` against a real device/emulator has never happened for the **main mobile app** (Sprint 0's separate app did run — see below). |

---

## 8. Test coverage and verification discipline

**Freshly re-verified by me, this session, not carried forward from the log:**

- Backend: **271/271 passing**, `ruff check backend` clean.
- Mobile: **297/297 passing**, `flutter analyze` clean.

**What this coverage is, and is not:** every backend test that touches the live database genuinely does — `INSERT`/query/`DELETE` cycles against the real, live Supabase project, per Rule 5, with disclosed cleanup (`finally` blocks) and at least two real, disclosed incidents of stray test rows found and cleaned (a DNS-interrupted run's leftover row in `action_events`, `DEC-110`'s own 45 orphaned `users` rows). Mobile tests are real, compiled, executed `dart test`/`flutter test` runs as of `DEC-103` onward — genuinely stronger evidence than the earlier "structurally correct" sessions, which were never claimed as more than that. **No test anywhere in this project exercises a real, human-driven end-to-end flow** — no test opens the actual app, taps sign-in, completes Google's real consent screen, and uses a screen with live data. Every login-adjacent test uses a manually minted token or an in-memory fake. This is disclosed consistently and repeatedly throughout the log, never hidden — but it means the single most basic "does this actually work for a person" question has never been answered by a test, only by individual pieces of the chain.

**Review tiers actually used, per `CLAUDE.md` Rule 6:**
- **CRITICAL tier, fresh-context (no cross-model reviewer ever available in this environment, disclosed every single time):** `provenance_check` (`DEC-056`), `orchestration.py` (`DEC-058`), `refresh_token.py`/`oauth_pkce.py` (`DEC-062`), `action_disposition.dart` (`DEC-093`), `refresh_token.py`'s async conversion + `claim_and_rotate()` (`DEC-101`), user provisioning (`DEC-110`), `DELETE /account` (`DEC-113`).
- **Standard, fresh-context:** every other merged branch (Track C read endpoints, the login screen, the subscription-detective correction).

I did not find a single instance across the whole log where a CRITICAL-tier file was merged *without* a recorded review, or where a review's own finding was silently dropped rather than fixed or explicitly logged as accepted risk.

---

## 9. Consolidated register — every real deviation, bug, and self-correction found across this project's history

This is the audit trail in one place. Everything below is disclosed *somewhere* in the log; this table exists so you don't have to hunt for it.

| # | Entry | What was found | Disposition |
|---|---|---|---|
| 1 | `DEC-051`–`053` | Three consecutive kickoff prompts each omitted the real spec's last function parameter | Built to the real signature every time |
| 2 | `DEC-053` (real) | `impact_simulator.py`'s `_direction()` had inverted polarity for `task_hours_committed` — found *during Range A's own preparation of Batch 4*, so it was built correct from the start in Range B, never actually shipped wrong here | Built correct from line one (`DEC-070`) |
| 3 | `DEC-058` | An early draft test would never have reached Stage B at all — caught by hand-tracing before running | Fixed before running |
| 4 | `DEC-088` | A "fix" the batch guide assumed was needed targeted a file that doesn't exist in this repo | Declined to fabricate; no backend change made |
| 5 | `DEC-095` | The spec's assumed layout-crash cause (nested internal scrollables) didn't match this repo's real code (none of the zones are internally scrollable) | Diagnosed and fixed the *actual*, different real cause |
| 6 | `DEC-096` | A genuinely missing mobile screen (Tasks) found by a full audit, never tracked anywhere across 22 prior sessions | Given its own full session |
| 7 | `DEC-097` | Phase 0's own spec claimed a flat backend layout and 156 tests; both false | Corrected before building |
| 8 | `DEC-100` | A `gcloud describe` command printed every live credential in plaintext into the session | Disclosed directly; **no evidence of credential rotation afterward** — see §11.1 |
| 9 | `DEC-101` | **A confirmed-exploitable refresh-token race**, found in this session's own first fix attempt, by this session's own mandatory review | Fixed, re-verified 6/6 deterministic runs; a second, narrower bug found by the same review's second pass, closed same day |
| 10 | `DEC-103` | A real test-authoring bug (`ListView` viewport gap) | Fixed |
| 11 | `DEC-104` | Two real bugs (`RenderFlex` overflow, `setState`/`Future` misuse) found only by actually running new tests, invisible to `flutter analyze` | Both fixed |
| 12 | `DEC-105` | 3 duplicate `/auth/callback` tests, LOW severity, found by pre-merge review | Removed before merge |
| 13 | `DEC-106` | A real, pre-existing, time-of-day-dependent UI content collision, unrelated to that session's own work | Found and fixed anyway |
| 14 | `DEC-109` | A test-fixture date-overflow bug (`datetime(2026, 1, 32, ...)`) | Fixed; **recurred twice more** in `DEC-110` and `DEC-112` (same class of bug, same fix each time) |
| 15 | `DEC-110` | No user-identity-provisioning system existed anywhere — a real blocker for `DELETE /account`, found by stopping and checking before building | Built, with retroactive fix to 3 already-shipped endpoints |
| 16 | `DEC-110` (review) | 45 real orphaned `users` rows from a fixture with no cleanup | Fixed as a same-branch fast-follow |
| 17 | `DEC-112` | `subscription_detective.py` shipped against an incomplete spec check — a second document specified real parameters the first session missed | Corrected, with an honest, disclosed behavior change to shipped logic |
| 18 | `DEC-113` | An identity-conflation bug in `account_deletion.py`'s signature, found during design before it could ship | Fixed before any implementation existed to expose it |
| 19 | `DEC-113` (review) | A misleading doc comment; a narrow, disclosed atomicity gap between two purge stores; a missing widget test | Comment fixed; other two logged as open items #15/#16, not silently accepted |

---

## 10. What the CRITICAL-tier reviews actually found (the two most consequential)

**`DEC-101` — the refresh-token race.** This is the single highest-value piece of review work in the project's history, and worth understanding in your own words, not just trusting the log's summary. The theft-detection scheme depends on "claim the old token" and "issue the new token" being effectively one atomic step. The first real attempt at building this got the *claim* right (an atomic `UPDATE ... WHERE used=false`) but left the *new token's insertion* as a separate statement — meaning two concurrent requests replaying the same stolen token could both "win" in a way that left one attacker-controlled token alive inside a family the system believed it had just fully killed. The review didn't just reason about this abstractly; it wrote a controlled test forcing the exact race with `asyncio.Event` gates and got back a live, unrevoked token as proof. The fix (one transaction, a real row lock) was then itself re-probed six consecutive times against the live database, deterministic every time, before being trusted.

**`DEC-113` — `DELETE /account`.** Lower stakes than `DEC-101` but the same discipline: independently ran the real backend suite against the live database, hand-traced the identity-parameter split for conflation, confirmed the FK-safe deletion ordering against the real schema (not the code's own comment), and confirmed the two "honest zero" purge stores by direct grep rather than trusting the docstring.

---

## 11. Critical review — independent findings

Per your instruction, I did not assume something is fine because it was marked done. Below is organized by how seriously I think each one deserves your attention, and I've separated what the project already disclosed from what I'm surfacing independently.

### 11.1 HIGH — needs your direct attention

**The live, deployed backend may still be signing real access tokens with a publicly-known default JWT secret.** I found this independently while verifying the audit, not by reading it off a disclosed open item.

- The literal default string is `"change-me-in-real-deployment"`, visible directly in `main.py`'s own source (I read it during this audit — it is not a secret in the code, it's the *fallback value the code warns about*).
- `DEC-098`'s own text confirms this exact warning **genuinely fired on the live, deployed Cloud Run service** at the time of that session — meaning the deployment was, at that point, actually signing tokens with the known default.
- I read every entry from `DEC-098` through `DEC-113` looking for a moment where `JWT_SIGNING_KEY` was rotated to a real secret and could not find one. `DEC-101`, `DEC-105`, and `DEC-113` all build and test extensive real session-management logic on top of "the real, live `JWT_SIGNING_KEY`" — language that is consistent with either a real secret having since been set, or the known default still being in place and simply being treated as "the real, currently-configured value." The log does not disambiguate this anywhere I could find.
- I attempted to verify this directly: I confirmed via `gcloud run services describe` that `JWT_SIGNING_KEY` is genuinely configured as an environment variable on the live service (I did not, and would not, print its value). I then tried to check Cloud Run's own logs for whether the insecure-default warning has fired on any *recent* deployment — this was blocked by this environment's own permission classifier, and I did not attempt to work around that block.
- **Why this matters:** the service has been `--allow-unauthenticated` at the network layer since `DEC-102` — the JWT check is the *entire* real security boundary now. If the signing key is still the known default, anyone who reads this project's own public GitHub repository (it's confirmed public — `STATUS_INDEX.md`'s Environment section) can forge a valid access token for any user and call every authenticated endpoint, including `DELETE /account`, without ever completing a real login.
- **What I recommend:** before doing anything else with this deployment, directly confirm whether `JWT_SIGNING_KEY` is still `"change-me-in-real-deployment"` (e.g., `gcloud run services describe quorum-backend --region=asia-south1 --format="value(spec.template.spec.containers[0].env)"` filtered to that one name, run somewhere with permission to do so, or simply set a fresh, real, random secret regardless and redeploy — that action is safe either way and closes the question for good).

**No evidence the credentials plaintext-exposed in `DEC-100` were ever rotated.** `DEC-100` discloses, honestly and directly, that a `gcloud` command printed every live credential (Supabase password, every API key, the OAuth client secret) in plaintext into that session. The entry states no *new* party gained access from it, which is true as far as it goes — but I found no later entry documenting that any of those credentials were subsequently rotated as a precaution. Given how cheap rotating a Supabase password or an API key is compared to the cost of being wrong about who has seen a chat transcript, I'd treat this as worth doing now if it hasn't been done, not because anything is known to be wrong, but because the log doesn't currently let you rule it out.

### 11.2 MEDIUM — real, worth tracking, not urgent

- **The two open items the `DEC-113` review itself logged remain genuinely open** (`STATUS_INDEX.md` #15, #16): a narrow atomicity gap between the Postgres and vector-embedding purges in account deletion, and no widget test for the delete-button's error path. Both low-probability/low-severity, both honestly disclosed, neither fixed. Fine to leave as-is given the reasoning recorded, but they are real, not just theoretical.
- **The whole system has never been run once by an actual human.** No real Google sign-in has ever been completed through the real app; no `flutter run` has ever launched the main app on a device or emulator; the Today screen (the app's actual home screen) has no live backend at all. If asked to demo this live in an interview, none of it currently works end-to-end on a phone — every individual wire is real and tested, but they have never been exercised together by a person. This is disclosed consistently throughout the log, but it's worth stating plainly here since it's the single largest gap between "the architecture is real and correct" and "you can hand someone a phone and show them the app."
- **Concurrency ceiling is very low for anything beyond solo demo use.** `--max-instances=2`, `--concurrency=1` is architecturally correct and deliberate (it's what makes cross-user state isolation real rather than assumed) — but it also means this deployment cannot meaningfully serve more than a couple of concurrent real users. Fine for a portfolio project's actual purpose; worth being explicit about if you ever describe this as "production-ready" rather than "architecturally production-shaped."
- **No load, chaos, or failure-injection testing exists anywhere.** The `/health`-vs-`/trust_digest` DB-unavailability test (`DEC-100`) and the `503`-not-a-crash tests on each Track C endpoint are the closest thing to this, and they're real and good — but there's no test of, say, Cloud Run scaling from 0→2 instances under real concurrent load, or of Supabase's connection pool under real contention.

### 11.3 LOW — disclosed, accepted, genuinely fine to leave as-is

- `coverage_check`'s single-shared-stopword leniency (open item #3) — a real, spec-accepted trade-off, not a bug.
- `orchestration.py`'s retry wrapping the whole Stage B call rather than Critic/Judge independently (open item #4) — minor cost inefficiency, not a correctness issue.
- The Dart `.5`-rounding difference from Python — confirmed, understood, consistently avoided in every affected test's assertions.
- `pii_leak_check`'s cross-platform wiring to the mobile Privacy Gate's real flagged-span output — real, disclosed, not yet done, genuinely lower priority than the items above.

### 11.4 Log-integrity / documentation findings

- **The `DEC-050`–`~063` number collision** (§2) is real, disclosed, and explained, but it remains a technical violation of the log's own stated Rule 2, and it has already caused at least one real internal citation mistake (`DEC-077`). I'd treat this as closed/acceptable given the explanation, but flag it here since you asked me to name inconsistencies even ones the project has already reasoned through.
- **The `_at(N)`-date-overflow test bug recurred three separate times** (`DEC-109`, `DEC-110`, `DEC-112`) — the exact same class of mistake, caught and fixed identically each time. Not a real defect in shipped code (every instance was a test fixture, caught by the test run itself before merge), but worth knowing as a recurring authoring pattern if you're looking for where review attention tends to be needed.
- **No entry in the log documents when, or whether, the exposed credentials from `DEC-100` were rotated** — already covered in §11.1, listed again here because it's as much a documentation gap as a security one: even if rotation happened, there's no record of it.

---

## 12. What remains incomplete or uncertain — the complete, current list

This is `STATUS_INDEX.md`'s own open-items register (16 items as of `DEC-113`), organized by what actually blocks real end-to-end use versus what's a smaller, disclosed gap:

**Blocks a real, human, end-to-end demo:**
1. No genuine, human-completed Google sign-in has ever been exercised (needs a real browser interaction this environment can't automate).
2. No `flutter run` against a real device/emulator for the main app has ever happened.
3. The Today screen (the app's home) has no live backend — needs a `pendingActions`/`negotiations` persistence design that doesn't exist in the spec corpus at all, not just in this repo.
4. Search, Waiting On, and Memories have no backend wiring — each needs real, new architecture (a `sent_messages` table, real embedding/ranking, a real `mem0` integration respectively).

**Real but smaller, disclosed gaps:**
5. On-device Full-tier model unresolved by design — SmolLM2-1.7B is the honest, decided fallback (§5.3, `DEC-111`); a genuine Full-tier candidate has never actually loaded on this hardware, only failed to download.
6. `pii_leak_check` ↔ mobile Privacy Gate wiring, not done.
7. Real demo dataset across all 5 domains, not built.
8. The multi-day `pg_cron`-vs-Supabase-pause observation, needs real elapsed time no session can compress.
9. Phase 6 (CI hardening — full build/test/deploy pipeline) untouched.
10. `DEC-113`'s two logged nits (§11.2).
11. **§11.1's JWT signing-key question — not on the project's own open-items list at all, and the most important item on this page.**

---

## 13. Overall assessment

Judged against what the project actually set out to be — a real, spec-driven, honestly-verified build, not a demo — the work is consistent with its own stated discipline throughout. I did not find a single case in Range B's real history where a claimed result wasn't backed by a real command's real output, where a CRITICAL-tier file merged without review, or where a found problem was quietly dropped instead of fixed or explicitly logged as accepted risk. The project's own culture of stopping to report a spec/reality mismatch rather than building around it is real and consistently practiced, not just stated in `CLAUDE.md` — `DEC-088`'s declined fabrication and `DEC-110`'s stop-and-report on the identity-provisioning gap are the clearest examples, but the pattern recurs dozens of times across both ranges of the log.

The gap between "architecturally real and correct" and "a person can pick up a phone and use it" is genuine and currently large — nothing in this system has ever been exercised end-to-end by a human. And one real, unresolved question (§11.1) sits directly on the project's actual security boundary and deserves a direct answer before this deployment is treated as safe to rely on, demo publicly, or extend further.
