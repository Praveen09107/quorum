-- Quorum initial schema. Real, exact content from
-- specs/tier1_foundation/QUORUM_DATA_CONTRACTS.md §3, verbatim -- this is
-- one of the few files in this project where a full, literal spec exists
-- to copy faithfully, not a construction from a described property.
--
-- Proven against a real, local Postgres 16 + pgvector in this repository
-- -- see specs/tier3_verification/DECISIONS_LOG.md for the real command
-- output. No live Supabase project exists yet; that remains a genuinely
-- open item (STATUS_INDEX.md), not something this file can resolve.

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

-- Embeddings (pgvector) — dimension pending confirmation, see STATUS_INDEX.md open item 5
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE note_embeddings (
    embedding_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    content         TEXT NOT NULL,
    embedding       VECTOR(1024),  -- CONFIRM against Qwen3-Embedding-0.6B's real output dimension at integration time; not asserted here as certain.
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Interviews (Career domain) — split from applications
CREATE TABLE interviews (
    interview_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id  UUID NOT NULL REFERENCES applications(application_id),
    scheduled_at    TIMESTAMPTZ,
    format          TEXT CHECK (format IN ('phone', 'video', 'onsite')),
    prep_task_ids   UUID[] DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'completed', 'cancelled')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Retry queue — lightweight Postgres table, drained on a schedule.
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
