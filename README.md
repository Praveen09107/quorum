# Quorum

A mobile-first, hybrid edge-cloud, multi-agent platform that introduces
trust into autonomous AI through independent verification, collaborative
agent negotiation, and safe real-world action execution — a personal
operations assistant across Email, Calendar, Tasks, Finance, and Career.

**The core idea:** don't ask to be trusted — be checked, and show the
checking. Every proposed action passes through an independent Gate
before it reaches a person, and the Gate's own failures are logged with
the same visibility as its successes.

## Current real status

Never restated here — this file would go stale the way several others
in this project once did, and the fix that worked was refusing to
duplicate the number a second time. The real, live-verified state
lives in one place:

**`specs/tier3_verification/STATUS_INDEX.md`**

## Getting started

1. Read `specs/tier1_foundation/QUORUM_PROJECT_STRUCTURE.md` — the map
   of this repository.
2. Read `QUORUM_SPEC_METHODOLOGY.md` — how development sessions work
   here.
3. Run `scripts/setup_dev_env.ps1` for local backend + mobile setup.
4. Before starting any new work, find its session document under
   `specs/tier2_implementation/` (backend) or `specs/tier4_mobile/`
   (mobile) — that document is the real spec, not this README.

## Architecture

The full design lives in `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md`. The
plain-language walkthrough lives in `handbook/`, six entries from "how
sessions work" through "the complete app."