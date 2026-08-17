# QUORUM — Session Guide

**Tier:** `tier0_agent_guide` · **Volatility:** Rewritten whenever the plan changes · **Version:** 1.0

**Purpose:** the exact, ordered list of every remaining session — 44 total (23 backend, 21 mobile), plus the 4 supporting non-session documents (`TESTING_STRATEGY.md`, `VERIFICATION_STANDARDS.md`, and the 6 handbook documents are tracked separately, not numbered as sessions since they're not build units). This document defers to `STATUS_INDEX.md` for what's actually done — this is the sequence and the *why* of the order; that file is the live truth of progress.

**How to use this:** run sessions strictly in the order below. A session's "Prerequisites" line names exactly what must be real before it starts — never skip ahead on the assumption something's probably fine.

---

## Backend — 23 sessions

| # | Session | Prerequisites | Attach | One-line scope |
|---|---|---|---|---|
| `IMPL_00` | **Sprint 0 — Model & Plugin Resolution** | None — first session | `QUORUM_MASTER_REFERENCE.md`, `QUORUM_CONFIGURATION_CONSTANTS.md` | Runs both on-device model candidates and all three Flutter plugin candidates for real, writes the winners into `QUORUM_CONFIGURATION_CONSTANTS.md` §7, closes Open Items 1–2 permanently |
| `IMPL_01` | Validator — `AvailabilityCheck` | `IMPL_00` complete | `QUORUM_GATE_SPECIFICATION.md`, `QUORUM_DATA_CONTRACTS.md` | Real implementation + tests, matching the `temporal_fact_check` pattern already proven |
| `IMPL_02` | Validator — `DeadlineConflictCheck` | `IMPL_01` | Same as above | Tasks-DB-backed validator |
| `IMPL_03` | Validator — `RecipientCheck` | `IMPL_02` | Same as above | Email-metadata/contacts-backed validator |
| `IMPL_04` | Validator — `CommitmentCheck` | `IMPL_03` | Same as above | Parsed-user-intent-backed validator |
| `IMPL_05` | Validator — `PIILeakCheck` | `IMPL_04` | Same as above, plus Privacy Gate categories (from `MOBILE_03`, see below — this session may need to wait if run out of order; flagged explicitly) | Outbound-content-vs-Privacy-Gate-categories validator |
| `IMPL_06` | Validator — `ProvenanceCheck` | `IMPL_05` | Same as above | The primary structural prompt-injection defense |
| `IMPL_07` | `CoverageCheck` — comparison half | `IMPL_06` | Same as above | The deterministic set-comparison; extraction already real in `prompts.py` |
| `IMPL_08` | **Gate orchestration** (`gate.review()`) | All of `IMPL_01`–`IMPL_07` | `QUORUM_GATE_SPECIFICATION.md` in full, `QUORUM_DATA_CONTRACTS.md` | The real state machine — Stage A → Stage B → the bounded revision loop, against a real LangGraph node |
| `IMPL_09` | Router | `IMPL_08` | `QUORUM_MASTER_REFERENCE.md`, `QUORUM_CONFIGURATION_CONSTANTS.md` | Stakes lookup + rule-based complexity cold-start |
| `IMPL_10` | Infrastructure, part 1 | `IMPL_09` | `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §13 | Real Supabase + Upstash provisioning |
| `IMPL_11` | Infrastructure, part 2 | `IMPL_10` | Same | Real Cloud Run + Secret Manager + CI deploy target |
| `IMPL_12` | **Auth & Session Management** | `IMPL_11` | `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §14.1–14.2, `QUORUM_DATA_CONTRACTS.md` §5.5 | Real OAuth flow, JWT issuance/rotation, the revocation endpoint — found missing from the plan during document audit, now a real session |
| `IMPL_13` | Agent — Email | `IMPL_12` | `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §9.1 | LangGraph node, real Gmail OAuth, MCP tool binding |
| `IMPL_14` | Agent — Calendar (backend) | `IMPL_13` | ADD §9.2 | LangGraph node; native mobile-side integration is separate (`MOBILE_04`) |
| `IMPL_15` | Agent — Tasks | `IMPL_14` | ADD §9.3 | LangGraph node |
| `IMPL_16` | Agent — Finance | `IMPL_15` | ADD §9.4 | LangGraph node |
| `IMPL_17` | Agent — Career | `IMPL_16` | ADD §9.5 | Rides on Email; wires in the already-real `career_digest.py` |
| `IMPL_18` | Negotiation — trigger | All 5 domain agents (`IMPL_13`–`IMPL_17`) | ADD §8.1 | The `ConflictScan` computation |
| `IMPL_19` | Negotiation — positions + synthesis | `IMPL_18` | ADD §8.2–8.3 | Parallel position generation, merge-not-invent synthesis |
| `IMPL_20` | Negotiation — impact simulation | `IMPL_19` | ADD §8.4 | The zero-LLM-call deterministic simulator |
| `IMPL_21` | Negotiation — subgraph wiring | `IMPL_20` | ADD §8 in full | Wires the four negotiation pieces into one real LangGraph subgraph |
| `IMPL_22` | **Trace-scrubbing + delete-account** | `IMPL_12` (needs Auth) | ADD §14.6–14.7 | Combined session — both security/data-lifecycle, neither large enough alone; found missing during audit |

## Mobile — 21 sessions

| # | Session | Prerequisites | Attach | One-line scope |
|---|---|---|---|---|
| `MOBILE_01` | Flutter scaffold | `IMPL_00` complete (needs the resolved model/plugin) | `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §12 | Project init, Riverpod, Drift, the four-tab shell — no real screens yet |
| `MOBILE_02` | On-device model integration | `MOBILE_01` | ADD §11.1–11.2 | Wires in `IMPL_00`'s real, resolved model + plugin |
| `MOBILE_03` | **Privacy Gate** | `MOBILE_02` | ADD §10.1 | Rule layer + SLM classification — found missing from the plan during audit |
| `MOBILE_04` | **CalendarProvider native integration** | `MOBILE_03` | ADD §9.2, §10.3 | The `device_calendar` platform-channel wiring — found missing during audit |
| `MOBILE_05` | Today — "Needs you now" | `MOBILE_04` | ADD §12.2 | First of the three zones |
| `MOBILE_06` | Today — "Holding steady" | `MOBILE_05` | ADD §12.2, `computed_state.py`/`.dart` | Includes the live computed capacity/budget numbers |
| `MOBILE_07` | Today — "In motion" | `MOBILE_06` | ADD §12.2 | Third zone |
| `MOBILE_08` | The Gate reveal | `MOBILE_07`, `IMPL_08` | ADD §6, §12.4 | The staged Stage A/Stage B interaction |
| `MOBILE_09` | Negotiation screen | `MOBILE_08`, `IMPL_21` | ADD §8, §12 | Agent voices, option cards, computed deltas |
| `MOBILE_10` | Waiting On | `MOBILE_09` | `waiting_on.py` | Real backend module, first real screen |
| `MOBILE_11` | Career pipeline | `MOBILE_10`, `IMPL_17` | ADD §9.5 | Application → interview → offer/rejection view |
| `MOBILE_12` | Company digest detail | `MOBILE_11` | `career_digest.py` | Full digest view |
| `MOBILE_13` | Finance | `MOBILE_12`, `IMPL_16` | `subscription_detective.py` | Budget view + Subscription Detective's findings |
| `MOBILE_14` | Search results | `MOBILE_13` | `search.py`, `QUORUM_DATA_CONTRACTS.md` §5.7 | The persistent search bar's real destination |
| `MOBILE_15` | Log | `MOBILE_14` | ADD §12.3 | Chronological history, searchable |
| `MOBILE_16` | Trust — Honesty Log + Self-Test | `MOBILE_15` | `honesty_log.py`, `self_test_harness.py` | Failures given equal prominence to successes |
| `MOBILE_17` | Trust Digest | `MOBILE_16` | ADD §17 | The weekly benefit-narrative artifact |
| `MOBILE_18` | You | `MOBILE_17` | ADD §10.7, §14.7 | Preferences, tier transparency, account controls (including `DELETE /account`) |
| `MOBILE_19` | Memory transparency | `MOBILE_18` | ADD §7.3 | Browse/edit what Quorum believes |
| `MOBILE_20` | Extended-Outage wiring | `MOBILE_19`, `IMPL_22` | ADD §10.4–10.5 | The degraded-mode state machine, live on-device |
| `MOBILE_21` | Platform features wiring | `MOBILE_20` | Real: `share_intent_handler.dart`, `TodayWidgetProvider.kt`, `shortcuts.xml` | Wiring the already-real, sandbox-unverified code into the actual running app |

---

## Milestone checkpoints — full-system verification, not just per-session

Adopted directly from the AEGIS precedent (*"full manual checklist only at 3 milestones"*) — a real, live run-through of the whole system as it stands, not a new document category:

- **After `IMPL_08`** (Gate orchestration complete) — Handbook Walkthrough 1
- **After `IMPL_17`** (all five domain agents real) — Handbook Walkthrough 3 *(Walkthrough 2, "backend live," sits after `IMPL_11`, infrastructure)*
- **After `MOBILE_21`** (complete app) — Handbook Walkthrough 5, final

---

## What this document does not contain

Per-session file lists, exact code, and verification steps — those live in each individual `IMPL_NN`/`MOBILE_NN` spec, written just-in-time, one session ahead, per `QUORUM_SPEC_METHODOLOGY.md`. This document is the map; each session spec is the territory.

---

*Attach only this document, plus the specific session's own spec, to start any session — never the whole corpus.*
