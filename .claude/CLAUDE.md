# CLAUDE.md — Quorum

## What this is
Quorum is a hybrid edge-cloud, multi-agent trust architecture for autonomous AI action, deployed as a mobile personal-operations assistant (email, calendar, tasks, finance, career). Full history: `specs/tier3_verification/DECISIONS_LOG.md`.

**Current status lives in `specs/tier3_verification/STATUS_INDEX.md` — always check that file first, never assume status from this one.** This file holds stable facts and rules; session-by-session progress changes too often to duplicate here safely without it going stale, which has already happened once (see "What changed mid-project" below).

## Preethish's context — write code accordingly
Solo developer, portfolio-motivated, prior real experience with this exact spec-driven Claude Code methodology on AEGIS (a production SAP helpdesk AI) — this is not a first attempt at the *methodology*, so don't over-explain the ritual itself. It *is* the first attempt at a system this architecturally distinctive (an independent verification Gate, cross-domain negotiation, a two-model Generator/Critic split) — do over-explain anything Quorum-specific, especially the reasoning behind a design decision, not just what it is. No other developer reviews this code — be the second pair of eyes yourself before calling anything done, the same standard `DECISIONS_LOG.md`'s own entries hold themselves to throughout this project's real history.

**Confirmed directly, not assumed, during a full re-grounding pass:** this is a personal portfolio project aimed specifically at getting placed as an AI Engineer — not academic (no rubric, no institution, no submission date) and not intended for the developer's own daily personal use (purely a project, stated explicitly). The real goal is **100% completion**, not a scoped-down demo — all five domains matter, with Career carrying a little extra real weight given the direct, fitting connection to the actual job-search goal this project serves. No hard deadline exists, but speed is genuinely valued — treat "as soon as possible, done right" as the real operating tension, not license to cut the verification discipline that's been this project's actual differentiator throughout its history.

**Beginner-level coder, confirmed directly** — not a self-deprecating hedge, an accurate description to write code and explanations against. Preferred communication: plain-language by default, with technical depth available on request, not the reverse. When something breaks: fix it and report what was wrong afterward — not a guided joint debugging session. If a proposed improvement or upgrade beyond the immediate ask is well-reasoned, it's explicitly welcomed, not scope creep to apologize for.

**Real machine:** Intel i5-12500H, 16GB RAM, RTX 3050 4GB (laptop). No real Android device confirmed — Sprint 0's on-device benchmark should run against a real Android emulator configured with ≥4GB allocated RAM, a legitimate, real path to a genuine measurement, not a compromise. Real cloud accounts (Supabase, Upstash, Google Cloud) are free-tier only, by explicit constraint — every infrastructure recommendation must fit within real free-tier limits, not assume paid tiers are available. Real API keys (Gemini, Groq) get generated when actually needed for a session, not provisioned speculatively ahead of time.

## The Rules — non-negotiable, every session
1. No placeholder code, ever. No `TODO`, no bare `pass`, no stub returns. If a session can't be completed with real, runnable code, it stops and reports — it doesn't ship a plausible-looking placeholder.
2. Every verification step in a session's spec must pass before the session is complete. One failing check = incomplete session, not "mostly done."
3. Never invent architecture beyond what the spec (as corrected by `DECISIONS_LOG.md`) describes. A good idea that isn't in scope becomes a logged OPEN item, not silent extra work.
4. When a spec's assumption doesn't match the real code/API/schema, stop and report the discrepancy. Do not silently adapt to what seems reasonable.
5. **Real credentials, real APIs — except where the action is real-world-irreversible.** Test against real Gmail/Calendar auth flows, real free-tier LLM APIs, real Postgres — never mocks, when the point is proving an integration works. **The one carve-out: anything that would actually send an email, book a real calendar event, or otherwise touch a real external destination uses dedicated sandbox test accounts, always.** This is not a relaxation of the "test the real thing" principle — it's the same principle applied with the same rigor Quorum's own router applies to S3-stakes actions.
6. Anything touching the Gate's verification logic, security/auth, secrets handling, or a real external-action path gets cross-model independent review before merge — not just fresh-context review. See "Review discipline" below.

## Architecture facts that must never be violated
- Stakes classification (S0–S3) is a hardcoded lookup table by action type. Never a learned classifier, never inferred from model confidence.
- The Gate's Stage A validators are pure code — zero LLM calls, zero exceptions. If a check can be a database lookup, it is one.
- `Finding.evidence_state` is three-valued: `verified_true` / `verified_false` / `no_data_found`. Never collapse `no_data_found` into a pass or a fail.
- S3 (external-irreversible) actions always require explicit human approval — in every mode, including the degraded-offline-continuity mode. No exception, ever, regardless of how confident any automated check is.
- The Critic runs on a different model provider (Groq/Llama) than the Generator/Judge (Gemini). This is deliberate model diversity, not a cost optimization — never "simplify" it onto one provider.
- Cloud Run concurrency = 1, explicit. Never raised without a documented reason — this is the fix for a real cross-user state-isolation risk, not a default left unconsidered.
- Compute (Cloud Run) and database (Supabase) live in the same region. Never assume geographic co-location doesn't matter here — it was a real, found bug once.
- `tasks.status` is a real, closed set (`open`/`done`/`cancelled`), enforced by a database `CHECK` constraint — parse it fail-loud on an unrecognized value. `applications.status` has no such constraint and is genuinely open — parse it defensively instead. These are opposite handling on purpose; don't make them consistent with each other, they're describing two genuinely different real contracts (`MOBILE_11` vs. `MOBILE_23`).

## What changed mid-project — don't assume the old state
- **The backend's real, current layout is flat** — `backend/main.py`, `backend/router.py`, and package directories (`gate/`, `agents/`, etc.) all sit directly under `backend/`, imported via `PYTHONPATH=backend`. A restructure to a proper `backend/src/quorum_backend/` src-layout is *specified* (`specs/tier1_foundation/QUORUM_PROJECT_STRUCTURE.md`) but **not yet applied** — don't write new code assuming `from quorum_backend.gate import X` import paths work today. Check which state is actually on disk before assuming either.
- **This project has real git history only as of one deliberate, disclosed late bulk commit**, not a clean per-session log — a written commitment to per-session branches existed for 45+ sessions before anyone actually followed it. Don't infer anything about *when* a piece of code was written from commit timestamps; the real record of that is `DECISIONS_LOG.md`, not `git log`.
- **`self_test_harness.py` still runs against `_stub_gate_for_demo`, not the real Gate**, even though the real Gate (`gate.review()`) has been complete since `IMPL_08`. A `target: "stub" | "real_gate"` field exists specifically so downstream consumers (like the Trust screen) can tell the truth about which one produced a given result — check that field, never assume "the Gate is real" means "this specific test ran against it."
- **Every mobile screen's repository is an honest `UnimplementedError` placeholder**, not a bug — real backend deployment doesn't exist yet, so nothing in `mobile/lib/features/**/*_screen.dart` has ever been run against a live API. This is deliberate and disclosed, the same "injected dependency" pattern used for every other real/external boundary in this project — don't "fix" it by mocking data in.

## Drift patterns to actively watch for
1. **Reaching for an LLM call to check something checkable in code.** The Gate's entire cost/correctness advantage depends on this never happening. If you're about to write a prompt that asks a model to verify a fact that exists in Postgres or Redis, stop — write the lookup instead.
2. **Self-assessed model confidence as a routing signal.** Never ask a model "how confident are you" and route on the answer. Stakes and complexity are computed from structural features, not self-report.
3. **Treating a fresh-context review as sufficient for Gate/security code.** It's sufficient for routine code. It is not the bar for anything under Rule 6 above — that needs a genuinely different model reviewing it.
4. **A persistent background worker or long-running process.** The deployment is deliberately fully serverless (Cloud Run, scale-to-zero) with `pg_cron`/`pg_net` as the scheduler. Any code that assumes a process stays alive between invocations is wrong for this architecture.
5. **Chronological-feed-as-primary-surface in any frontend work.** The home screen is status-first (Needs you now / Holding steady / In motion). The chronological log is real, but secondary — never let it creep back to primary.
6. **Restating a real number (test count, document count, session count) instead of pointing to `STATUS_INDEX.md`.** This exact pattern caused real, disclosed drift at least three separate times across this project's history — a number copied once and never updated again as the count kept changing. If you're about to type a specific count into a file that isn't `STATUS_INDEX.md` itself, stop and use a pointer instead.

## Environment
Real project root, as of this writing: `D:\Program Files\QUORUM\quorum` on Windows, opened via the Claude Code VS Code extension running as a chat interface — not WSL, not a Linux dev environment. Real, confirmed machine: Intel i5-12500H, 16GB RAM, RTX 3050 4GB (laptop) — factor this into any local resource recommendation (e.g., how many Docker services can realistically run concurrently). No live Supabase project, Cloud Run service, or other real cloud infrastructure has been provisioned yet; every deployment-related fact in this codebase is a real, current specification, not yet an executed deployment. **All real cloud accounts (Supabase, Upstash, Google Cloud) are free-tier only, by explicit, confirmed constraint** — every infrastructure recommendation must fit within real free-tier limits, never assume a paid tier is available. Fill in the real Supabase project ref and Cloud Run service name here the moment either becomes real — until then, this line stays accurate by staying blank rather than guessing.

## Where the real detail lives
- Why any decision was made → `specs/tier3_verification/DECISIONS_LOG.md`
- What's next / current build status → `specs/tier3_verification/STATUS_INDEX.md`
- Why this project exists, and a curated reading map through everything else → `specs/tier1_foundation/QUORUM_PROJECT_OVERVIEW.md`
- The full spec-writing methodology and session template → `QUORUM_SPEC_METHODOLOGY.md`
- The Gate's full specification → `specs/tier1_foundation/QUORUM_GATE_SPECIFICATION.md`
- The full repository layout, current and target → `specs/tier1_foundation/QUORUM_PROJECT_STRUCTURE.md`
- Phases and gates from here through production → `specs/tier1_foundation/QUORUM_IMPLEMENTATION_STRATEGY.md`
- How this spec system actually works with Claude Code specifically → `specs/tier1_foundation/QUORUM_CLAUDE_CODE_SPEC_USAGE_GUIDE.md`
- Whether an old claim is still true → `DECISIONS_LOG.md` in practice (append-only, real record of what changed and why). `specs/tier5_historical/` was specified as a future home for this if it were ever needed separately — checked during a full staleness audit: it was never actually created, and `DECISIONS_LOG.md` has adequately absorbed this role throughout the project. Don't look for a directory that isn't there.

## Common commands
```bash
# Backend lint — run before every commit, every backend-touching session
ruff check backend

# Backend test suite — the real, live-verified count lives in STATUS_INDEX.md
PYTHONPATH=backend pytest backend/tests -q

# Mobile pure-logic tests (zero-Flutter-dependency files only) — needs a real
# Dart SDK, unavailable in the original development sandbox; run on a real
# machine before merging any mobile session
dart test

# Mobile static analysis — same real-machine caveat as above
flutter analyze
```
(Note the `PYTHONPATH=backend` convention above reflects the *current, real, flat* backend layout — see "What changed mid-project." If the `src/quorum_backend/` restructure has been applied by the time you're reading this, these commands need updating to match; check which is actually true before running either version blindly.)

## Spec-reading discipline
Before writing any code: environment check (correct branch, correct working directory, required services actually reachable — stop and report if anything's wrong, don't proceed on an unconfirmed environment), then a full read of the session's spec — every file section and the verification section — before touching anything, then a cross-reference check (does each file this session touches already exist from an earlier session?), then a dependency check (do this session's imports actually exist yet?). See `QUORUM_SPEC_METHODOLOGY.md` for the full ritual, and `specs/tier1_foundation/QUORUM_CLAUDE_CODE_SPEC_USAGE_GUIDE.md` for how that ritual maps to real Claude Code mechanics (what's auto-loaded, what needs an explicit read, and the slash commands that package the ritual as something executable rather than just described).

## Decision-making protocol — confirmed directly, not assumed
Use reasonable judgment on non-trivial calls and report afterward, rather than stopping to ask before every one — but **when exercising that judgment, rethink it twice and verify before implementing, not on first instinct.** This is the same standard already established elsewhere in this file (checking the real source before building, hand-verifying arithmetic before trusting a test) — applied explicitly to judgment calls themselves, not just to code.

**When my recommendation and Preethish's stated preference genuinely conflict: implement my recommendation, with the reasoning explained plainly.** This is a real, confirmed instruction, not an assumption of authority — stated explicitly because good engineering judgment is what this project is actually for. Explaining the "why" is not optional in this case; a silent override of a stated preference, even a well-reasoned one, would be a real trust violation.

**Session cadence for actual implementation work: one session, explicit approval, then the next — not a batch run through multiple sessions unsupervised.** This is specific to real Claude Code implementation sessions against `IMPL_XX`/`MOBILE_XX` specs, distinct from the separate session-guide/verification-prompt authoring effort this project has also produced.

## Review discipline
Fresh-context subagent review of the diff before merge, for every session — standard. For anything under Rule 6 (Gate logic, security/auth, secrets, real-action paths): the review subagent runs on a **different model family than the one that implemented the session**, mirroring the Generator/Critic split that is Quorum's own architecture. This is not optional ceremony — it's the same reasoning Quorum's own thesis makes about same-family review sharing blind spots, applied to building Quorum itself.
