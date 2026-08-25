# QUORUM — Master Reference

**Tier:** `tier1_foundation` · **Volatility:** Stable content, real-world direct edits — corrected here during a full staleness audit: this previously read "Frozen — amended, never edited directly · Version: 1.0," which didn't match how this document was actually kept current. In practice it was edited directly, in place, whenever a genuine gap was found, each edit disclosed in `DECISIONS_LOG.md` rather than through a separate "amendment" mechanism or an incremented version number — neither was ever actually used across the real project.

**Purpose:** the one document every session checks first. Dense, checkable, not explanatory — rationale lives in the ADD; exact values live in `QUORUM_CONFIGURATION_CONSTANTS.md`; exact schemas live in `QUORUM_DATA_CONTRACTS.md`; the Gate in full lives in `QUORUM_GATE_SPECIFICATION.md`. This document is the map, not the territory.

---

## 1. Seven Non-Negotiable Rules

1. Anything checkable against ground truth is code, never an LLM call.
2. Stakes (S0–S3) is a hardcoded lookup by `ActionType`, never learned.
3. `Finding.evidence_state` is three-valued, never binary.
4. S3 actions require explicit human approval in every mode, no exception, ever.
5. The Critic runs on a different model provider than the Generator/Judge.
6. No fine-tuning anywhere in the system.
7. The Gate's revision loop is bounded to one round — enforced by `GateVerdict.revision_count`'s type, not just application logic.

---

## 2. System Topology

Full diagram: `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §2. Summary: phone (Flutter, on-device SLM, Drift local storage) ↔ Cloud Run (FastAPI modular monolith, LangGraph, the Gate, Capacity Manager) ↔ Supabase / Upstash / Langfuse Cloud / Cloud Logging (all managed, all co-located in region with Cloud Run except Langfuse and Upstash which are region-agnostic REST services).

---

## 3. Component Responsibility Table

| Component | Responsibility | Depends on |
|---|---|---|
| Router | Classify stakes (lookup) + complexity (rules → trained classifier) | `QUORUM_CONFIGURATION_CONSTANTS.md` §1, §3 |
| Domain agents (5) | Draft proposals within their own domain, own their own tool allowlist | MCP, two-layer authorization |
| The Gate | Verify every S1+ proposal before execution | `QUORUM_GATE_SPECIFICATION.md` in full |
| Negotiation subgraph | Resolve ≥2-domain resource conflicts | Deterministic impact simulator, `Position`/`ImpactDelta` schemas |
| Capacity Manager | Single chokepoint for every LLM call, multi-provider fallback | §8 of `QUORUM_CONFIGURATION_CONSTANTS.md` |
| Extended-Outage Mode | Preserve S1/S2 utility and S3 integrity during connectivity loss | Local Drift mirror, `computed_state.py`/`.dart` parity |
| Evaluation layer | Golden suite, live accuracy, Honesty Log | `Outcome` enum, `verdict_outcome_mapping.py` (DEC-002) |

---

## 4. Domains — One Line Each

Email (spine, Gmail API) · Calendar (CalendarProvider primary, GCal API for external invites only) · Tasks (decomposition templates, effort-hours) · Finance (lean budget layer, third conflict axis) · Career (rides on Email's classification, no separate API surface until DEC-004's Tavily integration for Company Research Digest). Substrate (not a domain): mem0 + pgvector, four memory tiers.

---

## 5. Models — Pointer Table

| Role | Model | Status |
|---|---|---|
| On-device primary | **Llama 3.2 3B** | **RESOLVED, live Sprint 0 result, run to genuine completion via a real head-to-head comparison on a real physical device (`DEC-130`/`DEC-131`)** — both candidates genuinely downloaded, loaded, and ran real inference: **Gemma 4 E4B 17% validity, 0.1 tok/s; Llama 3.2 3B 67% validity, 0.8 tok/s.** `decideWinner()`'s own real mechanical logic (a 50-point validity gap, far past its 5-point closeness threshold) makes Llama 3.2 3B a decisive, genuine winner on measured accuracy and speed — not merely because Gemma initially failed to finish downloading (`DEC-111`'s original emulator-DNS theory is superseded; the real cause was a retry-budget/transfer-length mismatch, fixed in `DEC-130`). Full detail: `STATUS_INDEX.md`, `DECISIONS_LOG.md` `DEC-130`/`DEC-131`. |
| On-device fallback | SmolLM2-1.7B | Locked |
| Generator, Judge | Gemini Flash | Locked |
| Fast/cheap cloud | Gemini Flash-Lite | Locked |
| Critic | Llama 3.3 70B via Groq | Locked |
| Embeddings | Qwen3-Embedding-0.6B | Locked (dimension pending confirmation) |
| Router classifier | Classical ML, self-trained | Locked |
| Injection guard | Pretrained, off-the-shelf | Locked |
| Career search | Tavily (DEC-004) | Locked, Exa named fallback |

Full detail: `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §10.

---

## 6. Real Code Index — what exists, where (structure is permanent; counts are not, and live in `STATUS_INDEX.md`)

| Package | Contents |
|---|---|
| `backend/main.py` | FastAPI app, `/health` |
| `backend/gate/schemas.py` | `ActionType`, `Stakes`, `EvidenceRef`, `Finding`, `Objection`, `ActionProposal`, `GateVerdict`, `Position`, `ResourceClaim`, `ImpactDelta` |
| `backend/gate/prompts.py` | Critic, Judge, CoverageCheck-extraction prompts |
| `backend/gate/validators.py` | All 9 Stage A validators |
| `backend/features/*.py` | The feature-module layer (waiting_on, subscription_detective, meeting_load, predictive_risk, honesty_log, search, style_reply, self_test_harness, career_digest, computed_state, verdict_outcome_mapping, and any added since) |
| `mobile/lib/**` | The mobile app — platform features and every real screen |
| `.github/workflows/ci.yml` | lint (ruff) + test + build + Trivy |

**Authoritative source for current test counts, per-item real/specified status, and how many feature modules or mobile screens actually exist right now: `specs/tier3_verification/STATUS_INDEX.md` — never this table.** This document previously restated a specific total here ("50 tests," "11 feature modules"), and it drifted twice — once caught and corrected mid-project (`DEC-006`), once not, directly contradicting the ADD's own separately-drifted number by the time both were checked together. The fix is the same one that already worked for `QUORUM_GATE_SPECIFICATION.md`: this table holds the permanent *shape*, never the count.

---

## 7. Open Items — pointer, not a restated list

**Authoritative source: `STATUS_INDEX.md`'s "Known open items" — never this section.** The five items open at this document's last substantive revision are preserved below for historical context; genuine new open items have emerged since, during real implementation work, and belong only in the one place that's actually kept current.

1. **RESOLVED, real Sprint 0 result, run to genuine completion on a real physical device (`DEC-130`, superseding `DEC-111`):** on-device primary model — Llama 3.2 3B, a real, mechanically-decided winner (Gemma 4 E4B never finished a real, ordinary interrupted download; Llama 3.2 3B genuinely downloaded, loaded, and passed real inference at 67% validity; see §5 above).
2. **RESOLVED, real Sprint 0 result, reconfirmed on real hardware (`DEC-130`):** Flutter llama.cpp plugin — `llamadart`, confirmed real and working via a real, successful health-check model load (`SmolLM2-135M-Instruct-Q2_K.gguf`) on a real physical device, before either Full-tier candidate was ever attempted.
3. Real Cloud Run cold-start latency under actual model footprint — unmeasured.
4. Whether `pg_cron`'s own firing prevents Supabase's inactivity pause, independent of the keep-alive ping — unmeasured.
5. Embedding vector dimension for the `note_embeddings` pgvector column — confirm against the loaded Qwen3-Embedding-0.6B model at integration time, do not hardcode from assumption.

---

*This document supersedes nothing by redesign — it is the condensed index over `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md`, `QUORUM_DATA_CONTRACTS.md`, `QUORUM_CONFIGURATION_CONSTANTS.md`, and `QUORUM_GATE_SPECIFICATION.md`. Read this first; read the others for the depth this document points at.*
