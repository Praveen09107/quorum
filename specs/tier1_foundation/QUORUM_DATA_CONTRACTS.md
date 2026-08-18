# QUORUM — Data Contracts

**Tier:** `tier1_foundation` · **Volatility:** Stable content, real-world direct edits — corrected here during a full staleness audit: this previously read "Frozen — amended, never edited directly · Version: 1.0," which didn't match how this document was actually kept current. In practice it was edited directly, in place, whenever a genuine gap was found, each edit disclosed in `DECISIONS_LOG.md` rather than through a separate "amendment" mechanism or an incremented version number — neither was ever actually used across the real project.

**Purpose:** every data structure crossing a component boundary, exhaustively. If a value crosses a boundary and it isn't defined here, the boundary isn't fully specified. Where real code already exists, this document references it as authoritative rather than duplicating it — a copy that can drift is worse than a pointer.

---

## 1. The Gate's Core Schemas

**Authoritative source:** `backend/gate/schemas.py` — real, tested, validated (`backend/tests/test_gate_schemas.py`, 5/5 passing). This section documents the contract; the file is the contract.

### 1.1 `ActionType` (closed enum)

```
send_email · create_calendar_event_external · create_calendar_event_local ·
create_task · update_task · log_expense · update_budget · create_note ·
update_application_status · archive_email · label_email
```

Every real action the system can propose maps to exactly one entry in `CONSTANTS.STAKES_TABLE` (§3 of `QUORUM_CONFIGURATION_CONSTANTS.md`). This enum is the join key between the action layer and the stakes classification layer — adding a new action type requires a corresponding stakes-table entry in the same change, never a follow-up.

### 1.2 `EvidenceRef`

| Field | Type | Constraint |
|---|---|---|
| `source_type` | `Literal["calendar","task","budget","email_thread","contact_history"]` | closed set |
| `source_id` | `str` | required |
| `retrieved_at` | `datetime` | auto-populated, UTC |

A pointer to real data, never restated claim text. This is what makes a `Finding` falsifiable — anyone can re-fetch `source_id` and check the claim independently.

### 1.3 `Finding` — the three-valued verification result

| Field | Type | Constraint |
|---|---|---|
| `validator` | `str` | e.g. `"TemporalFactCheck"` |
| `claim` | `str` | the specific claim being checked |
| `evidence_state` | `Literal["verified_true","verified_false","no_data_found"]` | **never binary** — see rationale below |
| `source_ref` | `EvidenceRef \| None` | present when `evidence_state != no_data_found` |
| `confidence` | `float` | bounded `[0.0, 1.0]`, enforced by the schema itself, not application logic |

**Why three-valued, not boolean:** collapsing `verified_false` and `no_data_found` into one "fail" state produces false rejections when ground truth is merely incomplete (an informal meeting never entered into a calendar). Collapsing the other way — treating `no_data_found` as a pass — silently defeats verification. `no_data_found` is neither; it is an unresolved item that must reach Stage B for explicit judgment, never silently resolved either way by Stage A alone.

### 1.4 `Objection` — one Critic output

| Field | Type | Constraint |
|---|---|---|
| `category` | `Literal["tone","completeness","safety","commitment_wisdom","factual"]` | closed set |
| `severity` | `Literal["low","medium","high"]` | |
| `description` | `str` | required |
| `evidence_ref` | `EvidenceRef \| None` | optional — not every objection is fact-grounded (tone, for instance) |
| `suggested_fix` | `str \| None` | optional |
| `signed_off` | `bool` | default `False` |

**The obligation-to-critique rule, enforced by shape:** the Critic must return at least one real `Objection`, **or** an `Objection` with `signed_off=True` and non-empty `description` explaining why nothing was found. An empty list is never a valid Critic output — it's indistinguishable from "didn't try," which the schema makes structurally impossible to produce silently.

### 1.5 `ActionProposal`

| Field | Type | Constraint |
|---|---|---|
| `proposal_id` | `UUID` | auto-generated |
| `action_type` | `ActionType` | required |
| `payload` | `dict` | action-type-specific shape, validated by the domain agent before Gate entry |
| `evidence` | `list[EvidenceRef]` | default empty |
| `assumptions` | `list[str]` | explicit, never implicit |
| `context_used` | `ContextSnapshot` | what informed the draft — thread id, retrieved notes, preference-weights version |
| `created_at` | `datetime` | auto-populated, UTC |

### 1.6 `GateVerdict`

| Field | Type | Constraint |
|---|---|---|
| `decision` | `Literal["approve","revise","reject","escalate_to_human"]` | see §1.7 for the outcome mapping |
| `revised_payload` | `dict \| None` | present only when `decision == "revise"` |
| `findings` | `list[Finding]` | Stage A's complete output |
| `objections` | `list[Objection]` | Stage B's complete output, empty for S0/S1 |
| `trace_id` | `str` | Langfuse trace correlation |
| `revision_count` | `int` | **bounded `[0, 1]` by the schema itself** — the one-revision-round rule is not application logic that could be forgotten, it's a type constraint |

### 1.7 `GateVerdict.decision` → evaluation `Outcome` mapping (DEC-002)

**Authoritative source:** `backend/features/verdict_outcome_mapping.py`. Restated here because it's a boundary contract, not because the code should be duplicated:

- `approve` → `APPROVED_UNCHANGED`, always.
- `revise` / `reject` → `CAUGHT_BY_GATE`, always — the granular revise-vs-reject distinction is a deliberate simplification for the user-facing Honesty Log; it remains available in the underlying trace for anyone who drills in.
- `escalate_to_human` → **cannot resolve without `human_action`.** `edited`/`rejected` → `CORRECTED_BY_USER`. `approved_as_is` with `escalation_reason == "no_data_found"` → `UNCERTAIN_NO_DATA` (genuinely uncertain, not falsely confident). `approved_as_is` otherwise → `APPROVED_UNCHANGED`.

### 1.8 Negotiation schemas — `Position`, `ResourceClaim`, `ImpactDelta`

| `Position` field | Type |
|---|---|
| `domain` | `Literal["calendar","tasks","finance"]` |
| `concern` | `str` |
| `severity_claim` | `str` |
| `resource_claims` | `list[ResourceClaim]` |
| `proposed_resolution` | `str` — **the field that turned synthesis from invention into merging (§4 of `QUORUM_GATE_SPECIFICATION.md`)** |
| `evidence` | `list[EvidenceRef]` |

`ResourceClaim`: `claim_type: Literal["time","money","effort"]`, `amount: float`, `unit: str`.

`ImpactDelta`: `metric: Literal["deadline_slack_hours","budget_remaining_fraction","task_hours_committed"]`, `before: float`, `after: float`, `direction: Literal["improves","worsens","unchanged"]`. **Every field is code-computed. `ImpactDelta` is never produced by a model call — this is the literal implementation of "the model narrates, the code computes."**

---

## 2. Feature-Layer Schemas (real, existing code — referenced, not duplicated)

These are internal value objects, never crossing an untrusted boundary — plain `@dataclass`, not Pydantic, deliberately (see §5 rationale). Each is authoritative at its real file location:

| Schema | File | Used by |
|---|---|---|
| `SentMessage` | `backend/features/waiting_on.py` | Waiting On tracker |
| `Expense`, `DetectedSubscription` | `backend/features/subscription_detective.py` | Subscription Detective |
| `CalendarEvent`, `LoadAssessment` | `backend/features/meeting_load.py` | Meeting-Load Defense |
| `HistoricalWeek`, `RiskAssessment` | `backend/features/predictive_risk.py` | Predictive Risk |
| `WeeklyTrustSummary`, `TrendResult` | `backend/features/trust_digest.py` | Trust Digest — a genuinely new backend module, not an existing one exposed; confirmed no digest/trend aggregation existed anywhere before `MOBILE_17` built it |
| `Memory` | `backend/security/memory_transparency.py` | Memory Transparency — another genuinely new module: `mem0` was referenced throughout the backend (purged on deletion, read for calendar buffer preferences) but no schema for a single memory existed anywhere before `MOBILE_19` built one |
| `LoggedAction`, `Outcome` | `backend/features/honesty_log.py` | Honesty Log |
| `SearchableItem` | `backend/features/search.py` | Unified Fast Search |
| `PastMessage` | `backend/features/style_reply.py` | Style-Conditioned Replies |
| `AdversarialScenario`, `ScenarioResult` | `backend/features/self_test_harness.py` | Self-Test Harness |
| `SearchFinding`, `CompanyDigest` | `backend/features/career_digest.py` | Company Research Digest |
| `TaskCommitment`, `CapacityState`, `BudgetState` | `backend/features/computed_state.py` (Python reference) and `mobile/lib/features/computed_state.dart` (on-device, parity hand-verified) | Today screen computed numbers |

---

## 3. Database Schema — Postgres (Supabase)

**Status: specified, not yet executed against a live database** — no Supabase project has been provisioned in this environment. The following is a complete, implementation-ready specification; it has not been run.

```sql
-- Core event log — every proposal's lifecycle, feeding L2 evaluation.
CREATE TABLE action_events (
    proposal_id     UUID PRIMARY KEY,
    action_type     TEXT NOT NULL,
    stakes          TEXT NOT NULL CHECK (stakes IN ('S0','S1','S2','S3')),
    payload         JSONB NOT NULL,
    gate_decision   TEXT CHECK (gate_decision IN ('approve','revise','reject','escalate_to_human')),
    outcome         TEXT CHECK (outcome IN ('approved_unchanged','corrected_by_user','caught_by_gate','uncertain_no_data')),
    trace_id        TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at     TIMESTAMPTZ
);
CREATE INDEX idx_action_events_created_at ON action_events (created_at DESC);
CREATE INDEX idx_action_events_outcome ON action_events (outcome) WHERE outcome IS NOT NULL;

-- Tasks (Tasks domain)
CREATE TABLE tasks (
    task_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    title           TEXT NOT NULL,
    estimated_hours NUMERIC(4,1) NOT NULL,
    deadline        TIMESTAMPTZ,
    status          TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','done','cancelled')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Expenses (Finance domain)
CREATE TABLE expenses (
    expense_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    payee           TEXT NOT NULL,
    amount          NUMERIC(10,2) NOT NULL,
    occurred_at     TIMESTAMPTZ NOT NULL,
    source          TEXT NOT NULL CHECK (source IN ('on_device','manual','extracted')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Applications (Career domain)
CREATE TABLE applications (
    application_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    company         TEXT NOT NULL,
    role            TEXT,
    status          TEXT NOT NULL DEFAULT 'applied',
    source_thread_id TEXT,
    deadline        TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Embeddings (pgvector) — dimension pending confirmation, see §5.2
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE note_embeddings (
    embedding_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    content         TEXT NOT NULL,
    embedding       VECTOR(1024),  -- CONFIRM against Qwen3-Embedding-0.6B's real output dimension at integration time; not asserted here as certain.
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Interviews (Career domain) — split from applications; a real gap found
-- during document audit, previously implied but never defined.
CREATE TABLE interviews (
    interview_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id  UUID NOT NULL REFERENCES applications(application_id),
    scheduled_at    TIMESTAMPTZ,
    format          TEXT CHECK (format IN ('phone', 'video', 'onsite')),
    prep_task_ids   UUID[] DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'completed', 'cancelled')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Retry queue — the "lightweight Postgres table, drained on a schedule"
-- the ADD (§13.4) commits to, but which was never actually defined until
-- this audit found the gap.
CREATE TABLE retry_queue (
    retry_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type        TEXT NOT NULL,
    payload         JSONB NOT NULL,
    attempt_count   INT NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_error      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_retry_queue_next_attempt ON retry_queue (next_attempt_at) WHERE attempt_count < 5;

-- LangGraph checkpoints — standard LangGraph Postgres checkpointer table
-- shape, created by the library's own migration, not hand-specified here.
```

---

## 4. Redis (Upstash) Key Patterns

| Pattern | Purpose | TTL |
|---|---|---|
| `ratelimit:{user_id}:{window}` | Per-user request rate limiting | 60s rolling window |
| `cache:coverage_check:{email_id}` | Cached CoverageCheck extraction (reused across Stage A re-checks) | 24h |
| `cache:embedding:{content_hash}` | Cached embedding to avoid recomputation | 7d |
| `queue:retry:{job_type}` | Postgres-table-drained retry queue is primary (§13.4 of the ADD); this key namespace reserved if a lightweight Redis-side dedup is later needed | n/a — not currently used |

---

## 5. REST API Contracts (FastAPI)

### 5.1 `GET /health`
Real, implemented, verified. Response: `{"status": "ok"}`, `200`.

### 5.2 `POST /actions/{action_id}/approve` (specified, not yet implemented)
Request: none (action already exists server-side). Response: `202 Accepted`, body `{"status": "queued_for_execution"}` — actual send/write happens asynchronously; the client polls status (§5.3).

### 5.3 `GET /actions/{action_id}/status` (specified — this is the polling endpoint replacing WebSocket streaming)
Response:
```json
{
  "proposal_id": "uuid",
  "current_stage": "stage_a" | "stage_b" | "complete",
  "findings_so_far": [/* Finding objects, populated incrementally */],
  "verdict": null | {/* GateVerdict, once complete */}
}
```
Client polls at 1–2s intervals while a run is in progress (§9 of the product experience review — this is the mechanism that partially recovers the live-streaming experience the serverless deployment decision gave up).

### 5.4 `GET /today` (specified — extended here, a real gap found before building `MOBILE_05` against it)

**Original scope** (`CapacityState`/`BudgetState`) powers "Holding steady" alone. **Real gap found:** nothing in this document ever specified what "Needs you now" — the zone ranked highest by urgency — actually receives. Extended now, before `MOBILE_05` builds against it, rather than discovered mid-session.

```json
{
  "capacity": { "...CapacityState, unchanged..." },
  "budget": { "...BudgetState, unchanged..." },
  "needs_you_now": [
    {
      "proposal_id": "uuid",
      "action_type": "send_email",
      "stakes": "S3",
      "payload": { "to": "priya@x.com", "body": "..." },
      "created_at": "2026-08-20T14:00:00Z"
    }
  ]
}
```

`needs_you_now` is every real proposal currently in `pending_human_approval` (§2 of `QUORUM_GATE_SPECIFICATION.md`) — never pre-sorted server-side; ranking by urgency is a client-side concern (`MOBILE_05`), since "urgency" here is a display decision, not a fact about the data itself.

**A second real gap, found the same way, before `MOBILE_07` was built against it:** nothing anywhere specified how the client discovers active negotiations exist — `POST /negotiations/{negotiation_id}/choose` (§5.6) lets you act on a negotiation you already know about, but nothing surfaces that one is active in the first place. Fixed here, extending the same `/today` response:

```json
{
  "capacity": { "..." },
  "budget": { "..." },
  "needs_you_now": [ "..." ],
  "in_motion": [
    {
      "negotiation_id": "uuid",
      "conflicted_domains": ["calendar", "finance"],
      "started_at": "2026-08-20T09:00:00Z"
    }
  ]
}
```

`in_motion` is every negotiation currently awaiting a real choice — again unsorted server-side; staleness ranking is a client concern (`MOBILE_07`), same reasoning as `needs_you_now`'s ranking.

**Restated explicitly, since it was present before this extension and must not be lost in it:** `capacity` and `budget` each carry `source: "live_backend" | "local_mirror"` — the client must render this label, never silently presenting one as the other (§9.4 of the ADD, the F4 fix).

### 5.5 Auth endpoints (specified — a real gap found during audit, absent until now)

`POST /auth/token` — exchanges a Gmail OAuth authorization code (server-side, per §14.2 of the ADD) for a Quorum access + refresh token pair.
`POST /auth/refresh` — rotates the refresh token, issues a new 15-minute access token.
`POST /auth/revoke` — the "sign out everywhere" control (§14.1 of the ADD); invalidates the server-side revocation list entry for the current user's refresh tokens.

### 5.6 `POST /negotiations/{negotiation_id}/choose` (specified — absent until now)

Request: `{"chosen_option": "option_a" | "option_b" | "do_nothing"}`. Response: `202 Accepted` — downstream actions from the chosen option are enqueued, each re-entering the Gate at its own stakes level (§8.3 of the ADD).

### 5.7 `GET /search?q=...` (specified — improved here, not a missing-endpoint gap this time)

Wraps `search.py`'s real, tested ranking function (§2 of this document). **A real, honest distinction worth stating explicitly, since it's the opposite of `needs_you_now`/`in_motion`'s pattern:** search ranking genuinely requires scoring the full corpus, so it stays entirely server-side — the response arrives **already sorted**, unlike Today's zones where the client does the final ordering. Response, capped at 10 per `QUORUM_CONFIGURATION_CONSTANTS.md` §4:

```json
[
  {
    "item_id": "uuid",
    "item_type": "email",
    "text": "Re: budget approval for the Q3 offsite",
    "timestamp": "2026-08-10T09:00:00Z"
  }
]
```

The real ranking score itself is not exposed — it's an internal ordering mechanism, not a fact meaningful to show a person; the array's order *is* the ranking.

### 5.8 `DELETE /account` (specified — absent until now)

Required to exist before real user data enters the system (§14.7 of the ADD). Purges Postgres, pgvector, and mem0 records for the user, and revokes stored OAuth tokens. Irreversible — this endpoint is itself S3-equivalent and requires the same explicit-confirmation UI pattern as any other irreversible action, even though it never enters the Gate (it's an account-level operation, not a domain action).

### 5.9 `GET /waiting_on` (specified — a third real gap found the same way as `/today`'s two, before `MOBILE_10` was built against it)

`SentMessage` (§2) is documented explicitly as internal-only — never crossing the API boundary directly. What was missing: any real endpoint exposing the *output* of `find_stale_waiting_on()` for display. Fixed here:

```json
[
  {
    "recipient": "priya@x.com",
    "subject": "Re: budget approval",
    "sent_at": "2026-08-10T09:00:00Z"
  }
]
```

Already pre-filtered server-side — `find_stale_waiting_on()`'s threshold decision (what counts as "stale" at all) is real business logic, not a display concern, so it stays server-side. Computing *how* to display the resulting age (e.g., "5 days" vs. a formatted date) is a client concern, consistent with `needs_you_now` and `in_motion`'s established ranking/formatting split.

### 5.10 `GET /career_pipeline` (specified — a fourth real gap found the same way as the prior three, before `MOBILE_11` was built against it)

The real `applications` table (`backend/migrations/001_initial_schema.sql`) has existed since infrastructure work, with no endpoint ever exposing it for display. Fixed here:

```json
[
  {
    "application_id": "uuid",
    "company": "Notion",
    "role": "Software Engineer",
    "status": "interview_scheduled",
    "deadline": "2026-09-01T00:00:00Z"
  }
]
```

**A real, deliberate note for whichever session consumes this:** `applications.status` has no `CHECK` constraint at the database level (unlike `interviews.status`, which does) — the real status vocabulary is open, not closed to a fixed enum. Only `"applied"` and `"interview_scheduled"` are exercised anywhere in the current real codebase (`test_career_agent.py`). A client grouping applications by status must handle an unrecognized status string gracefully, not assume a fixed four-stage pipeline.

### 5.11 `GET /career_pipeline/{application_id}/digest` (specified — a fifth real gap found the same way as the prior four, before `MOBILE_12` was built against it)

`CompanyDigest` (§2) is documented as internal-only, same pattern as `SentMessage` before it — real, compiled, and never exposed. Fixed here:

```json
{
  "company": "Notion",
  "summary_points": ["Raised a large Series C round in 2021.", "..."],
  "source_count": 3
}
```

**A real, honest edge case worth stating explicitly:** a digest may not exist yet for a given application — per `MOBILE_09`'s Career agent design (`IMPL_17`), compilation only happens once a real interview is detected *and* real search findings have actually returned, which can lag behind detection. A client requesting a digest before it exists should receive a real `404`, not an empty-but-200 response — the absence of a digest is a genuinely different state from "a digest exists with zero points," and collapsing the two would misrepresent which is true.

### 5.12 `GET /finance/subscriptions` (specified — a sixth real gap found the same way as the prior five, before `MOBILE_13` was built against it)

`DetectedSubscription` (§2) is documented as internal-only, same pattern as every prior gap. `detect_subscriptions()` has been real and tested since well before mobile work began. Fixed here:

```json
[
  {
    "payee": "Netflix",
    "average_amount": 649.00,
    "occurrences": 4,
    "average_interval_days": 30.2
  }
]
```

Amounts arrive as raw numbers; currency formatting (₹, consistent with this project's established convention) is a client display concern.

### 5.13 `GET /honesty_log` (specified — a seventh real gap found the same way as the prior six, before `MOBILE_15` was built against it)

`build_honesty_feed()`'s real output has never been exposed to a client. Fixed here — the response mirrors the real function's dict shape exactly, since that shape *is* the design commitment (successes and `failures_and_catches` at the same structural level, never one nested inside or subordinate to the other):

```json
{
  "total": 42,
  "success_rate": 0.857,
  "successes": [
    {"action_id": "uuid", "timestamp": "2026-08-10T09:00:00Z", "outcome": "approved_unchanged", "description": "Replied to Priya about Thursday"}
  ],
  "failures_and_catches": [
    {"action_id": "uuid", "timestamp": "2026-08-11T14:00:00Z", "outcome": "caught_by_gate", "description": "Draft claimed a meeting that didn't exist"}
  ],
  "genuinely_uncertain": []
}
```

**A real, load-bearing UI requirement, not a suggestion:** per `build_honesty_feed()`'s own docstring — "never filters anything out... shown with EQUAL prominence, not buried" — any client rendering this response must give `failures_and_catches` genuinely equal visual weight to `successes`, not a collapsed section, not a smaller font, not a lower position by default. This is the literal implementation of the project's own stated trust commitment, and a screen that violated it would be a real, meaningful failure, not a cosmetic one.

### 5.14 `GET /trust` (specified — an eighth real gap found while preparing `MOBILE_16`, alongside a real backend staleness finding fixed in the same session)

Wraps `self_test_harness.py`'s `run_self_test()` output. **A real backend finding, not just a missing endpoint:** that module's own docstring previously claimed the real Gate "doesn't exist yet as code" — false since `IMPL_08`, corrected directly in the same session this endpoint was specified. Nothing in the backend currently wires the real Gate into this harness; it still runs against `_stub_gate_for_demo`.

```json
{
  "total": 12,
  "caught": 11,
  "missed": [
    {"scenario_id": "S7", "expected": "reject", "actual": "approve", "passed": false}
  ],
  "results": [ "...every ScenarioResult, never filtered..." ],
  "target": "stub"
}
```

**A real, load-bearing requirement, matching the same honesty pattern as `source: live_backend | local_mirror`:** `target` is `"stub"` or `"real_gate"`, and any client displaying this data must render which one plainly — a self-test result against the stub gate is a real, useful signal that the harness itself works, but it is **not yet a real measurement of the actual Gate's adversarial performance**, and presenting it as if it were would be a genuine, meaningful misrepresentation of what's actually been tested.

### 5.15 `GET /trust_digest` (specified — a genuinely new backend module, not just a missing endpoint, found and built during `MOBILE_17`)

Wraps `trust_digest.py`'s real `compare_weeks()` — confirmed, before building, that no digest/trend aggregation existed anywhere in the backend prior to this session:

```json
{
  "current_week": {"week_start": "2026-08-10", "total_actions": 24, "success_rate": 0.875},
  "previous_week": {"week_start": "2026-08-03", "total_actions": 19, "success_rate": 0.789},
  "trend": "improving",
  "delta": 0.086
}
```

`trend` is one of `"improving"`, `"declining"`, `"stable"`, or `"insufficient_data"` — the last is a real, honest state (a week with zero actions, or no prior week yet), never silently reported as `"stable"`, which would falsely claim a real comparison was made.

### 5.16 `GET /memories` and `DELETE /memories/{memory_id}` (specified — a genuinely new capability, not just a missing endpoint, found and built during `MOBILE_19`)

`mem0` is referenced throughout the backend as a real storage layer — purged on account deletion (§5.8), read for calendar buffer preferences (`gate/validators.py`) — but no real schema for a single memory, and no real way for a client to list or delete one individually, existed anywhere before this session.

```json
// GET /memories
[
  {
    "memory_id": "uuid",
    "content": "Prefers 15-minute buffers before meetings",
    "category": "preference",
    "created_at": "2026-07-01T09:00:00Z"
  }
]
```

`DELETE /memories/{memory_id}` — real, individual, honest deletion, distinct from the full-account purge in §5.8. Response: `204 No Content` on success. **A real, deliberate design choice worth stating:** deleting one memory is genuinely reversible in spirit — the underlying preference or pattern could be relearned from future behavior — so this endpoint does **not** require the same S3-equivalent type-to-confirm gate `DELETE /account` does. Treating every deletion with maximal ceremony regardless of its actual stakes would be its own kind of dishonesty — a screen crying wolf on a low-stakes action teaches people to stop reading confirmations at all, which weakens the real ones.

### 5.17 `GET /tasks` (specified — found during a full specification audit: the Tasks domain has a real backend agent, schema, and `ActionType`s, but no mobile screen and no endpoint ever existed for it, unlike every other core domain)

```json
[
  {
    "task_id": "uuid",
    "title": "Finish the Q3 budget review",
    "estimated_hours": 2.5,
    "deadline": "2026-08-20T00:00:00Z",
    "status": "open"
  }
]
```

`status` is a genuinely closed set — `"open"`, `"done"`, `"cancelled"`, enforced by a real `CHECK` constraint at the database level (confirmed directly against `backend/migrations/001_initial_schema.sql`), unlike `applications.status`'s open vocabulary (§5.10). A client may safely assume exactly these three values, no defensive handling of an unrecognized status required — a real, meaningful difference from the Career pipeline's contract, worth stating explicitly so it isn't built the same defensive way out of habit.

---

## 6. MCP Tool Call Shapes

Each domain agent's tool calls carry the calling agent's declared domain, enforced server-side (not just by graph wiring) per the two-layer authorization design:

```json
{
  "tool": "gmail.send",
  "calling_agent_domain": "email",
  "payload": { "to": "...", "body": "..." }
}
```

A tool server rejects any call where `calling_agent_domain` doesn't match the tool's declared allowlist — e.g. `finance.write_budget` rejects any call not declaring `calling_agent_domain: "finance"`, regardless of what content the request carries.

---

## 7. Verification Status of This Document

- §1 (Gate core schemas): **verified live** — 5/5 tests passing, including rejection of invalid data (out-of-range confidence, out-of-bound revision count, invalid enum values). See `backend/tests/test_gate_schemas.py`.
- §2 (feature schemas): verified live in earlier sessions, referenced not re-verified here.
- §3 (Postgres): the real migration file **was proven against a real, local Postgres instance in the development sandbox** — schema executes cleanly, all 7 tables and their constraints confirmed. What remains genuinely unexecuted is the *live Supabase project* specifically — no cloud instance was ever provisioned in the course of this project. The original wording here ("specified, not executed") was imprecise about which of these two things was actually true; corrected during a full staleness audit.
- §4 (Redis): specified, not executed.
- §5 (REST): §5.1 verified live on the actual deployed Cloud Run service. **§5.15 (`GET /trust_digest`) is now also real and wired (Batch 10 Phase 3 Part B, `DEC-100`)** — a real FastAPI route, a real Postgres query against the real, live `action_events` table, real response shape, confirmed via `TestClient` against the real lifespan. **Not yet true of §5.15, disclosed rather than implied:** the currently-deployed Cloud Run revision predates this work — this endpoint has not yet been exercised against the actual public URL, only against the real database through a local `TestClient`; a fresh deploy is the real, tracked next step (`STATUS_INDEX.md`). §5.2–§5.14 and §5.16 remain specified, not implemented as live HTTP endpoints at all — none of those were ever wired into a real FastAPI route and executed end to end. **Important distinction, not to be lost in the "not implemented" label:** most of these endpoints wrap business logic that *is* real and tested at the function level — `waiting_on.py`, `search.py`, `self_test_harness.py`, and others are genuinely real; what's specified-but-unbuilt is only the thin REST layer connecting each to an HTTP route. §2's schema index names exactly which real module backs each one.
- §6 (MCP): specified, not implemented.

---

*Attach this document to any session touching the Gate, negotiation, or cross-domain data flow.*
