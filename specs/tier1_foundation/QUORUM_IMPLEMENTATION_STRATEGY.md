# Quorum — Implementation Strategy
## Current State Through Production — Phases, Gates, and Reasoning
## Place at `specs/tier1_foundation/`

---

## HOW THIS RELATES TO OTHER DOCUMENTS

`STATUS_INDEX.md` has the literal current state and the complete open-items list — the *what's true right now*. `QUORUM_PROJECT_STRUCTURE.md` has the literal file/folder map — the *where things go*. This document is the *why* and the *gates*: what must be true before moving from one phase to the next, and what a genuine blocker looks like versus something to fix forward through. Read all three; none of them duplicate the others.

**The single most important fact this document is built around, worth stating before anything else:** unlike a typical spec-driven project starting from an empty repository, Quorum's situation right now is that **all 46 planned build sessions are already complete** — 23 real backend sessions, 23 real mobile sessions, 156 real passing tests, 65 real specification documents, a completed full specification audit. What follows is not "the remaining sessions to build" in the usual sense. It's the real-world work that can only happen outside a development sandbox: physical device testing, real cloud provisioning, and closing the small number of genuinely open items `STATUS_INDEX.md` already names precisely.

---

## REAL CURRENT STATE (confirmed live, not assumed — re-verify before trusting this section if it's been a while)

- `PYTHONPATH=backend pytest backend/tests -q` → 156 passed, `ruff check backend` clean
- 2 real git commits exist (`abe7fe8`, `906483f`) — a disclosed late bulk baseline, not per-session history; see `CLAUDE.md`'s "What changed mid-project"
- All 23 backend and 23 mobile session documents are marked real in `STATUS_INDEX.md`, cross-verified during a full specification audit (`DEC-046`) that found and closed 18 real issues, all in documentation, none in the backend or mobile implementation layers themselves
- `backend/src/quorum_backend/` (the target src-layout) is **specified, not applied** — the real backend on disk is still the flat layout as of this writing
- No live Supabase project, Cloud Run service, or Upstash Redis instance exists — every deployment fact is a real, current spec, not an executed deployment
- `dart test` and `flutter analyze` have **never been run** anywhere in this project's real history — every mobile session was written and structurally verified without a Dart/Flutter SDK available in the original development environment

Nothing here has been verified to run *as a deployed system* yet — only to exist correctly and pass isolated tests. The phases below close that gap in order.

---

## PHASE 0 — STRUCTURAL MIGRATION (you are here)

**Goal:** apply `QUORUM_PROJECT_STRUCTURE.md`'s specified repository layout to the real, already-complete codebase, without touching business logic.

1. Create the full directory skeleton per `QUORUM_PROJECT_STRUCTURE.md` (folders + every `[CREATE NOW]` file).
2. Move every real backend `.py` file into `backend/src/quorum_backend/`, matching subfolder for subfolder.
3. Update every import statement from the current bare top-level form (`from gate.schemas import X`) to the namespaced form (`from quorum_backend.gate.schemas import X`) — across both source files and test files.
4. Add `backend/src/quorum_backend/core/config.py` — the real settings module named as a genuine gap in `QUORUM_PROJECT_STRUCTURE.md` §3, since no runtime config layer exists anywhere in the current codebase.

**Gate to Phase 1:** `pytest backend/tests -q` still shows **156 passed** after the move — not "roughly the same number," the exact same real count, since this phase must not change behavior, only location. If the count differs, something migrated incorrectly; fix it here before moving on, per Rule 2 in `CLAUDE.md`.

---

## PHASE 1 — SPRINT 0: EMPIRICAL RESOLUTION

**Why this can't happen earlier or be skipped:** two real open items (`STATUS_INDEX.md` #1–#2 — the on-device model choice and the Flutter plugin choice) are explicitly not resolvable by further specification. `IMPL_00`'s real benchmark harness (`sprint0/lib/model_benchmark.dart`, `sprint0/lib/scoring_test.dart`) already exists, tested, and complete — this phase is running it on a real device, not building anything new.

1. Run the real benchmark harness on a physical Android device or emulator with ≥4GB RAM.
2. Record the real, measured result — which model wins on the real structured-output prompts, not an assumption.
3. Update `mobile/lib/model/on_device_model_loader.dart`'s `resolvedFullTierModel` from `unresolved` to the real, measured choice.

**Gate to Phase 2:** `resolvedFullTierModel` holds a real value backed by an actual benchmark run, and the loader's own test (which currently asserts it throws rather than guesses) is updated to reflect the real resolved state.

---

## PHASE 2 — REAL INFRASTRUCTURE PROVISIONING

**Why this phase is sequenced here, not earlier:** two more open items (`STATUS_INDEX.md` #3–#4 — real Cloud Run cold-start latency, and whether `pg_cron`'s firing prevents Supabase's inactivity pause) are **unmeasurable until real infrastructure exists**. This is provisioning, not building — standard infra work, not session-spec-driven development.

1. Provision a real Supabase project; run the real migration (`backend/migrations/`, or its Phase-0-relocated equivalent) against it.
2. Confirm the real output vector dimension of the loaded Qwen3-Embedding-0.6B model before writing it into any migration — open item #5, and a real, named risk if guessed instead of confirmed.
3. Provision real Upstash Redis, real Langfuse Cloud project.
4. Deploy the backend to a real Cloud Run service, concurrency explicitly set to 1 per `CLAUDE.md`'s architecture facts — never left at a framework default.
5. Fill in `CLAUDE.md`'s "Environment" section with the real project ref and service name the moment each exists — that section was deliberately left blank rather than guessed.

**Gate to Phase 3:** a real HTTP request against the deployed Cloud Run URL's `/health` endpoint returns successfully, and the real, measured cold-start latency is recorded (closing open item #3) rather than estimated.

---

## PHASE 3 — REAL INTEGRATION WIRING

**The largest remaining phase, and why it's genuinely different in kind from Phases 0–2:** this is the first phase involving real *new* code, not migration or provisioning. Two categories of work:

**A. Closing the two real, deferred backend gaps** (`STATUS_INDEX.md` #7–#8):
- Wire the real Gate into `self_test_harness.py`, replacing `_stub_gate_for_demo` — this needs `AdversarialScenario`'s current toy format redesigned to carry what real `stage_a_checks`/`critic_call`/`judge_call` construction actually requires, confirmed genuinely substantial when first found (`MOBILE_16`), not a quick fix.
- Build the real weekly-aggregation query grouping raw `action_events` into `WeeklyTrustSummary` instances, closing the gap between `trust_digest.py`'s already-correct `compare_weeks()` and a live `/trust_digest` endpoint.

**B. Wiring every mobile repository to the now-real backend** (per Phase 2): every `*Repository` class across `mobile/lib/features/**/` currently throws `UnimplementedError` by design (see `CLAUDE.md`'s "What changed mid-project") — this phase replaces each with a real HTTP implementation against the real, deployed API from Phase 2.

**Gate to Phase 4:** at least one full, real, end-to-end flow works — a real action proposed, passed through the real Gate (not the stub), and visible on a real device's Today screen, sourced from the real deployed backend, not mocked data.

---

## PHASE 4 — MOBILE NAVIGATION COMPLETION

**Real, remaining scope:** `STATUS_INDEX.md` #9 — seven real, already-built, already-tested screens (Career pipeline, Company Research Digest, Finance, Search, Waiting On, the Gate reveal, the negotiation screen) aren't reachable from normal app navigation. Genuinely smaller than Phase 3, since no new screens need building — this is an information-architecture decision (a "More" menu, integration points within Today's zones, or a dedicated section) plus wiring the real navigation links, the same pattern already used successfully for Trust→Trust Digest and You→Memory Transparency.

**Gate to Phase 5:** all seven screens are reachable through real, considered navigation — not an arbitrary set of links added just to close the item.

---

## PHASE 5 — FULL REAL-DEVICE VERIFICATION

**Why this is its own phase, not folded into earlier ones:** `dart test` and `flutter analyze` have never actually run anywhere in this project's history — every mobile session was verified structurally, against real, cross-checked APIs, but never executed. This phase is the first time that changes.

1. Run `dart test` across every mobile test file — expected to pass, since every test was written with real, hand-verified expected values, but genuinely unconfirmed until this phase.
2. Resolve open item #6 — Dart's exact `.5`-boundary rounding behavior for `num.round()`/`toStringAsFixed()` — with a real compiler, then write the test that was deliberately left unasserted in `finance_logic.dart` pending exactly this.
3. Run `flutter analyze` and resolve the two honestly-flagged uncertainties in the codebase (`CardThemeData` vs. `CardTheme`, the `device_calendar` `Result<T>` field names) with real compiler output.

**Gate to Phase 6:** `dart test` and `flutter analyze` both genuinely pass, on a real machine, with real output — the same bar Rule 2 in `CLAUDE.md` already holds every other verification step to.

---

## PHASE 6 — PRODUCTION HARDENING

The CI stages already deliberately deferred, named directly in `.github/workflows/ci.yml`'s own comment (`DEC-003`): the golden scenario suite, and the health-checked deploy-cutover stage. Both were correctly left unbuilt because they need the real Gate and a real Cloud Run target — both now exist, following Phases 2–3.

1. Populate the golden scenario suite, CI-gated, trajectory-checked.
2. Build the real deploy-cutover CI stage in `infra/github_actions/`, health-checked against the real Cloud Run service.
3. Full go-live checklist against the real, public deployment — not `localhost`, not a staging placeholder.

**Gate to "done":** the full pipeline — lint → test → build → golden suite → health-checked deploy — runs green against the real production target.

---

## IF SOMETHING BREAKS MID-PHASE

Per `CLAUDE.md` Rule 2: a session with a failing verification is not a complete session, regardless of phase. Fix forward within the phase currently open — don't skip ahead to "make progress elsewhere" in a later phase while an earlier gate remains unmet. If a fix genuinely requires reopening an earlier phase's work, that's real, valuable information — log it as a new entry in `DECISIONS_LOG.md`, the same way every other real finding across this project's history has been logged, not silently patched and left unrecorded.

---

*Related: `STATUS_INDEX.md` (the detailed current-state and open-items list), `CLAUDE.md`, `QUORUM_SPEC_METHODOLOGY.md`, `QUORUM_PROJECT_STRUCTURE.md`, `QUORUM_CLAUDE_CODE_SPEC_USAGE_GUIDE.md`.*
