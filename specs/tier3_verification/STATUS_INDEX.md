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
| `backend/src/quorum_backend/gate/orchestration.py` | **Real, tested — CRITICAL tier.** `review()`, `run_stage_a()`, `stage_a_hard_fail()`, `run_stage_b()`, `_call_with_retry()`, `InfrastructureFailure`. No literal source ever existed anywhere in this project's real corpus for this file — a real, careful construction from the documented state machine (`QUORUM_GATE_SPECIFICATION.md` §2) and described properties, manually reviewed (see `DECISIONS_LOG` DEC-058). `Stakes` enum added to `gate/schemas.py` for the same reason — no full type definition existed anywhere either. |
| `backend/src/quorum_backend/router.py` | Real, tested (`IMPL_09`). `STAKES_TABLE` (all 11 real `ActionType`s), `get_stakes()` (raises loudly, no default), `Complexity`/`ComplexitySignals`/`compute_complexity()` — no literal source ever existed anywhere in this project's real corpus, a real construction from the documented properties + `QUORUM_CONFIGURATION_CONSTANTS.md` §1's exact stakes table. |
| `agents/*`, `negotiation/*`, `auth/*`, `security/*`, `features/*` | Not yet built in this repository. |
| Mobile (`mobile/lib/**`) | Not yet built — zero `.dart` files exist. Flutter SDK and Android SDK are not yet installed on this machine. |
| `backend/migrations/0001_initial_schema/up.sql` + `down.sql` | Real, proven against a real, local Postgres 16 + pgvector (`docker run pgvector/pgvector:pg16`) — 7 tables, 3 explicit indexes created cleanly; the `tasks.status` `CHECK` constraint genuinely rejected bad data; a real 1024-dim vector's self-distance computed as exactly 0; the `interviews`→`applications` FK genuinely rejected a nonexistent reference; the `retry_queue` partial index confirmed used by the query planner (`EXPLAIN`); `down.sql` (genuinely new, no literal spec existed) proven by a real drop→recreate cycle. Redis key/TTL patterns (`ratelimit:*` 60s, `cache:coverage_check:*` 86400s) proven against a real `redis:7-alpine` container. **No live Supabase project or Upstash Redis instance exists yet** — real account provisioning is a genuinely separate, still-open step (see open items) that this local proof cannot substitute for. |
| Cloud Run / Docker | Real `Dockerfile` + `.dockerignore` + `infra/docker/docker-compose.local.yml` + `infra/cloud_run/service.yaml.template` (`IMPL_11`). **`docker build` succeeded completely in this environment** — new, real evidence: the original environment's sandbox hit an SSL failure specific to its own container networking; this machine has no such issue. The built image was run as a real container and its `/health` endpoint returned a genuine `200 {"status":"ok"}`. No live Cloud Run service exists yet. |
| `backend/src/quorum_backend/auth/` | Real, tested (`IMPL_12`). `access_token.py` (STANDARD), `refresh_token.py`/`oauth_pkce.py` (CRITICAL, manually reviewed — see `DECISIONS_LOG` DEC-062). |
| CI pipeline | Not yet built. |
| **Backend total, this repository** | **87/87 real, passing tests** (`ruff check backend` clean). `pytest backend/tests -q` — verified live this session (Batch 2: `IMPL_09`–`12`, 16 new tests from `71`). |
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
3. Domain agents (`IMPL_13`–`17`), negotiation (`IMPL_18`–`21`), and `security/` (`IMPL_22`) — specified, not yet built in this repository. The Gate's core decision-making (all 9 validators, orchestration, and the Router) is now real.
4. `coverage_check`'s single-shared-stopword limitation — honestly documented (`DECISIONS_LOG` DEC-057), a real, deliberately-accepted trade-off from the original spec, not a bug — noted here only so it isn't lost, not as an action item.
5. `budget_check`'s body was constructed from an interface signature only, no full spec ever existed for it — worth a real cross-check against the eventual live Finance domain agent (`IMPL_16`) once that exists, to confirm the reasoning still holds.
6. `orchestration.py`'s `_call_with_retry` wraps the whole Stage B call, not Critic/Judge independently — a transient Judge-only failure re-invokes the Critic on retry, a real, minor cost inefficiency, disclosed in `DECISIONS_LOG` DEC-058, not required against by anything in the real spec but worth knowing.
7. Real demo dataset (simulated-and-real hybrid, all 5 domains) — wanted, tracked, not yet built; needs real backend/schema to load against (Phase 3 per `QUORUM_IMPLEMENTATION_STRATEGY.md`).
8. No real cloud infrastructure provisioned anywhere (Supabase/Upstash/Cloud Run/Gemini/Groq) — free-tier accounts to be created when a session first needs one. The schema/key patterns are now proven against real *local* Postgres+pgvector and Redis (`IMPL_10`), and the real Docker image builds and runs cleanly in this environment (`IMPL_11`) — neither substitutes for the real cloud accounts themselves, still genuinely open.
9. Everything else in the 46-session `IMPL_XX`/`MOBILE_XX` plan not listed above — none of it is real in this repository yet.

## Update protocol

Rewritten — not appended to — at the end of every single session, per its own stated discipline. Never let this file describe a session as done without a real, live-verified reason to believe so, and never let it restate the specification narrative's claims about a codebase this repository doesn't actually contain.

---

*Read this file first, every session, before anything else — including before `CLAUDE.md`. If it disagrees with `DECISIONS_LOG.md`'s entries before DEC-050, this file is correct — see DEC-050 for why.*
