# QUORUM — Architecture Design Document (ADD)

**Version:** 2.0 (Authoritative, Full-Depth) · **Date:** 2026-08-13
**Status:** Supersedes v1.0. This is the complete, comprehensive system architecture reference. Four companion documents carry implementation-precision detail this document points to rather than duplicates: `QUORUM_MASTER_REFERENCE.md` (condensed index), `QUORUM_DATA_CONTRACTS.md` (every schema), `QUORUM_CONFIGURATION_CONSTANTS.md` (every number), `QUORUM_GATE_SPECIFICATION.md` (the Gate in full, with real prompts). Where those documents hold the deepest precision, this document says so explicitly and does not restate it — a restated copy is a drift risk, a pointer is not.

**Audience:** engineers beginning implementation. Assumes no prior context.

---

# 1. Executive Summary

Quorum is a mobile-first, hybrid edge–cloud, multi-agent platform whose purpose is engineering **trust** into autonomous AI action — through independent verification, collaborative negotiation, adaptive intelligence routing, and safe real-world execution. It is deployed as a personal-operations assistant spanning email, calendar, tasks, finance, and career management for busy young professionals. The assistant is the **proving ground** for the trust architecture; the trust architecture is the actual product.

Three claims anchor every decision in this document:

1. Agent actions can be **systematically verified** — §6, full detail in `QUORUM_GATE_SPECIFICATION.md`.
2. Cross-domain conflicts can be **resolved transparently** — §8.
3. Trust can be **measured, not asserted** — §17.

**Current real implementation status, stated up front because it changes how this document should be read:** this is not a purely aspirational design — real, tested code exists against every layer described below, all the way through a working mobile app. **The exact current count lives in `specs/tier3_verification/STATUS_INDEX.md`, re-verified live every session — not here, and not in §19, which is a pointer to the same place rather than a restated number.** This document held a literal, dated snapshot here through v2.0 (34 tests); it drifted, and now doesn't hold one at all, by design.

---

# 2. System Overview & Topology

```
┌───────────────────────── PHONE (Flutter) ─────────────────────────┐
│ UI (Riverpod) · polling client (1–2s interval during Gate runs)   │
│ · FCM push                                                          │
│ Local persistence: Drift/SQLite                                    │
│   - offline action queue (pending sync)                            │
│   - read-only mirror: tasks / budget / near-term calendar          │
│     (refreshed on every successful backend sync)                   │
│ ┌──────────── EDGE INTELLIGENCE ────────────┐                     │
│ │ SLM: Full tier (≥8GB RAM) / Light tier      │                    │
│ │   (4–8GB) / Cloud-only (<4GB) — §12          │                   │
│ │ Privacy Gate: rule layer (regex) +           │                   │
│ │   SLM classification layer                   │                   │
│ │ CalendarProvider (device_calendar pkg,       │                   │
│ │   no OAuth)                                   │                  │
│ │ Extended-Outage local drafter + local Stage A │                  │
│ │ Computed-state engine (identical math, live   │                  │
│ │   or mirrored — real code both sides, §11.4)  │                  │
│ └──────────────────────────────────────────────┘                  │
└───────────────┬─────────────────────────────────────────────────────┘
                │ HTTPS (JWT: 15-min access, rotating refresh, revocable)
┌───────────────▼──────── COMPUTE: GOOGLE CLOUD RUN ─────────────────┐
│ Region: a free-tier-eligible US region, same region as Supabase    │
│ Serverless, scale-to-zero, concurrency = 1 (explicit, §13.1)       │
│ FastAPI (modular monolith) — REST only, no persistent WebSocket    │
│ ├── Router: hardcoded stakes table + complexity signal (§6.1)      │
│ ├── LangGraph orchestrator, Postgres-checkpointed (§7)             │
│ │     ├── Domain agents: Email·Calendar·Tasks·Finance·Career (§9)  │
│ │     ├── Negotiation subgraph (§8)                                │
│ │     └── Proactive-agent endpoints, invoked directly by pg_cron   │
│ │           (no persistent worker daemon anywhere)                 │
│ ├── THE GATE — full spec in QUORUM_GATE_SPECIFICATION.md           │
│ │     ├── Stage A: 9 validators registered, 2 implemented (§6.3)   │
│ │     └── Stage B: Critic (Groq/Llama 3.3 70B) ≠ Generator/Judge   │
│ │           (Gemini Flash) — real prompts, tested (§6.4)           │
│ ├── Capacity Manager: single LLM-call chokepoint, multi-provider   │
│ │     fallback with backoff (§11.3)                                │
│ ├── Self-hosted on this same compute: Qwen3-Embedding-0.6B,        │
│ │     router classifier (classical ML), injection guard (pretrained)│
│ └── MCP tool layer — two-layer authorization (§14.3)               │
└──────┬─────────────────┬─────────────────┬─────────────────────────┘
       │                 │                 │
┌──────▼──────┐  ┌───────▼──────┐  ┌───────▼────────┐  ┌─────────────┐
│ Supabase     │  │ Upstash      │  │ Langfuse Cloud │  │ Cloud       │
│ Postgres +   │  │ Redis        │  │ (AI/agent      │  │ Logging     │
│ pgvector     │  │ (cache/rate- │  │  traces only)  │  │ (infra      │
│ same region  │  │  limit)      │  │                │  │  errors     │
│ as Cloud Run │  │              │  │                │  │  only)      │
│ pg_cron +    │  │              │  │                │  │             │
│ pg_net       │  │              │  │                │  │             │
│ (scheduler)  │  │              │  │                │  │             │
└──────────────┘  └──────────────┘  └────────────────┘  └─────────────┘
       ▲
       │ low-frequency keep-alive ping (every 3–4 days)
┌──────┴──────────┐
│ GitHub Actions   │  ← also runs CI/CD (lint, test, Trivy, build)
│ (repurposed,     │
│  not primary      │
│  scheduler)        │
└───────────────────┘
```

Two properties define this system more than any individual box: **every action with real-world, irreversible consequences requires an explicit human tap, in every mode, no exception** — enforced structurally, not just by convention (§6.6, §11.5); and **the phone is never a dependency, only an enhancement** — full cloud-only operation is guaranteed, and Extended-Outage Mode preserves meaningful functionality at reduced guarantees rather than failing outright (§11).

---

# 3. Core Design Principles

**3.1 — Machines verify facts; models judge what machines cannot.** A correctness property, not a cost optimization. A database lookup is categorically more reliable than any model, at any size, for verifying a factual claim — this holds regardless of model capability improvements over time.

**3.2 — Fixed workflow graphs, never open-ended autonomous planning.** The decision path must be reproducible and auditable *in advance*. LangGraph's explicit state-graph model is chosen specifically because it makes this a structural property, not a hoped-for behavior.

**3.3 — On-device is an enhancement, never a dependency.** The app is 100% functional with zero on-device model present. Three separable reasons justify it existing at all: privacy, offline capability, trivial-latency responsiveness.

**3.4 — Trust degrades in usefulness before it degrades in integrity.** Under any failure — network loss, provider outage, ambiguous data — the system does less, more slowly, with more friction. It never verifies less than a situation requires.

---

# 4. Target User & Product Framing

**Final framing:** busy young professionals broadly — deliberately broadened from an original placement-season-student-only scope. This broadening had one material, resolved consequence: the original headline negotiation trigger (interview vs. deadline vs. budget) is rare for a general professional. Resolution (§8.6): the negotiation trigger was widened to everyday tensions — commitment vs. remaining capacity, spontaneous spend vs. known upcoming cost — so the negotiation machinery fires at a frequency matching the broadened user's actual week, not just placement season.

---

# 5. The Router — Stakes and Complexity

**Full schema and constant detail:** `QUORUM_DATA_CONTRACTS.md` §1.1–1.2 and `QUORUM_CONFIGURATION_CONSTANTS.md` §1, §3.

**Stakes** is a hardcoded, closed-enum lookup by `ActionType` — never learned, never inferred from model confidence. Rationale: a safety boundary must be auditable by inspection. Adding a new `ActionType` requires a corresponding stakes-table row in the same change — there is no default; an unmapped action type is a bug.

**Complexity** is computed from structural features (domain count touched, temporal/financial content, ambiguity flags). It cold-starts as hardcoded rule thresholds and upgrades to a trained classical-ML classifier (logistic regression or LightGBM — **never a neural fine-tune**, consistent with the project's hard no-fine-tuning constraint) once the nightly Tier-1/Tier-2 replay job produces sufficient labeled data. This upgrade is self-funding: the replay/logging infrastructure exists anyway for calibration measurement (§17.3), so training the classifier costs nothing additional once real usage exists. No fixed data-volume trigger is set — this is deliberately left as an observed-from-real-data decision (§22), not guessed.

**Why not self-assessed model confidence:** rejected permanently. Small models produce confident-sounding text regardless of correctness. Asking a model "how sure are you" conflates two independent questions — is this complex? is this risky? — into one unreliable signal.

---

# 6. The Trust Layer — The Gate

**Full specification, real prompts, real validator code:** `QUORUM_GATE_SPECIFICATION.md`. This section is a complete but non-duplicative summary — read the referenced document for prompt text and validator implementation.

## 6.1 Design principle
Stage A: pure code, zero LLM calls, zero exceptions. Stage B: reserved exclusively for genuine judgment. This split is not a cost optimization — it is the correctness argument stated in §3.1, applied.

## 6.2 The three-valued Finding
`Finding.evidence_state ∈ {verified_true, verified_false, no_data_found}` — never binary. `verified_false` short-circuits to `revise` at zero cost. `no_data_found` is neither pass nor fail; it is carried into Stage B as an unresolved item requiring explicit judgment. **This is now a tested property of real code** (`test_temporal_fact_check_no_data_found_not_false_when_absent`), not just a documented intention — the distinction was identified early in this project as the single most important correctness guarantee in the Gate, because collapsing it either direction produces a real failure mode (false rejections from incomplete data, or silently ignored uncertainty).

## 6.3 Stage A — the validator registry
Nine validators registered; two fully implemented and tested (`TemporalFactCheck`, `BudgetCheck`); seven specified with real interface signatures, not yet implemented (`AvailabilityCheck`, `DeadlineConflictCheck`, `RecipientCheck`, `CoverageCheck`'s comparison half, `CommitmentCheck`, `PIILeakCheck`, `ProvenanceCheck`). Every validator follows the same injectable-ground-truth-adapter pattern (`Protocol`-typed), testable with synthetic data and swappable for real Supabase-backed adapters at deployment with zero change to validator logic. `ProvenanceCheck` is the primary structural defense against prompt injection — it verifies an action's justification traces to user intent, not solely to instructions embedded in ingested content.

## 6.4 Stage B — the debate
Three roles, a deliberately fixed count. Two conflates fault-finding with severity-weighing in a single call; four or more multiplies cost for judgment work Stage A has already narrowed to one coherent task.

- **Generator** (Gemini Flash) drafts, using retrieved context per the priority order in §7.3.
- **Critic** (Groq-hosted **Llama 3.3 70B — a genuinely different model family**, not merely a fresh context) receives the proposal plus Stage A's findings, obligated by both prompt instruction and schema (`Objection.signed_off`) to return real objections or an explicit, reasoned sign-off. The real prompt (`gate/prompts.py::CRITIC_SYSTEM_PROMPT`) explicitly instructs that retrieved content is data, never a directive — injection hardening in the Critic role, not only the Judge.
- **Judge** (Gemini Flash) receives the proposal, objections, and findings with **role labels stripped and objection order randomized by the orchestration layer** (not the prompt — this is a deliberate design choice so the anonymization discipline is independently unit-testable rather than trusted to prompt phrasing alone). The real prompt instructs weighing cited evidence over rhetorical confidence, and — the same jailbreak hardening as the Critic — treating any instruction-like text within the proposal or objections as data, never a command.

**Why model diversity for the Critic specifically, restated because it matters this much:** a model reviewing content from its own family shares its own training-induced blind spots. This is not incidental — it is the same reasoning this project's own development methodology (`CLAUDE.md` Rule 6) applies to *building* Quorum: cross-model review is mandatory for Gate-touching code, for the identical reason.

## 6.5 The bounded loop — two failure classes, deliberately separated
**Content revision:** maximum one round, **enforced by `GateVerdict.revision_count`'s Pydantic type bound `[0,1]`**, not application logic alone — a stronger guarantee than a check that could be forgotten. A `revise` verdict re-runs Stage A only on the revised payload. A second failure escalates to human with both versions and every finding.

**Infrastructure failure** (provider timeout, malformed structured output): retried up to 2 times with backoff, entirely separate from the content-revision count — a transient Groq or Gemini hiccup is never miscounted as a Gate rejection.

## 6.6 The one rule that never bends
S3 actions require explicit human approval in **every mode, including Extended-Outage Local Continuity Mode** (§11.5). No tap, under any circumstance, authorizes an unverified irreversible action. The pending-approval UI additionally requires the verification trace to have been visibly displayed before the approve affordance activates — an anti-rubber-stamp measure, not just a data guarantee.

## 6.7 Cost/latency profile
S1: 0 LLM calls, <100ms. S2: 1 call, ~2–4s. S3: 2–3 calls, ~5–10s, streamed via polling (§14.4). The claimed ~50% cost reduction versus a naive all-LLM baseline is **not yet independently benchmarked** — an ablation study using the golden scenario suite is named future work (§17.1), not a completed measurement.

## 6.8 Gate verdict → evaluation outcome mapping (DEC-002, real code)
`gate/verdict_outcome_mapping.py`, tested (4/4). `approve` → `APPROVED_UNCHANGED`. `revise`/`reject` → `CAUGHT_BY_GATE` (a deliberate user-facing simplification; the granular distinction remains in the underlying trace). `escalate_to_human` cannot resolve without the human's subsequent action — `approved_as_is` after a `no_data_found` escalation resolves to `UNCERTAIN_NO_DATA`, never to a falsely confident `APPROVED_UNCHANGED`.

---

# 7. Multi-Agent Orchestration

## 7.1 Framework — LangGraph
Chosen over AutoGen (optimized for open-ended conversational dynamics, not bounded state transitions — the wrong pattern given §3.2), CrewAI (abstracts away the explicit graph structure the auditability claim depends on), and a hand-rolled state machine (real checkpointing and human-in-the-loop interrupts are non-trivial to build correctly; LangGraph provides both, tested by the broader ecosystem). Checkpointed to Supabase Postgres — this pairs unusually well with the serverless compute decision (§13.1): resuming across invocations is exactly what checkpointing already does, so a decision made for auditability reasons turned out to also solve a deployment-model problem for free.

## 7.2 Agent specialization — domain-based
Not capability-based (would require a shared agent to hold every domain's tool access, breaking least-privilege) and not monolithic (no natural least-privilege boundary, no clean mapping to negotiation's distinct per-domain voices — the rejected autonomous-planning pattern from §3.2 in agent-count form). One decomposition simultaneously produces: a least-privilege security boundary (§14.3), a UX requirement (negotiation's distinct voices, §8), and a reliability property (independent, parallelizable failure units). This convergence is evidence the decomposition carves the problem at a genuine joint, not an arbitrary one.

## 7.3 Memory architecture — four tiers, explicit

| Tier | What | Where | Lifespan |
|---|---|---|---|
| Working | Current task's live context | LangGraph graph state | Ephemeral |
| Episodic | Specific past decisions | mem0 | Persistent, retrievable |
| Semantic | Generalized stable preferences | mem0 EMA weight vectors | Persistent, incremental |
| Retrieval | Large corpus, relevance-retrieved | pgvector (Qwen3-Embedding-0.6B) | Persistent, similarity-searched |

**Context-assembly priority order** (fixed, not ad hoc per call): immediate thread content > Stage-A-verified ground truth > retrieved historical context > general preference weights. Verified facts outrank retrieved history because they're verified; specific history outranks general preferences because it's specific to the situation. Long threads are summarized via one cached extraction call (reusing the same pattern as `CoverageCheck`'s extraction) rather than truncated or dumped whole.

## 7.4 Internal structure — modular monolith
One deployable unit, internally enforced package boundaries (`gate/` imports nothing from `agents/` — a real, checkable property of the actual repo structure, not just a stated intention). This makes the Gate's separability claim literally true in code at zero deployment-complexity cost, appropriate to this system's actual scale. Rejected: full microservices (real operational tax — network overhead, service discovery, inter-service auth — for a scale that doesn't need it; the modular monolith already delivers the same least-privilege and separability properties without the tax).

## 7.5 Agent-to-tool protocol — MCP, two-layer authorization
Full detail: §14.3.

---

# 8. The Negotiation Protocol

**Full schemas:** `QUORUM_DATA_CONTRACTS.md` §1.8 (`Position`, `ResourceClaim`, `ImpactDelta` — all real, tested Pydantic models).

## 8.1 Trigger — computation, not inference
Resource claims (time/money/effort) extracted from a proposal are checked against each domain's state; ≥2 conflicted domains fires the subgraph. Facts are resolved by lookup **before** positions are generated — agents argue priorities, never facts, which structurally eliminates most degenerate debate before it can start.

## 8.2 Position generation
One parallel call per conflicted domain; uninvolved domains stay silent — zero wasted calls, zero added latency since the calls are independent. Each `Position` includes a `proposed_resolution` field, not just a stated concern.

## 8.3 Option synthesis — merge, not invent
The synthesis call combines each domain's own `proposed_resolution` into exactly 2 complete options + "do nothing," rather than authoring solutions from nothing. **This directly closes what this project's own review process identified as its single weakest architectural point** — an unscaffolded LLM call carrying too much unconstrained responsibility. Merging already-generated, domain-scoped proposals is a meaningfully more bounded task.

## 8.4 Impact simulation — zero LLM calls, pure code
Each option applies to a copy of domain state; standing metrics (`deadline_slack_hours`, `budget_remaining_fraction`, `task_hours_committed` — the exact `ImpactDelta.metric` enum values, §1.8 of `QUORUM_DATA_CONTRACTS.md`) are recomputed and emitted as typed deltas. **The numbers are reproducible; only the narration is generative.** Say this sentence precisely in any explanation of the system — it is the single most important honesty distinction in the whole negotiation design.

## 8.5 Preference weights — explainable, gated
An EMA-updated vector over `{deadline_protection, meeting_accommodation, budget_discipline, rest_buffer}`, gated behind a minimum of **5 real observed choices** before influencing option ordering — before that threshold, options display in neutral order. If the user disagrees with the weighted ordering twice consecutively in one category, the system asks explicitly rather than continuing to guess. Weights are visible and editable in the You tab (§12.3), never a hidden black box.

## 8.6 Everyday-conflict widening — the resolution to §4's consequence
The negotiation trigger extends beyond rare literal three-domain collisions to frequent daily tensions: commitment-vs-remaining-capacity, spontaneous-spend-vs-known-upcoming-cost, attention-triage-across-competing-priorities. Same machinery (§8.1–8.4), aimed at a frequency that actually matches the broadened target user's real week rather than a placement-season-only scenario.

## 8.7 Degenerate cases
Deadlock (no good option exists) still yields exactly the same 2-options-plus-do-nothing shape, with **honest, not optimistic, deltas** — the simulator does not manufacture a falsely reassuring picture. More than 3 conflicted domains still produces exactly 2 complete options; each candidate option is validated for internal consistency by Stage-A-style lookups before display.

---

# 9. Domain Architecture

Five action domains, one context substrate, briefing enrichments. Career was added deliberately — the only candidate that scored cleanly on real consequential actions, genuine conflict surface, ₹0 feasibility, and direct alignment with the target user's actual life, against a wider field of candidates considered and rejected (WhatsApp/Telegram messaging, health/fitness, travel booking, documents/Drive) during original domain selection.

## 9.1 Email — the spine
Gmail API, OAuth with server-side token exchange (full flow: §14.2). Ingestion via polling (5–15 min interval; `watch`/Pub/Sub push is a documented, not-yet-implemented upgrade path). **Style-Conditioned Replies** (real, tested — `backend/features/style_reply.py`): drafts conditioned via few-shot examples retrieved from the user's own past sent mail to the *same specific contact*, using the same pgvector retrieval substrate as everything else — not generic AI phrasing. The retrieval and prompt-assembly logic is fully real and tested; the actual generation call is injectable (proven via a fake `llm_call` in tests) and needs live Gemini credentials to run end-to-end, which this environment doesn't have. **Waiting On** (real, tested): the inverse of commitment tracking — surfaces sent messages with no reply past a 4-day staleness threshold (`QUORUM_CONFIGURATION_CONSTANTS.md` §4).

## 9.2 Calendar — the shared resource
**CalendarProvider primary** (on-device, `device_calendar` Flutter package, zero OAuth) — reads whatever calendars are already synced to the phone, removing most of the OAuth blast radius entirely. **Google Calendar API only for external-invitee sends** (creating an event that emails a real external person requires Google's infrastructure; CalendarProvider can write to the user's own calendar but cannot invite a third party). **Meeting-Load Defense** (real, tested — `backend/features/meeting_load.py`): proactively flags an over-scheduled day using an 8-hour working-day default, 0.25 buffer fraction, 0.7 overload threshold — the exact same duration-math pattern `AvailabilityCheck` will use once implemented.

## 9.3 Tasks — the intent layer
NL creation, decomposition templates (study plan / interview prep / assignment), effort-hours per task, recurrence. **Predictive Risk** (real, tested — `backend/features/predictive_risk.py`): mines historical correction patterns — if an upcoming week's deadline density matches a historically risky pattern (≥0.5 historical correction rate at that density, within ±1 deadline tolerance) it's flagged before the collision happens, not after. This is temporal pattern mining, a technique named in the project's original scope and, until this feature, never actually built out past recurring-expense detection.

## 9.4 Finance — the third conflict axis
Lean budget layer — explicitly not a fintech app, its job is giving negotiation a money axis. **Subscription Detective** (real, tested — `backend/features/subscription_detective.py`): deterministic recurring-expense detection via interval clustering (minimum 3 occurrences, ±5-day tolerance around a 30-day target interval) — not ML, a concrete, satisfying, fully explainable application of the same temporal-pattern-mining technique.

## 9.5 Career — rides on Email
No independent external API for detection — application/interview classification rides entirely on Email's existing ingestion and extraction pipeline. **Company Research Digest** (real, tested — `backend/features/career_digest.py`, DEC-004): compiles a short brief the moment an interview or application is detected. This required a genuinely new architectural decision the project previously lacked: a real search-API integration. **Tavily** was chosen after live, current (August 2026), multi-source research found Bing retired, Google Custom Search closed to new signups and shutting down entirely January 2027, Brave's free-tier status disputed in its own current coverage (a real instability signal, not a minor detail — the same pattern that has bitten this project on two other providers), and SerpAPI carrying a live DMCA legal risk over the scraping mechanism it depends on. Tavily: 1,000 free credits/month, 1 credit per basic search (the endpoint actually used here, not the more expensive multi-step Research mode), no card required, and an explicit public commitment from its February 2026 acquirer (Nebius) that existing customers' access and data policies don't change. Exa is the named fallback in the Capacity Manager's routing if Tavily's terms ever move.

## 9.6 Memory/Context Substrate — not a domain
mem0 + pgvector, absorbing Notes and Contacts as searchable context rather than action-bearing domains. **Self-Test Harness** and **Honesty Log** (both real, tested) live here conceptually: the harness runs adversarial scenarios against the Gate (currently against an explicit stub — not because the real orchestration function doesn't exist, it's been real since `IMPL_08`, but because nothing has wired the harness to it yet; see `STATUS_INDEX.md`'s open items) and reports misses with the same prominence as catches — proven by test to surface a deliberately-mis-specified scenario rather than hide it. The Honesty Log guarantees corrections and near-misses are never filtered from the evaluation surface, a direct response to research finding that showing AI reasoning tends to increase user agreement *even when the AI is wrong* — surfacing uncertainty and failure with equal prominence to success is the calibration correction, not an afterthought.

## 9.7 Newly built features — complete real-code status

**RESOLVED, real, load-bearing correction (`specs/tier1_foundation/QUORUM_PRODUCTION_COMPLETION_PLAN.md`'s own creation session):** a full repository diagnosis, checking the actual filesystem directly rather than trusting this table, found 6 of the rows below describe files that **do not exist anywhere in this repository** — the same "specification narrative describes a different, no-longer-accessible environment" pattern `specs/tier3_verification/STATUS_INDEX.md`'s own intro paragraph already disclosed once for a different claim (`DEC-050`), never previously caught here. Confirmed real, present, and passing in this repository as of that same check: `subscription_detective.py`, `self_test_harness.py` (real since `DEC-099`, wired directly to the live Gate, no stub was ever built here), `search.py`. The "Real code" column below is corrected accordingly; building the 6 genuinely-absent modules is tracked as real, scoped work in `QUORUM_PRODUCTION_COMPLETION_PLAN.md` (Phases 2, 4–6), each against this table's own already-real, already-specified parameters rather than starting from nothing.

| Feature | Domain | Real code | Tests | Status |
|---|---|---|---|---|
| Style-Conditioned Replies | Email | **`style_reply.py` — does not exist in this repository** | — | Not built. Real parameters (few-shot retrieval from past sent mail to the same contact) remain valid design guidance for `QUORUM_PRODUCTION_COMPLETION_PLAN.md` Phase 4. |
| Waiting On | Email | **`waiting_on.py` — does not exist in this repository** | — | Not built (backend). A mobile screen/logic file exists with no backend behind it. Real 4-day staleness threshold (`QUORUM_CONFIGURATION_CONSTANTS.md` §4) remains valid — see Phase 4. |
| Meeting-Load Defense | Calendar | **`meeting_load.py` — does not exist in this repository** | — | Not built. Real parameters (8h working day, 0.25 buffer fraction, 0.7 overload threshold) remain valid — see Phase 5. |
| Predictive Risk | Tasks | **`predictive_risk.py` — does not exist in this repository** | — | Not built. Real parameters (≥0.5 historical correction rate, ±1 deadline tolerance) remain valid — see Phase 6. |
| Subscription Detective | Finance | `subscription_detective.py` | real, passing | **Confirmed real and present** — the one feature in this table that genuinely is what this table claims. |
| Company Research Digest | Career | **`career_digest.py` — does not exist in this repository** | — | Not built. Real search-API decision (Tavily, `DEC-004`) remains valid — see Phase 6. |
| Self-Test Harness | Substrate | `self_test_harness.py` | real, passing | **Confirmed real and present.** Status corrected: real, wired directly to the live Gate since `DEC-099` — no stub was ever built in this repository (a separate, since-resolved stale claim, see `.claude/CLAUDE.md`'s own "What changed mid-project"). |
| Honesty Log | Substrate | **`honesty_log.py` — does not exist in this repository** | — | Not built (backend). A mobile screen/logic file exists with no backend behind it — the app's own permanent "Log" bottom-nav tab is a dead end for every real user as a direct result. See Phase 6. |
| Unified Fast Search | Cross-cutting | `search.py` | real, passing | **Confirmed real and present** — and further ahead than this row claims: real semantic pgvector search is already live (`DEC-120`), not just the "named upgrade" this row still describes as future work. |
| Computed State (Today numbers) | Cross-cutting | `computed_state.dart` (on-device) only | hand-verified parity (Dart) | **`computed_state.py` (the Python reference) does not exist in this repository** — a real, already-disclosed gap `STATUS_INDEX.md` has repeated at every relevant milestone (most recently `DEC-119`, whose own narrower `today.py` port covers only Today's specific needs, not the general Python reference this row claims exists). |
| Share-to-Quorum | Mobile platform | `share_intent_handler.dart` + manifest snippet | real, passing (`flutter test`) | Confirmed present and real; genuinely verified as of `DEC-103`, not "unverified in sandbox" as this row still claims. |
| App Icon Shortcuts | Mobile platform | **`shortcuts.xml` — does not exist anywhere in this repository** | — | Not built (confirmed by a real, direct search across the whole `mobile/` tree during this diff's own review pass, after this row was first left as "not independently re-verified" — checked rather than left ambiguous). |
| Home-Screen Widget | Mobile platform | `today_widget_bridge.dart` + `TodayWidgetProvider.kt` | real, passing (`flutter test`) | Confirmed present and real; genuinely verified as of `DEC-103`, not "unverified in sandbox" as this row still claims. |

## 9.8 Briefing Enrichments — not domains
Weather via a free API, folded into the morning composition alongside the computed-state numbers (§11.4) — one additional call, disproportionate perceived-quality gain.

---

# 10. Edge Architecture — On-Device & Degraded Mode

## 10.1 The Privacy Gate
Runs on-device, before any cloud escalation, two layers: a rule layer (regex pattern detection for credentials, OTPs, account numbers, government IDs, medical terms — milliseconds, zero model involvement) and an SLM classification layer (public/personal/sensitive). Policy: sensitive content is handled entirely locally where possible, redacted with typed placeholders before escalation where cloud reasoning is genuinely required, or the user is asked with one tap. **This is what makes using free-tier cloud LLMs — whose terms explicitly permit training on traffic — a defensible trade-off rather than a quietly risky one.** The two decisions (free-tier LLM usage, on-device privacy gating) are directly connected, not coincidentally paired.

## 10.2 What the on-device model is allowed to do
C0-complexity work only: extraction, classification, routing-signal generation, offline capture. Never drafting, never debate, never negotiation — a deliberate, permanent scope boundary matching what a 4B-class model can reliably do, not a current limitation awaiting a bigger model later.

## 10.3 CalendarProvider — ground truth without a network call
Because `AvailabilityCheck` (once implemented) needs calendar ground truth and CalendarProvider is already local, availability checking can run instantly, even offline — this is a direct architectural consequence of §9.2's integration choice, not a separate feature.

## 10.4 Extended-Outage Local Continuity Mode — the full state machine

**Detection:** 3 consecutive cross-provider LLM call failures **and** a connectivity check confirming no reachability for 2+ continuous minutes (`QUORUM_CONFIGURATION_CONSTANTS.md` §6). Both conditions, not either alone — a single transient failure should not flip the whole app into degraded mode.

**Recovery:** automatic, immediate on the first successful health-check. Anything queued during the outage **replays through the full cloud Gate before finalizing** — never grandfathered in as pre-approved just because it survived the outage.

**By stakes class:**
- S0/S1: entirely unaffected — already local.
- S2: Stage A runs against the local Drift mirror instead of the cloud database, executes with a `pending_reverification` flag, and the full check re-runs automatically the moment connectivity returns.
- **S3: prepared on-device, clearly labeled "prepared offline — not yet verified," and never sent regardless of any user tap.** A tap in this mode is recorded as "approve once verified," not "send now." This is the one place the app is deliberately less convenient than normal operation, and that asymmetry is intentional: the alternative would make the trust guarantee conditional on network status, exactly when a stressed user is least likely to independently catch an error.

## 10.5 Reconciliation with the retention design — the real, closed gap (F4)
The Today screen's live computed numbers (§12.2) were originally specified against live backend data only, designed independently of Extended-Outage Mode's local-mirror design — the two pieces of otherwise-good work were never checked against each other until a later project review found the gap. **Resolved, with real code on both sides of the platform boundary:** `compute_capacity_state()` and `compute_budget_state()` are pure, deterministic functions, proven by test (`test_capacity_math_is_identical_regardless_of_source`, `test_budget_math_is_identical_regardless_of_source`) to produce numerically identical results whether fed live backend data or the local Drift mirror — only the `source` label differs, surfaced honestly in the UI as "live" or "offline estimate," never silently presented as one when it's the other. The Dart port (`mobile/lib/features/computed_state.dart`) was hand-verified line-for-line against the same three test cases already proven in Python, since this sandbox cannot execute Dart directly. The signature retention feature now survives the exact scenario — an outage — where a calm, reliable home screen matters most, rather than going stale precisely when it would matter.

## 10.6 Operational reality — Android fights this
Doze mode and aggressive OEM battery management (particularly on Xiaomi, Vivo, Oppo — common among the target demographic) can silently kill background work the architecture depends on. Addressed explicitly, not assumed away: onboarding requests battery-optimization allowlisting with a clearly stated reason; the sync/notification path is designed to recover reliably on next app-foreground rather than assuming uninterrupted background execution Android does not actually guarantee.

## 10.7 On-device model tiering
Three tiers sized to Quorum's actual model footprints, not a generic industry threshold (real research found no universal standard to defer to — this is a project-specific engineering judgment):

| Tier | Device RAM | Model |
|---|---|---|
| Full | ≥8GB | Primary — **open, Sprint 0** (§22) |
| Light | 4–8GB | SmolLM2-1.7B (~1.1GB footprint) |
| Cloud-only | <4GB | No local model; all C0 work routes to Gemini Flash-Lite |

Download: deferred, backgrounded, Wi-Fi-default, never a blocking first-run step. Only one tier's model is ever stored on-device at once. Silent per-request fallback to cloud if a load ever fails — never a visible error. Tier is shown transparently in the You tab (§12.3), stated factually and respectfully ("your device doesn't have enough memory for local processing, so quick actions route through the cloud instead — still private, still verified"), never as a warning.

---

# 11. AI & ML Model Architecture

## 11.1 On-device models — genuinely open
Primary tier candidate: **Gemma 4 E4B or Llama 3.2 3B.** Live research found a real, current trade-off, not a settled choice: Gemma has newer, spec-sheet-level native function calling; Llama 3.2 3B carries a specific, credible claim to superior real-world tool-calling reliability at this parameter scale. **This is resolved only empirically** — by testing both on real structured-extraction prompts in Sprint 0 — never by further design argument. Fallback tier: SmolLM2-1.7B, chosen specifically for being the fastest tokens-per-second in its weight class, appropriate to a fallback tier's job.

## 11.2 On-device runtime — also open
llama.cpp via a maintained Flutter plugin, evaluated in a fixed order as an empirical Sprint 0 spike: llamadart → fllama → llama_flutter_android, first success wins. Not hand-rolled FFI — would burn real hours for zero interview or product value.

## 11.3 Cloud LLMs (API, free-tier) and the Capacity Manager
Gemini Flash (Generator, Judge — full reasoning tasks). Gemini Flash-Lite (high-volume, lower-complexity: extraction, classification, routing signals — a deliberate split from Flash, not one undifferentiated "Gemini" pool). Llama 3.3 70B via Groq (Critic — model diversity, §6.4). Cerebras named as an additional Capacity Manager fallback, its model catalog treated as volatile and never hardcoded by name in application logic, consistent with this project's repeated real experience of free-tier catalogs changing without notice.

The Capacity Manager is the single chokepoint for every LLM call in the system — no raw provider calls exist anywhere in the codebase. Per-user budgets, provider fallback with backoff, and an explicit degradation ladder whose invariant is: **the system runs out of speed before it runs out of integrity** — background/proactive work defers first, narration falls back to templates next, and S3 actions queue rather than ever skip the Gate.

## 11.4 Self-hosted models — real, on the same Cloud Run compute
**Qwen3-Embedding-0.6B** — supersedes an earlier Nomic-embed-text choice after research found a meaningfully higher MTEB benchmark score at a still-lightweight, self-hostable footprint (roughly 1.5GB vs. Nomic's 274MB — larger, but not the compute node's actual bottleneck). Retrieval quality feeds directly into both draft quality (§9.1's style-conditioned replies) and Gate context quality, making this a genuine upgrade, not a lateral rebrand. **The exact output vector dimension is not yet confirmed against the actually-loaded model** — the `note_embeddings` pgvector column specification in `QUORUM_DATA_CONTRACTS.md` §3 marks `VECTOR(1024)` explicitly as unconfirmed, to be verified at integration time rather than hardcoded from assumption now.

**Router/complexity classifier** — classical ML (logistic regression or LightGBM), trained entirely from scratch, never fine-tuned from any pretrained checkpoint, self-generating its own labeled training data from the nightly Tier-1/Tier-2 replay logs. Needs no dataset collected by hand, needs no GPU — this is a CPU-seconds training task, not a deep-learning one.

**Prompt-injection guard** — an existing, published, fine-tuned classifier (e.g. a DeBERTa-based model from a security-focused publisher), used entirely as-is. Never trained or fine-tuned in-house.

## 11.5 No fine-tuning anywhere — hard constraint, verified by inspection
Confirmed directly against every model-touching module in the real codebase: `style_reply.py`'s LLM call is injected and invoked as-is, never adjusted. The router classifier and embedding model are either trained fully from scratch or used unmodified — never fine-tuned from a pretrained checkpoint. The injection guard is downloaded and used unmodified. This constraint was set explicitly early in the project and has held across every subsequent model decision without exception.

---

# 12. Frontend & Application Architecture

## 12.1 Visual direction — "instrument-grade clarity"
Reconsidered entirely from a first, rejected direction (a chronological, ledger-style metaphor, criticized as reading like a generic AI-generated dark-mode dashboard — near-black-plus-single-accent, uniform rounded cards, icon-in-colored-chip patterns, all identified as overused conventions rather than intentional choices). The final direction borrows the *discipline* of high-stakes instrumentation — a flight deck, not a costume of one: only decision-relevant information is visible at any moment, status is never conveyed by color alone (paired with shape/icon/position, both a genuine accessibility requirement and a real differentiator against competitors that lean entirely on color-coding), and a verification check resolving is a real, literal, satisfying interaction, not a metaphor buried in copy.

**Light-primary** — a deliberate, contrarian choice against dark-mode-default competitors in this exact product category, chosen specifically because restraint paired with light is the less expected choice in 2026's AI-trust-app design landscape, and pairs with the "gets out of the way of the content" quality that design-award-caliber work in this period consistently favors over decoration. **No dominant chromatic brand identity** — color is reserved purely for functional status signaling, used sparingly; the memorable, ownable signature is the checklist-tick interaction itself, not a hex code — this also deliberately avoids purple, confirmed via research to be the industry-default "this is AI" color, and avoids the warm-clay/terracotta palette independently flagged as a different AI-product convention to avoid.

## 12.2 Information architecture — status-first, then reconciled for retention
The home surface ("Today") answers *what's true right now*, not *what happened, in order* — three zones ranked by urgency, not recency: **Needs you now**, **Holding steady**, **In motion**. A dedicated retention analysis found the purely event-driven version of this screen has empty days by design (nothing to show when nothing eventful has happened) and that the "caught this" mechanic structurally erodes as the product succeeds at its actual job — success reduces the very content meant to drive engagement. **Resolution:** "Holding steady" was extended to feature **live computed numbers** — capacity remaining today, budget pace — reusing the negotiation subgraph's own deterministic impact-simulator math (§8.4), now proven identical whether sourced live or from the local mirror (§10.5). Two natural daily touchpoints bookend the day: a morning "what does today look like" and an evening "how did today go," without gamification, streaks, or any social/comparative mechanic — those were explicitly considered and rejected.

## 12.3 Navigation
Four stable tabs, chosen deliberately over an adaptive-navigation-position pattern (research found adaptive *content* works but adaptive *navigation position* actively confuses users — a real, cited failure mode from prior design eras): **Today** (§12.2), **Log** (the full chronological history, correctly demoted to secondary, searchable), **Trust** (reframed as benefit narrative — "Quorum handled 42 things this week, caught 4 problems before they happened" — never raw metrics as the primary framing; the Honesty Log and Self-Test results are surfaced here with equal prominence to successes, per §9.6's rationale), **You** (preferences, on-device tier transparency §10.7, negotiation weight editing §8.5, account controls). **Unified Search's navigation home:** a persistent search affordance in the top bar across all screens, not a fifth tab — this was a real, previously-unresolved gap (the feature was built before it had a defined home in the IA), closed by this decision rather than left open.

## 12.4 UX principles
**Semi-transparent explanation:** a "why?" affordance expanding a brief rationale on demand — neither a fully opaque black box nor a raw reasoning dump, the empirically-supported middle ground for AI trust interfaces. **Stakes-proportional friction:** the S0–S3 axis (§5) maps directly onto UI treatment — a read-only summary needs no ceremony; an irreversible S3 send visibly carries more weight (§6.6's anti-rubber-stamp gate is the concrete implementation of this principle, not a separate idea). **A correction affordance on every AI output** — research found the *ability* to correct is itself a trust signal independent of whether it's used. **Uncertainty surfaced with equal prominence to confidence** — a direct, deliberate response to research finding that revealing AI reasoning tends to increase user agreement *even when the AI is wrong*; showing work alone risks inflating trust rather than calibrating it, so `no_data_found` findings and genuine uncertainty get the same visual weight as confirmed catches, not a footnote.

## 12.5 Onboarding
Show, don't tell: the first real interaction is a trivial, low-stakes on-device action (a note, a small expense), with the real checklist-tick verification watched live, before any explanatory copy at all — the user experiences the core mechanism before being told about it.

## 12.6 The complete user-side flow
Full 36-step walkthrough (install → OAuth connection → first low-stakes interaction → Today screen → Gate reveal on a pending action → negotiation on a conflicted item → quiet confirmations → on-device capture → Log/Trust/You tabs → proactive notification handling → Extended-Outage behavior) is preserved as the canonical reference for how every architectural piece above composes into a single session, from install to an extended outage and recovery. Not repeated here in full to avoid duplicating a document-length walkthrough; the phase structure matches §9 (domains), §10 (edge), §6 (Gate), and §8 (negotiation) directly, in that order of appearance.

---

# 13. Infrastructure & Deployment Architecture

## 13.1 Compute — Google Cloud Run
Serverless, scale-to-zero — the resolution to a genuine, stated contradiction (zero cost, zero instance, yet real-time proactive agents) that no self-hosted VM could satisfy simultaneously; a self-hosted server, even a free one, is definitionally an instance, and the actual requirement was for the scheduling clock to live somewhere that costs nothing while idle. **Concurrency explicitly set to 1** — Cloud Run's default multi-request-per-container behavior creates a real, if statistically unlikely, risk of state leaking between two different users' verification runs within the same warm container instance; for a project whose entire premise is trustworthy isolation, this was judged worth closing with a single configuration line rather than trusting careful coding practice alone to prevent it. Free-tier eligibility is restricted to specific US regions (`us-central1`, `us-east1`, `us-west1`) — confirmed via live research, not assumed.

## 13.2 Database — Supabase, region-corrected
Postgres + pgvector, **co-located in the same region as Cloud Run.** This was originally specified as Mumbai, reasoned as "lower latency for the user" — that reasoning was found to be imprecise once it was established that the phone never calls Supabase directly (only the backend does, since custom JWT/OAuth and custom polling/FCM were chosen over Supabase's own Auth and Realtime products), making backend-to-database the actual dominant latency hop, not phone-to-database. Once Cloud Run's free tier turned out to be region-restricted to US zones, co-locating both in the same US region closed a real, previously undetected inconsistency between two decisions made in separate design passes — and improved real latency in the process, rather than trading it away. PgBouncer sits in front, justified now — serverless naturally produces connection-count spikes (many short-lived instances, each opening its own connection) more aggressively than a single long-running process ever would — not deferred to a future-scale concern.

## 13.3 Scheduling — the mechanism that changed twice, both times for real, researched reasons
**Original plan:** GitHub Actions cron as the primary trigger for proactive agents, reasoned at the time as "functionally identical to a self-hosted scheduler." **Found wrong** by a later, deliberately skeptical research pass: GitHub's scheduled triggers are documented to run 15–60 minutes late routinely, sometimes hours late during platform-wide load — not the real-time behavior originally claimed. **Replaced** with **Supabase's own `pg_cron` + `pg_net`**, living inside the already-used Supabase instance, invoking Cloud Run endpoints directly with real sub-minute precision, no new provider, no new credentials.

**GitHub Actions was reassigned, not removed.** A separate, later finding: Supabase's free-tier inactivity pause was tightened to 7 days as of February 2026, documented as the single most common thing that catches real projects on the platform. A low-frequency GitHub Actions ping (every 3–4 days, comfortably inside the 7-day window) prevents this — a job whose timing tolerance is wide enough that GitHub's drift is completely irrelevant, unlike the proactive-scheduling job it was originally, wrongly, assigned to.

## 13.4 Background work — no persistent process, anywhere
Scheduled jobs (briefing, deadline-watch, follow-up, spend-alert) are invoked as direct Cloud Run endpoint calls by `pg_cron`, not consumed from a queue by a persistent worker daemon — a worker daemon is, definitionally, an instance, which the whole "no instance, genuinely zero cost" requirement was built specifically to avoid. Anything needing retry/ordering semantics beyond a direct invocation uses a lightweight Postgres table, drained on a schedule, not a message-queue consumer process.

## 13.5 CI/CD — real, executed, not merely specified
GitHub Actions pipeline, in order: **lint (`ruff`)** — real, executed, confirmed clean against the actual codebase. **Unit tests** — real, 34/34 passing. **Golden scenario suite** — intentionally deferred, since no Gate orchestration exists yet to test against; this is a logged, deliberate deferral (DEC-002), not an oversight discovered late. **Trivy vulnerability scan** — real, correctly configured against the documented GitHub Action, but genuinely unverified by actual execution in this environment, since this sandbox has no Docker; needs a real GitHub Actions run to be truly confirmed. **Build** — real, a working `Dockerfile`. **Health-checked deploy cutover** — intentionally deferred, no real Cloud Run target exists yet to deploy to.

---

# 14. Security Architecture

## 14.1 Authentication
JWT — 15-minute access token, rotating refresh token, server-side revocation list enabling a genuine "sign out everywhere" control. This was a real, previously-identified gap: an earlier design had no session-revocation mechanism at all for an app with real write access to a user's email, closed explicitly.

## 14.2 OAuth — the full flow
The phone's webview opens Google's real consent screen; the returned authorization code is handed to the backend, which performs the actual token exchange server-side, holding the client secret — the phone never sees a raw secret, since a secret embedded in a distributed mobile binary isn't meaningfully secret. Protected by a server-generated, single-use `state` parameter (CSRF protection) and **PKCE**, applied even on this confidential-client exchange as defense-in-depth beyond its original public-client design intent. Redirect URI validated by exact match, never prefix match — a classic, still-common misconfiguration deliberately avoided. Because the app runs in Google's OAuth Testing status (100-user allowlist, 7-day refresh-token expiry), the app sets this expectation honestly at connection time rather than hiding it, and detects `invalid_grant` server-side to trigger a one-tap reconnect flow rather than a silent, confusing breakage.

## 14.3 Agent authorization — two independent layers
Enforced both at LangGraph wiring (an agent is never *offered* a tool outside its own domain — Email's node has no reference to Finance's `write_budget` tool at all) and, independently, at the MCP tool server itself, which validates the calling agent's declared domain against a static allowlist before executing any call, regardless of what the request content asks for. A single wiring mistake alone cannot become a security hole, because the second layer doesn't depend on the first having been correct.

## 14.4 Prompt injection and jailbreak defense — distinguished precisely
**Injection** (untrusted ingested content attempting to redirect agent behavior): defended by strict content/instruction delimiting in any prompt handling ingested text, plus the `ProvenanceCheck` Stage A validator (specified, not yet implemented, §6.3) — an action whose justification traces only to embedded content, never to the user's own stated intent, is a structural red flag routed to mandatory human escalation. **Jailbreak**, precisely scoped for this system: an attempt to get the Judge specifically to approve despite real contrary evidence, via manipulated content. Mitigated by the anonymized, evidence-only Judge prompt construction (§6.4) — both the real `CRITIC_SYSTEM_PROMPT` and `JUDGE_SYSTEM_PROMPT` explicitly instruct that any instruction-like text within ingested content is data, never a command, tested to be present in the actual rendered prompt output. A genuine, earned architectural property worth stating plainly: because Quorum's user-facing surface is mostly structured (approve/reject, choice cards) rather than an open chat interface, the *direct user-driven* jailbreak attack surface is inherently smaller than a chat-first competitor product — a deliberate consequence of the product design in §12, not an accident.

## 14.5 Secrets, credentials, and the real-action testing rule
Google Secret Manager for all production credentials — never `.env`, never committed files. **A rule specific to this project's real-world-action surface, not present in the prior methodology this project's discipline was adapted from:** any development-time testing that could otherwise touch a real external destination (an actual email send, an actual calendar invite to a real person) uses dedicated sandbox Gmail/Calendar test accounts, always — never production-consequential targets, even during legitimate "test the real thing, not a mock" verification work.

## 14.6 Observability security — trace scrubbing
A middleware strips known-sensitive patterns (reusing the Privacy Gate's own rule-layer detectors, §10.1 — not a separately maintained pattern set) from anything sent to Langfuse, before it's persisted. The same comprehensive tracing that makes the trust thesis measurable (§17) is also the system's largest potential secret-leakage surface if this step were skipped — the connection between these two facts is direct, not coincidental.

## 14.7 Data retention and deletion
Raw email bodies retained 90 days; after that window, only extracted structured data and embeddings persist. A real delete-account flow — purging Postgres, pgvector, mem0, and revoking stored OAuth tokens — is required to exist before real user data enters the system in beta, not treated as later polish.

---

# 15. Data Architecture

**Full schema detail:** `QUORUM_DATA_CONTRACTS.md` in complete. Summary: the Gate's four core Pydantic schemas (§1 of that document, real and tested), twelve real feature-layer dataclasses (§2, referenced not duplicated), a specified-but-not-yet-executed Postgres schema (§3 — `action_events`, `tasks`, `expenses`, `applications`, `note_embeddings`), specified Redis key patterns (§4), REST contracts (§5, one real and verified, three specified), and MCP tool call shapes (§6).

**Data flow, end to end for a representative action:** an inbound email is polled → ingested and embedded into pgvector (Qwen3-Embedding-0.6B) → a request enters the router (§5) → if S0/read-only, a synchronous REST response; otherwise, accepted asynchronously and processed through the LangGraph orchestrator → if a cross-domain conflict is detected, the negotiation subgraph activates (§8) → the resulting action passes the Gate (§6) → any S3 action queues for human approval regardless of Gate confidence → on approval, the real external action executes and the event is logged to `action_events`, feeding the evaluation layer (§17).

---

# 16. Reliability & Failure Handling

Consolidated from decisions made throughout this document, gathered here as a single reference:

- **Idempotency keys** on every scheduled-invocation endpoint, closing a real gap identified during deployment verification — a `pg_cron` job firing twice for the same window must never produce a duplicate proposed action or duplicate notification.
- **Retry-vs-revision separation** in the Gate (§6.5) — infrastructure hiccups and genuine content disagreement are structurally different failure classes, handled by different mechanisms, never conflated.
- **The Capacity Manager's degradation ladder** (§11.3) — speed degrades before integrity does, at every layer, by explicit design invariant.
- **Extended-Outage Mode** (§10.4–10.5) — the most complete example of this principle: usefulness degrades gracefully; the one absolute guarantee (no unverified S3 action ever sends) does not.
- **Two-stage CI verification** (§13.5) — lint and unit tests are genuinely executed and confirmed on every real change; nothing in this project's real code has been claimed "passing" without an actual run to back the claim.

---

# 17. Evaluation Architecture

## 17.1 Three layers
A golden scenario suite (CI-gated, trajectory-checked — not yet populated; this is real, deliberately deferred work, not blocked on the orchestration function, which has been real since `IMPL_08` — see `STATUS_INDEX.md` for current status). Live action-accuracy tracking (approval-unchanged rate, correction rate, trend over time, backed by the real `action_events` table, §15). Routing-consistency measurement — explicitly named as *agreement* between Tier-1 and Tier-2, never *accuracy*, since agreement between two fallible systems is a materially weaker and different claim than correctness against ground truth.

## 17.2 Closing the accuracy-vs-agreement gap
A small, recurring human-labeled sample (roughly 15–20 real decisions reviewed per week) is the planned mechanism for genuine precision/recall measurement, once real usage exists to sample from.

## 17.3 The Self-Test Harness and Honesty Log as evaluation, not just features
Both (§9.6, §9.7) are the user-facing extension of this same evaluation discipline — proven by the harness's own test to surface a deliberately-introduced miss rather than hide it, which is the actual, demonstrated behavior this whole evaluation philosophy depends on, not merely an aspiration stated in prose.

## 17.4 Ablation studies — named, not yet performed
Two studies are named as real future work, not yet executed: two-stage Gate versus a naive all-LLM-checks-everything baseline (would convert the currently-asserted ~50% cost reduction claim, §6.7, into a measured one); Tier-1-always versus Tier-2-always routing (would quantify the actual, not assumed, value of the on-device tier).

---

# 18. Development Methodology (referenced, not reproduced)

Full detail: `QUORUM_SPEC_METHODOLOGY.md` and `CLAUDE.md` — this ADD is the *system* architecture; those are the *development process* that builds it. Summary: spec-driven, session-bounded implementation, one git branch per session; an append-only `DECISIONS_LOG.md` as the highest-authority record of what actually happened versus what was originally planned (currently at DEC-004, real entries, not placeholder structure); fresh-context subagent review as the default for routine sessions, with **cross-model review mandatory** for anything touching the Gate, security, secrets, or a real external-action path — the identical reasoning applied in §6.4 to why the Critic itself runs on a different model than the Generator, now applied reflexively to how Quorum gets built; and dedicated sandbox credentials for any testing that could otherwise fire a real external action (§14.5).

---

# 19. Current Implementation Status — pointer, not a restated snapshot

**Authoritative source for current implementation status: `specs/tier3_verification/STATUS_INDEX.md` — never this section.** This document held a literal snapshot here through v2.0 (34 tests, 2/9 validators, mobile as three platform features); by the time the real backend and mobile sequences finished, that snapshot was badly stale and briefly contradicted `QUORUM_MASTER_REFERENCE.md`'s own separately-drifted snapshot — the exact failure this rewrite exists to make structurally impossible going forward, the same fix `QUORUM_GATE_SPECIFICATION.md` §4/§7 already proved works.

What stays here permanently, because it doesn't change session to session: the real categories of what gets built and how they're organized — the Gate (schemas, prompts, Stage A validators, Stage B orchestration), the feature-module layer, the mobile platform-feature layer, the CI pipeline's stages. **For the actual current counts, test totals, and per-item real/specified status of every one of these categories, `STATUS_INDEX.md` is the only place that's re-verified live every session — read it, not this section.**

---

# 20. Alternatives Considered and Rejected (preserved for rationale, not live options)

Microservices (real operational tax for a scale that doesn't need it; the modular monolith already delivers the same least-privilege and separability properties). A single Oracle Free-Tier VM (rejected after real, repeated, documented capacity failures — replaced by the unbundled managed-service stack in §13). Supabase Edge Functions as a full backend replacement (would require rewriting the entire real Python backend into TypeScript for a locality benefit the region-co-location fix in §13.2 already achieves for free, with LangGraph's TypeScript port being meaningfully less mature than the Python original already validated). All-in-one hosting platforms — Railway, Render, Fly.io (predominantly time-limited trials or credit grants, not permanently free tiers, confirmed by research — disqualified on the same ₹0-forever grounds as everything else in §13). Bing Search API, Google Custom Search, Serper, DataForSEO, Brave Search API for the Career Research Digest (§9.5 — each ruled out for a specific, current, researched reason, not a generic preference). Fine-tuning any model anywhere in the system (§11.5 — a hard constraint, honored without exception throughout).

---

# 21. Verification of This Document Against Project History (dated to the v2.0 freeze, 2026-08-13 — not an ongoing claim)

**This is a historical record of one specific audit, performed when this document's own text was last substantively revised. It describes whether the ADD's *text* was internally consistent and complete at that moment — it does not describe whether the *implementation* still matches this text today.** For that, see `DECISIONS_LOG.md` (the append-only record of what actually happened, including every place reality diverged from this document afterward) and `STATUS_INDEX.md` (current state). Real, concrete divergences did emerge after this freeze — see §19's pointer — which is exactly why this section is now explicitly dated rather than presented as evergreen.

The v2.0 freeze audit itself, preserved as-written:
- **Omissions:** none identified against the full traceable history of design phases — vision, router, Gate, negotiation, domains, edge/on-device, models, frontend, deployment, security, evaluation, methodology.
- **Contradictions with the latest agreed architecture:** none found. Every point where an earlier iteration existed (scheduling mechanism, Supabase region, embedding model choice, retention design) states only the final, current, resolved form, with the superseded reasoning preserved for context, not presented as live.
- **Reintroduced obsolete decisions:** specifically checked — GitHub Actions as primary scheduler (correctly demoted to keep-alive only, §13.3), Nomic-embed-text (correctly absent, superseded by Qwen3-Embedding-0.6B, §11.4). Neither reappears.
- **Assumptions presented as final:** none — every genuinely open item is explicitly marked in §22, not silently resolved for the sake of narrative completeness.
- **Internal consistency:** the two most significant consistency risks this project's own review process ever found — the Gate/Honesty-Log vocabulary mismatch and the retention/degraded-mode gap — are both closed with real, tested code (§6.8, §10.5), not narrative reconciliation alone.
- **Sufficiency for implementation to proceed without ambiguity:** yes, with §22 as the explicit, bounded, complete exception — true of the ADD's *text* at freeze time; §22 itself is now a pointer rather than a restated list, for the same reason as §19.

---

# 22. Known Open Items — pointer, not a restated list

**Authoritative source: `specs/tier3_verification/STATUS_INDEX.md`'s "Known open items" section — never this section.** This document held a literal 5-item list here through v2.0. By the time the real backend and mobile sequences finished, four more genuine open items had emerged during real implementation work — a Dart rounding-boundary uncertainty, a real backend module not yet wired to the live Gate, a missing aggregation query, and a set of built-but-not-yet-navigable mobile screens — and this section's own confident closing line ("nothing else is open") became false the moment the first of those four existed and wasn't added here. Restating the list a second time is exactly how it drifted from the one that's actually kept current; this section stops doing that.

The five items open at v2.0 freeze, preserved for historical context (all five remain genuinely open as of this rewrite too — resolving them requires real, empirical work, not further specification):

1. On-device primary model (§11.1) — Sprint 0.
2. Flutter llama.cpp plugin selection (§11.2) — Sprint 0.
3. Real Cloud Run cold-start latency (§12.4) — unmeasured against real infrastructure.
4. Whether `pg_cron`'s own firing counts as "activity" against Supabase's inactivity-pause timer — empirical, not resolvable by design discussion.
5. Qwen3-Embedding-0.6B's real output vector dimension — confirm at integration time, never hardcode from assumption.

**For the complete, current list — including everything found during real implementation after this freeze — read `STATUS_INDEX.md` directly.**

---

*End of Architecture Design Document, Version 2.0.*
