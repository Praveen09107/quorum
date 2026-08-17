# QUORUM — Status Index

**Tier:** `tier3_verification` · **Volatility:** Living — updated after every single session, without exception
**Purpose:** what's actually true right now, in *this* repository. This file is intentionally short — its job is to be cheap enough to keep accurate that it never goes stale. If this file and any other document disagree, this file is correct until proven otherwise; see `DECISIONS_LOG.md` for why.

**A real, load-bearing correction, disclosed here because it's exactly the kind of thing this file exists to catch:** this document previously described the entire backend and mobile app as complete — 23/23 backend sessions, 156 passing tests, 23 mobile screens — carried forward from the specification corpus's own narrative. **That narrative describes a different, no-longer-accessible environment.** Direct, repeated, exhaustive verification in *this* repository (file counts, `git log`, a full search of this machine — see `DECISIONS_LOG.md` DEC-050) found none of that code actually present here. This file is rewritten from this point forward to describe only what's real and verified in this actual repository, never the specification narrative's own claims about a codebase this repo doesn't contain.

---

## What's real, right now, in this repository

| Layer | Status |
|---|---|
| `backend/src/quorum_backend/gate/schemas.py` | Real, tested. Full `QUORUM_DATA_CONTRACTS.md` §1 schema set (`ActionType`, `EvidenceRef`, `Finding`, `Objection`, `ContextSnapshot`, `ActionProposal`, `GateVerdict`, `ResourceClaim`, `Position`, `ImpactDelta`). `NegotiationOption` deliberately not yet added — no session has needed it yet. |
| `backend/src/quorum_backend/gate/validators.py` | Real, tested. `CalendarAdapter` Protocol + `availability_check` (`IMPL_01`). `TasksAdapter` Protocol + `deadline_conflict_check` (`IMPL_02`). The other 7 registry validators (`TemporalFactCheck`, `BudgetCheck`, `RecipientCheck`, `CommitmentCheck`, `PIILeakCheck`, `ProvenanceCheck`, `CoverageCheck`) are specified but not yet built here. |
| `backend/gate/prompts.py`, `orchestration.py`, `router.py`, `agents/*`, `negotiation/*`, `auth/*`, `security/*`, `features/*` | Not yet built in this repository. |
| Mobile (`mobile/lib/**`) | Not yet built — zero `.dart` files exist. Flutter SDK and Android SDK are not yet installed on this machine. |
| Infrastructure | Nothing provisioned — no Supabase project, Cloud Run service, or Upstash Redis instance exists yet. |
| CI pipeline | Not yet built. |
| **Backend total, this repository** | **18/18 real, passing tests** (`ruff check backend` clean). `pytest backend/tests -q` — verified live this session. |
| **Mobile total, this repository** | **0** — not started. |

## Environment, confirmed real (see `quorum-environment-constraints` for full detail if reading this outside Claude Code)

- Machine: Intel i5-12500H, 16GB RAM, RTX 3050 4GB, Windows.
- Python 3.13.1, virtualenv at repo root (`.venv/`), `pydantic==2.10.4`, `pytest==8.3.4`, `pytest-asyncio==0.25.0`, `ruff==0.8.4` — all pinned, all installed via `pip install -e "./backend[dev]"`.
- Git repository, connected to `https://github.com/Praveen09107/quorum` (public). One branch per session, merged to `main` only after real verification and explicit approval.
- Flutter SDK: not installed. Android SDK / emulator: not installed. No physical Android device available.
- Cloud accounts (Supabase, Upstash, Cloud Run, Gemini, Groq): not yet created — free-tier only, created when a session actually needs one.

## Known open items — the complete list for this repository

1. On-device primary model (Gemma 4 E4B vs. Llama 3.2 3B) — unresolved, needs Sprint 0 (`IMPL_00`), which itself needs Flutter SDK + a real or emulated Android device (≥4GB RAM) not yet set up.
2. Flutter llama.cpp plugin selection — same, resolved by the same session.
3. Remaining backend validators (`TemporalFactCheck`, `BudgetCheck`, `RecipientCheck`, `CommitmentCheck`, `PIILeakCheck`, `ProvenanceCheck`, `CoverageCheck`) — specified, not yet built in this repository.
9. `backend/gate/orchestration.py` (`gate.review()`) — specified, not yet built; needs all Stage A validators first.
10. Real demo dataset (simulated-and-real hybrid, all 5 domains) — wanted, tracked, not yet built; needs real backend/schema to load against (Phase 3 per `QUORUM_IMPLEMENTATION_STRATEGY.md`).
11. No cloud infrastructure provisioned anywhere (Supabase/Upstash/Cloud Run/Gemini/Groq) — free-tier accounts to be created when a session first needs one.
12. Everything else in the 46-session `IMPL_XX`/`MOBILE_XX` plan not listed above — none of it is real in this repository yet.

## Update protocol

Rewritten — not appended to — at the end of every single session, per its own stated discipline. Never let this file describe a session as done without a real, live-verified reason to believe so, and never let it restate the specification narrative's claims about a codebase this repository doesn't actually contain.

---

*Read this file first, every session, before anything else — including before `CLAUDE.md`. If it disagrees with `DECISIONS_LOG.md`'s entries before DEC-050, this file is correct — see DEC-050 for why.*
