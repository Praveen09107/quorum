# Quorum — Claude Code Spec Usage Guide
## How This Specification System Actually Works With Claude Code
## Place at `specs/tier1_foundation/`, referenced from `CLAUDE.md`

---

## THE REAL TRANSITION THIS GUIDE EXISTS FOR

Quorum's specs weren't built the way a typical spec-driven project's are — there's no earlier "paste a document bundle into a chat tool with no memory" phase to move on from, because the entire architecture (all 65 real specification documents — the ADD, `QUORUM_MASTER_REFERENCE.md`, `QUORUM_DATA_CONTRACTS.md`, 23 backend `IMPL_XX` sessions, 23 mobile `MOBILE_XX` sessions, and the full verification/audit trail) was designed and, in the case of backend and mobile, **already built and tested** across one long, continuous Claude.ai conversation. Every one of the 156 real backend tests already passing, and every real Dart file already written, came out of that conversation — this guide isn't onboarding Claude Code onto an *unbuilt* system, it's onboarding Claude Code onto a **real, substantially complete one**, for whatever real-world work remains: the structural repository migration, Sprint 0's empirical device testing, real infrastructure provisioning, and the handful of genuinely open items `STATUS_INDEX.md` tracks honestly.

**What that means concretely: don't assume a session document describes work that hasn't started.** Check `STATUS_INDEX.md` before treating any `IMPL_XX` or `MOBILE_XX` document as "the next thing to build" — the overwhelming majority of them describe work that is already real, tested, and sitting on disk. The open items are specific and named, not "whatever's left."

---

## WHAT'S ALWAYS LOADED VS. WHAT'S LOADED PER-SESSION

**Always loaded, every session, no action needed:**
- `.claude/CLAUDE.md` — the rules, architecture facts, and pointers that don't change often, read automatically from disk at the start of every session and re-read after `/compact` on long sessions

**Loaded on demand, when Claude Code actually reads the file (because it was referenced, or because the task requires it):**
- Everything under `specs/tier1_foundation/`, `specs/tier2_implementation/`, `specs/tier3_verification/`, `specs/tier4_mobile/`
- `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` and `QUORUM_SPEC_METHODOLOGY.md` (repo root)
- `handbook/` (the plain-language walkthroughs — genuinely useful for orienting on *why* something is designed the way it is, not just *what* it is)

**Every existing `IMPL_XX`/`MOBILE_XX` session document's own "Attach:" line already tells you exactly what to reference** — it just means "read these files" now, not "have these pasted into the chat":

> Document says: *Attach: `QUORUM_MASTER_REFERENCE.md`, `QUORUM_DATA_CONTRACTS.md`, `QUORUM_CONFIGURATION_CONSTANTS.md`*
>
> In practice: *"Read `specs/tier1_foundation/QUORUM_MASTER_REFERENCE.md`, `specs/tier1_foundation/QUORUM_DATA_CONTRACTS.md`, and `specs/tier1_foundation/QUORUM_CONFIGURATION_CONSTANTS.md` completely before writing anything."*

---

## HOW THE REAL TIER SYSTEM MAPS TO ACTUAL CLAUDE CODE BEHAVIOR

Quorum's tier structure is genuinely simpler than some spec-driven projects end up with — confirmed directly against the real `specs/` directory before writing this table, not assumed: there is no `tier1_amendments/`, `tier5_historical/`, or `tier6_production/` here. `DECISIONS_LOG.md` absorbed the "has this claim been superseded" role from the start, and no separate amendments layer was ever needed because tier1 documents were corrected in place, each correction disclosed directly in the document itself and logged. If a future session is tempted to create either of those directories because a similar-purpose project once had them, that's a real signal to check `STATUS_INDEX.md` and `DECISIONS_LOG.md` first — the need may already be met.

| Tier | Claude Code's relationship to it |
|---|---|
| `tier0_agent_guide/` | `SESSION_GUIDE.md` — the ordered map of every session. Read the specific session's own entry before starting it, not the whole file every time. |
| `tier1_foundation/` | The stable reference layer — the ADD's companion documents, plus the newer structural/strategy documents this guide belongs alongside. Read for ground truth on schemas, constants, the Gate's design, and the real repository layout. Corrections happen in place, disclosed directly in the document, per `DECISIONS_LOG.md` — never silently. |
| `tier2_implementation/` | The 23 real backend session specs (`IMPL_00`–`IMPL_22`). One read per session that's actually still open — check `STATUS_INDEX.md` first, since most of these already describe completed, tested work. |
| `tier3_verification/` | `STATUS_INDEX.md` is worth reading at the start of *every* session, not just ones touching something non-obvious — it's short by design specifically so this is cheap. `DECISIONS_LOG.md` is worth a scan when touching anything with real history (Gate internals, negotiation, auth). `TESTING_STRATEGY.md`/`VERIFICATION_STANDARDS.md` are read once, early, to internalize the discipline, then referenced only when a specific technique (hand-verification, fail-closed defaults) needs recalling. |
| `tier4_mobile/` | The 23 real mobile session specs (`MOBILE_01`–`MOBILE_23`). Same pattern as tier2 — check real status before assuming a session is unbuilt. |

---

## THE CUSTOM SLASH COMMANDS

The session ritual described in `QUORUM_SPEC_METHODOLOGY.md` and `CLAUDE.md`'s "Spec-reading discipline" is packaged as executable commands in `.claude/commands/`, rather than prose Claude Code has to re-interpret fresh every time:

- **`/quorum-session-start`** — the pre-session checklist: environment confirmation (which backend layout is actually on disk, which branch, which working directory), plus the full spec-read-before-touching-anything discipline, as one command instead of a ritual to remember.
- **`/quorum-verify`** — runs the actual real verification commands (`ruff check backend`, `pytest backend/tests -q`, and the real-machine caveats for `dart test`/`flutter analyze`) and reports genuine pass/fail, rather than just listing what they should be.
- **`/quorum-drift-check`** — walks the six drift patterns and four "what changed mid-project" facts in `CLAUDE.md` explicitly against whatever the current session is about to touch, since this project's own real audit found that exact category of silent drift repeatedly, in documents that existed specifically to prevent it.

These are the "verbs." `CLAUDE.md` stays "nouns" — the stable facts. Mixing the two would make `CLAUDE.md` both longer (hurting adherence — instruction-following degrades as a context file grows) and harder to update (a change to session ritual shouldn't require touching the same file as a change to an architecture fact).

---

## A REAL CORRECTION, WORTH KNOWING BEFORE IT TRIPS UP A SESSION

`self_test_harness.py`'s own docstring once claimed the real Gate "doesn't exist yet as code" — true when the harness was first written, false by the time the real Gate (`gate.review()`) shipped in `IMPL_08`, and never updated in between. Found and corrected during `MOBILE_16`, with a real `target: "stub" | "real_gate"` field added specifically so this exact category of stale claim can't recur silently — any consumer of self-test results can check which one actually produced them. **The harness itself still runs against the stub today** — the docstring fix didn't change what the harness tests against, only whether it's honest about it. Don't conflate "the false claim was corrected" with "the underlying gap was closed" — they're different, and only the first one has happened.

---

## WHAT TO DO IF CLAUDE CODE ISN'T FOLLOWING SOMETHING IN `CLAUDE.md`

Per Claude Code's own documented behavior: `CLAUDE.md` content is delivered as context, not hard-enforced configuration — there's no guarantee of strict compliance, especially for vague instructions. If something isn't being followed:

1. Run `/memory` to confirm `CLAUDE.md` is actually loaded — it should be, since it's at the project root, but confirm rather than assume.
2. Check whether the instruction was specific enough — "check `applications.status` for a real `CHECK` constraint before choosing fail-loud vs. defensive parsing" works better than "handle status fields carefully."
3. If it's a hard requirement that must never be violated regardless of in-the-moment judgment — the S3-human-approval rule is the clearest candidate in this project — that's a signal it may belong in a hook (a `PreToolUse` check), a real Claude Code mechanism for blocking an action outright, distinct from persuasive context. Not built here, since nothing in this project's current real scope has needed that level of enforcement yet, but worth knowing the option exists if the Gate's own implementation work ever does.

---

*Related: `CLAUDE.md`, `QUORUM_SPEC_METHODOLOGY.md`, `specs/tier1_foundation/QUORUM_IMPLEMENTATION_STRATEGY.md`, `specs/tier1_foundation/QUORUM_PROJECT_STRUCTURE.md`.*
