# QUORUM — Configuration Constants

**Tier:** `tier1_foundation` · **Volatility:** Stable content, real-world direct edits — corrected here during a full staleness audit: this previously read "Frozen — amended, never edited directly · Version: 1.0," which didn't match how this document was actually kept current. In practice it was edited directly, in place, whenever a genuine gap was found, each edit disclosed in `DECISIONS_LOG.md` rather than through a separate "amendment" mechanism or an incremented version number — neither was ever actually used across the real project.

**Purpose:** every hardcoded number in the system, in one place. No session spec should ever restate a number inline without citing this document — that's how numbers silently drift across a codebase. Where a constant is enforced by a schema's own type (not just application logic), that's noted explicitly, because it's a stronger guarantee.

---

## 1. Stakes Classification (hardcoded lookup, never learned)

| `ActionType` | Stakes | Verification required |
|---|---|---|
| `send_email` | S3 | Full Gate + mandatory human approval |
| `create_calendar_event_external` | S3 | Full Gate + mandatory human approval |
| `create_calendar_event_local` | S2 | Stage A + single-check Stage B |
| `create_task` | S1 | Stage A only |
| `update_task` | S1 | Stage A only |
| `log_expense` | S1 | Stage A only |
| `update_budget` | S2 | Stage A + single-check Stage B |
| `create_note` | S1 | Stage A only |
| `update_application_status` | S1 | Stage A only |
| `archive_email` | S1 | Stage A only |
| `label_email` | S0 | None |

**Any new `ActionType` added to `gate/schemas.py` requires a corresponding row here in the same change.** This table has no default — an action type with no entry is a bug, not an implicit S0.

---

## 2. The Gate

| Constant | Value | Enforcement |
|---|---|---|
| Max content-revision rounds | 1 | **Enforced by `GateVerdict.revision_count`'s type bound `[0,1]`** — not just application logic |
| Max infrastructure-failure retries | 2 | Application logic (retry-with-backoff, separate from the revision cap) |
| Judge role-label visibility | stripped | Application logic — Generator/Critic identity never passed to Judge prompt |
| Judge objection ordering | randomized | Application logic |
| `Finding.confidence` range | `[0.0, 1.0]` | **Enforced by Pydantic `Field(ge=0.0, le=1.0)`** |

---

## 3. Router

| Constant | Value |
|---|---|
| Complexity tiers | C0 (on-device eligible), C1 (cloud, single-domain), C2 (cloud, multi-domain/negotiation) |
| Complexity classifier cold-start | hardcoded rule thresholds |
| Complexity classifier upgrade trigger | once nightly Tier-1/Tier-2 replay produces sufficient labeled volume — **no fixed number set; this is a real, deliberately unspecified threshold, to be set from observed replay volume in Sprint 6, not guessed now** |

---

## 4. Feature Modules — pulled directly from real, tested code

| Constant | Value | Source file |
|---|---|---|
| Waiting-On staleness threshold | 4 days (default parameter, overridable) | `waiting_on.py` |
| Subscription min occurrences | 3 | `subscription_detective.py` |
| Subscription interval tolerance | ±5.0 days around a 30-day target | `subscription_detective.py` |
| Meeting-load working hours/day | 8.0 hours (default) | `meeting_load.py` |
| Meeting-load buffer fraction | 0.25 (25% of the day reserved, never bookable) | `meeting_load.py` |
| Meeting-load overload threshold | 0.7 (flags when committed time exceeds 70% of buffer-adjusted availability) | `meeting_load.py` |
| Predictive-risk density tolerance | ±1 deadline, when matching historical weeks | `predictive_risk.py` |
| Predictive-risk flag threshold | historical correction rate ≥ 0.5 at matching density | `predictive_risk.py` |
| Unified search result cap | top 10 | `search.py` |
| Unified search max backfill per request | 50 rows (a real, enforced `LIMIT`, not a soft intention) — this backend has no write path that creates a task/expense/application, so there is no "on creation" moment to embed at and `search()` lazily backfills inline instead; at Cloud Run `--concurrency=1`, an unbounded backfill would block a whole instance and could exceed the request timeout entirely. 50 is a real, disclosed, reasoned choice, not a measured optimum: ~0.2–0.5s per real embedding call puts it around 10–25s, well inside the real 300s timeout. A first search over a large unembedded corpus can therefore return honestly incomplete results, and self-heals across calls (`DEC-120`) | `search.py` |
| Career digest summary cap | 5 points (a brief, not a report) | `career_digest.py` |
| Style-reply max style examples | 3 | `style_reply.py` |
| Trust Digest stability threshold | 0.01 (1 percentage point — a week-over-week success-rate change smaller than this reports as "stable," not noise misread as a real trend) | `trust_digest.py` — added during a full staleness audit; genuinely missing despite this document's own stated purpose |
| Today capacity working hours/day | 8.0 hours (default) — the same real constant `meeting_load.py` already defines above, reused directly rather than duplicated, per this document's own single-source-of-truth discipline | `today.py` (`DEC-119`) |
| Today budget monthly limit | ₹50,000 (default) — a real, disclosed, reasoned placeholder: no per-user budget-configuration feature exists anywhere in this app yet, so this is a genuinely global default until one does, the same real, disclosed-choice pattern already established for `REFRESH_TOKEN_TTL_DAYS` | `today.py` (`DEC-119`) |

---

## 5. Negotiation

| Constant | Value |
|---|---|
| Conflict trigger | ≥2 domains with overlapping resource claims |
| Options presented | exactly 2 complete resolutions + "do nothing", always |
| Preference-weight activation | gated behind 5+ real observed user choices — before that, neutral ordering |
| Preference-weight correction trigger | user disagrees with weighted order 2 times consecutively in one category → system asks explicitly rather than continuing to guess |

---

## 6. Extended-Outage Local Continuity Mode

| Constant | Value |
|---|---|
| Outage detection — consecutive failures | 3 cross-provider call failures |
| Outage detection — connectivity check | confirmed unreachable for 2+ continuous minutes |
| Recovery | automatic, immediate on first successful health-check |
| S3 behavior in degraded mode | prepared, labeled "not yet verified," **never sent regardless of tap** — no numeric constant, an absolute rule |

---

## 7. On-Device Model Tiering

| Tier | Device RAM | Model |
|---|---|---|
| Full | ≥ 8GB | Primary — **SmolLM2-1.7B, resolved live by Sprint 0.** Real, mechanical decision (`ModelBenchmark.decideWinner()`'s own `StateError` escalation path, per `IMPL_00`'s design): both real Full-tier candidates (Gemma 4 E4B, Llama 3.2 3B) genuinely failed to load on the real Android emulator this project's real Sprint 0 run used — confirmed, honest reason captured directly from the device: `LlamaException: Failed to download ... (SocketException: Failed host lookup: 'huggingface.co' ...)`, a real, recurring emulator-level DNS relay failure (see `DECISIONS_LOG.md` `DEC-111`), not a RAM-capacity or inference-capability finding — neither candidate's real download ever completed enough to reach the load or inference stage. Per this project's own "trust the mechanical decision, never second-guess it with human intuition after the fact" discipline, this stands as the real, current, decided outcome, not a placeholder pending a cleaner re-run. |
| Light | 4GB – 8GB | SmolLM2-1.7B |
| Cloud-only | < 4GB | No local model; all C0 work routes to Gemini Flash-Lite |

| Model | Approximate RAM footprint (4-bit quantization) |
|---|---|
| Gemma 4 E4B | ~5GB |
| SmolLM2-1.7B | ~1.1GB |

---

## 8. Cloud LLM Free-Tier Quotas (verified live, current as of this project's most recent research pass — re-verify before relying on these long-term, per this project's own repeated experience of free-tier volatility)

| Provider / model | Quota |
|---|---|
| Gemini Flash | 10 RPM, 250,000 TPM, 1,500 requests/day |
| Gemini Flash-Lite | up to 15–30 RPM, ~1,000–1,500 requests/day |
| Groq (Llama 3.3 70B) | ~30 RPM, ~1,000 requests/day, ~6,000 TPM |
| Tavily | 1,000 free API credits/month; 1 credit per basic search (the endpoint Quorum actually uses) |

---

## 9. Self-Hosted / Infrastructure

| Constant | Value |
|---|---|
| Cloud Run concurrency | **1**, explicit — closes a real cross-user state-isolation risk |
| Cloud Run free-tier eligible regions | `us-central1`, `us-east1`, `us-west1` |
| Cloud Run free-tier monthly ceiling | 2,000,000 requests · 360,000 GB-seconds · 180,000 vCPU-seconds |
| Supabase free-tier storage | 500MB Postgres |
| Supabase inactivity pause | 7 days (tightened February 2026) |
| Supabase keep-alive ping frequency | every 3–4 days (comfortably inside the 7-day window; GitHub Actions' 15–60 min drift is irrelevant at this cadence) |
| Upstash Redis free tier | 500,000 commands/month, 256MB |
| Langfuse Cloud (Hobby) | 50,000 traced units/month, 30-day retention, 2 users |
| Embedding dimension (Qwen3-Embedding-0.6B) | **SUPERSEDED, `DEC-120`** — this row's own caution ("do not hardcode in a migration until verified against the loaded model at integration time") was correct and earned itself twice at real integration time; see the row below. Qwen3-Embedding-0.6B itself was never wired into this backend, and `QUORUM_MASTER_REFERENCE.md` §5's locking of it is superseded by a real, disclosed, Preethish-approved switch to Gemini's embedding API |
| Embedding model and dimension, real and live (`gemini-embedding-001`) | **768**, requested explicitly via `outputDimensionality` (Gemini's real Matryoshka/MRL truncation), never the model's own 3072 default. Both facts confirmed by real, live API calls before any migration hardcoded them: `text-embedding-004` (a plausible first guess) returns a real 404 for this project's key, and 3072 — while real — is **unusable here**, because pgvector refuses to build an HNSW or IVFFlat index above 2000 dimensions (confirmed live against the real production database), which would have condemned every search to a permanent sequential scan. MRL-truncated output is **not** pre-normalized (measured L2 norm `0.582911`, versus `1.000000` at 3072), so `core/embeddings.py` re-normalizes explicitly. Real consumers: `core/embeddings.py`, `migrations/0005_search_embeddings/` |

---

## 10. Security & Data

| Constant | Value |
|---|---|
| JWT access token lifetime | 15 minutes |
| JWT refresh token | rotating on use, server-side revocation list |
| Raw email body retention | 90 days, then structured extraction + embeddings only |

## 10.1 Sensitive Pattern Definitions — the single source of truth for both the Privacy Gate and trace-scrubbing

**Real gap this closes:** the ADD requires trace-scrubbing to reuse "the Privacy Gate's own rule-layer detectors... not a separately maintained pattern set" — but the Privacy Gate (`MOBILE_03`, Dart, on-device) and trace-scrubbing (`IMPL_22`, Python, backend) are necessarily two different implementations on two different platforms. They cannot literally share code. What they *can* share is this table — the actual pattern definitions, written once, here, with each platform's implementation required to match it exactly rather than maintaining its own independent pattern list.

| Category | Pattern (conceptual) | Real regex (Python reference) |
|---|---|---|
| Credit/debit card | 13–19 digits, optional separators | `\b(?:\d[ -]*?){13,19}\b` |
| Aadhaar-style ID | 12 digits, commonly grouped 4-4-4 | `\b\d{4}\s?\d{4}\s?\d{4}\b` |
| OTP / verification code | 4–8 digits following a labeling word | `\b(?:OTP\|otp\|code\|verification code)[\s:]*(\d{4,8})\b` (case-insensitive) |

**Whichever platform implements this second must match this table exactly, not approximate it** — a real, checkable requirement, not a suggestion. (Both platforms are real now: `IMPL_22` on the backend, `MOBILE_03` on-device — this note originally named `MOBILE_03` as pending and was never updated once it shipped; corrected here as part of a full staleness audit.)

---

## 11. Evaluation

| Constant | Value |
|---|---|
| Golden scenario suite target size | 80 scenarios |
| Human-labeled precision/recall sample | ~15–20 real decisions/week |

---

## 12. What is deliberately NOT in this document

Prompt template text — that belongs in `QUORUM_GATE_SPECIFICATION.md`, since it's not a single scalar constant but structured content with its own versioning needs. Anything marked "pending Sprint 0" in the ADD's §19 — those are empirical unknowns, not constants to guess at here.

---

*Attach this document to every implementation session without exception — it is the one file every session should check a number against before hardcoding it inline.*
