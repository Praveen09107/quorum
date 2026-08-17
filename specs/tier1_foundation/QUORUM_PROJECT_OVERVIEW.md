# QUORUM — Project Overview

**Tier:** `tier1_foundation` · **Volatility:** Low — this document describes purpose and orientation, which don't change session to session. If you're looking for current build state, this is the wrong document; go to `specs/tier3_verification/STATUS_INDEX.md` instead.

**What this document is not:** a re-explanation of Quorum's architecture. That already exists, in more depth and rigor than could usefully be repeated here, in `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` (exhaustive) and `specs/tier1_foundation/QUORUM_MASTER_REFERENCE.md` (condensed). Duplicating that content here would create exactly the kind of second, driftable "source of truth" this project's own full specification audit found and fixed repeatedly. This document's real job is different: **why this project exists, what success actually looks like, and where to look for anything specific** — an entry point, not a competitor to the documents it points to.

---

## Why this project exists

Quorum is a portfolio project built by a solo developer — beginner-level in hands-on coding, working in what's been called a "vibe coding" style: providing direction and approval while an AI coding agent generates the actual implementation. There is no other developer reviewing this code, and no human backstop catching a subtle bug before it ships. **That fact is not incidental context — it's the reason this project's verification discipline (the Gate architecture it implements, and the session/testing discipline used to build it) carries more real weight than it would in a traditionally-reviewed codebase.**

The real, stated career goal behind this project: demonstrating genuine AI engineering capability in service of becoming an AI Engineer professionally. That means the bar for this project isn't "does it demonstratively work in a demo" — it's "would a senior AI engineer reviewing this codebase find real, defensible engineering judgment throughout it." Every architectural decision should be able to survive the question "why did you build it this way, and what did you consider instead" — not because a reviewer is guaranteed to ask, but because building as if they will produces a genuinely better system than building as if no one's watching.

## What Quorum actually is, in three sentences

A mobile-first personal-operations assistant — email, calendar, tasks, finance, career — built around one architectural thesis: an autonomous AI system shouldn't be trusted because it says the right things, it should be *checked*, with the checking itself made visible. Every proposed action passes through an independent verification Gate before a person ever sees it, with the Gate's own failures logged with the same prominence as its successes. The mobile app is the surface where a person actually watches this happen — approving Gate-verified actions, resolving cross-domain conflicts through a real negotiation mechanism, and reading an honest record of what the system got right and what it got wrong.

For the full technical depth behind that summary, read the ADD. For the plain-language walkthrough of the finished system, read `handbook/HANDBOOK_05_COMPLETE_APP.md`.

## Where things actually stand right now

Not restated here as a number — that's exactly the drift pattern `CLAUDE.md` names explicitly and this document holds itself to the same rule. **Read `specs/tier3_verification/STATUS_INDEX.md` directly for the real, current, live-verified state:** what's built, what's tested, what's genuinely still open. It's short by design specifically so checking it is never expensive enough to skip.

What's safe to say without a number: the specification and design phase is complete — the full architecture, every backend and mobile session, and a full adversarial audit of the entire specification set. What remains is implementation-adjacent work belonging to the physical and infrastructural world (real device testing, real cloud provisioning, real integration wiring) rather than more design or specification. `specs/tier1_foundation/QUORUM_IMPLEMENTATION_STRATEGY.md` lays out exactly what that remaining work is, in order, with a real gate between each phase.

## The reading map — what to read for what kind of question

This is the part genuinely missing from every other document in this project: a curated path through the real specification set, organized by the *question being asked*, not by document name.

| If you need to know... | Read this | Not this |
|---|---|---|
| What's actually built and tested, right now | `specs/tier3_verification/STATUS_INDEX.md` | Any document's own embedded status claims — those are historical snapshots at best |
| Why a specific decision was made, or whether an old claim is still true | `specs/tier3_verification/DECISIONS_LOG.md` | Guessing, or assuming a document's first draft is its final state |
| The exhaustive technical architecture | `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` | This document — it deliberately doesn't repeat that depth |
| A specific schema, endpoint, or hardcoded constant | `specs/tier1_foundation/QUORUM_DATA_CONTRACTS.md` / `QUORUM_CONFIGURATION_CONSTANTS.md` | Inferring one from a session document's example — check the real source |
| The Gate's full design | `specs/tier1_foundation/QUORUM_GATE_SPECIFICATION.md` | The ADD's summary of it — this document is the authoritative depth |
| What phase of remaining work is next, and its real gate | `specs/tier1_foundation/QUORUM_IMPLEMENTATION_STRATEGY.md` | Assuming "the next `IMPL_XX` number" — most of those are already real and complete |
| The repository's file/folder layout, current and target | `specs/tier1_foundation/QUORUM_PROJECT_STRUCTURE.md` | Assuming the target `src/` layout already exists — check which is real first |
| How to actually run a session with Claude Code specifically | `specs/tier1_foundation/QUORUM_CLAUDE_CODE_SPEC_USAGE_GUIDE.md` | Re-deriving the ritual from scratch — it's already packaged as `/quorum-session-start` |
| The non-negotiable rules and architecture facts for every session | `.claude/CLAUDE.md` | This document — that one is operational, this one is orientational |
| Why the design turned out this way, told plainly | `handbook/` (six entries, `HANDBOOK_00` through `05`) | Nothing — this is genuinely the most accessible entry point if the ADD feels dense on a first read |

## What "done" actually looks like

Not "the demo works once." The real, stated gate for the whole project — defined precisely in `QUORUM_IMPLEMENTATION_STRATEGY.md`'s Phase 6 — is the full pipeline (lint → test → build → golden suite → health-checked deploy) running green against a real, public production target, not `localhost` and not a staging placeholder. Everything before that phase is real, necessary groundwork; none of it is the finish line on its own.

---

*Related: `.claude/CLAUDE.md`, `QUORUM_SPEC_METHODOLOGY.md`, `specs/tier1_foundation/QUORUM_IMPLEMENTATION_STRATEGY.md`, `specs/tier3_verification/STATUS_INDEX.md`.*
