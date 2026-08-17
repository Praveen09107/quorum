# QUORUM — Status Index

**Tier:** `tier3_verification` · **Volatility:** Living — updated after every single session, without exception
**Purpose:** what's actually true right now, in *this* repository. This file is intentionally short — its job is to be cheap enough to keep accurate that it never goes stale. If this file and any other document disagree, this file is correct until proven otherwise; see `DECISIONS_LOG.md` for why.

**A real, load-bearing correction, disclosed here because it's exactly the kind of thing this file exists to catch:** this document previously described the entire backend and mobile app as complete — 23/23 backend sessions, 156 passing tests, 23 mobile screens — carried forward from the specification corpus's own narrative. **That narrative describes a different, no-longer-accessible environment.** Direct, repeated, exhaustive verification in *this* repository (file counts, `git log`, a full search of this machine — see `DECISIONS_LOG.md` DEC-050) found none of that code actually present here. This file is rewritten from this point forward to describe only what's real and verified in this actual repository, never the specification narrative's own claims about a codebase this repo doesn't contain.

---

## What's real, right now, in this repository

| Layer | Status |
|---|---|
| `backend/src/quorum_backend/gate/schemas.py` | Real, tested. Full `QUORUM_DATA_CONTRACTS.md` §1 schema set (`ActionType`, `EvidenceRef`, `Finding`, `Objection`, `ContextSnapshot`, `ActionProposal`, `GateVerdict`, `ResourceClaim`, `Position`, `ImpactDelta`). `NegotiationOption` deliberately not yet added — no session has needed it yet. |
| `backend/src/quorum_backend/gate/validators.py` | **All 9 real Stage A validators now exist and are tested — Stage A is complete.** `budget_check`, `temporal_fact_check` (predate the numbered session sequence per the batch guide's own convention; built alongside `IMPL_07` to close this gate, since their full bodies were never assigned their own session — `budget_check`'s body specifically is a real, reasoned construction, not a copy of a given spec, since none existed). `availability_check` (`IMPL_01`). `deadline_conflict_check` (`IMPL_02`). `recipient_check` (`IMPL_03`). `commitment_check` (`IMPL_04`). `pii_leak_check` (`IMPL_05`) — full integration still needs `MOBILE_03`'s real flagged-span output, not yet built here. `provenance_check` (`IMPL_06`) — CRITICAL tier, manually reviewed (see DEC-056). `coverage_check` (`IMPL_07`) — has one honestly-documented limitation (see `DECISIONS_LOG` DEC-057): a single shared stopword satisfies the real default `min_shared_terms=1` threshold; this is the same trade-off the original spec already named and accepted, not a new open question. |
| `backend/gate/prompts.py` | Real, but only `COVERAGE_EXTRACTION_PROMPT`/`build_coverage_extraction_prompt` (`IMPL_07`) — no literal spec text existed for this prompt anywhere in the corpus, so its wording is a real, reasoned construction, flagged as such. `CRITIC_SYSTEM_PROMPT`/`JUDGE_SYSTEM_PROMPT` deliberately not yet built — nothing needs them until `IMPL_08`. |
| `orchestration.py`, `router.py`, `agents/*`, `negotiation/*`, `auth/*`, `security/*`, `features/*` | Not yet built in this repository. |
| Mobile (`mobile/lib/**`) | Not yet built — zero `.dart` files exist. Flutter SDK and Android SDK are not yet installed on this machine. |
| Infrastructure | Nothing provisioned — no Supabase project, Cloud Run service, or Upstash Redis instance exists yet. |
| CI pipeline | Not yet built. |
| **Backend total, this repository** | **53/53 real, passing tests** (`ruff check backend` clean). `pytest backend/tests -q` — verified live this session. |
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
3. `backend/gate/orchestration.py` (`gate.review()`) — specified, not yet built. **All 9 Stage A validators are now real** — this is genuinely unblocked, the next real session.
4. `coverage_check`'s single-shared-stopword limitation — honestly documented (`DECISIONS_LOG` DEC-057), a real, deliberately-accepted trade-off from the original spec, not a bug — noted here only so it isn't lost, not as an action item.
5. `budget_check`'s body was constructed from an interface signature only, no full spec ever existed for it — worth a real cross-check against the eventual live Finance domain agent (`IMPL_16`) once that exists, to confirm the reasoning still holds.
6. Real demo dataset (simulated-and-real hybrid, all 5 domains) — wanted, tracked, not yet built; needs real backend/schema to load against (Phase 3 per `QUORUM_IMPLEMENTATION_STRATEGY.md`).
7. No cloud infrastructure provisioned anywhere (Supabase/Upstash/Cloud Run/Gemini/Groq) — free-tier accounts to be created when a session first needs one.
8. Everything else in the 46-session `IMPL_XX`/`MOBILE_XX` plan not listed above — none of it is real in this repository yet.

## Update protocol

Rewritten — not appended to — at the end of every single session, per its own stated discipline. Never let this file describe a session as done without a real, live-verified reason to believe so, and never let it restate the specification narrative's claims about a codebase this repository doesn't actually contain.

---

*Read this file first, every session, before anything else — including before `CLAUDE.md`. If it disagrees with `DECISIONS_LOG.md`'s entries before DEC-050, this file is correct — see DEC-050 for why.*
