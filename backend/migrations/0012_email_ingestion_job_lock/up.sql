-- A real, singleton row used as this job's own concurrency guard --
-- see features/email_ingestion.py's own top-of-file docstring for the
-- full real account of why this shape, not a Postgres session-level
-- advisory lock, is the correct real primitive here.
--
-- REAL, LIVE-DISCOVERED INFRASTRUCTURE CONSTRAINT, found by this
-- session's own CRITICAL-tier-review-fix testing, not assumed in
-- advance: this backend's real `SUPABASE_URL` connects through
-- Supabase's own PgBouncer pooler in TRANSACTION-POOLING mode
-- (`aws-0-ap-south-1.pooler.supabase.com:6543`), confirmed live by a
-- real, reproduced failure -- a session-level `pg_try_advisory_lock`/
-- `pg_advisory_unlock` pair, held across two logically-separate
-- `asyncpg` calls with no explicit transaction wrapping them, silently
-- failed to serialize a real, live contention test: PgBouncer's
-- transaction-pooling mode does not guarantee the SAME underlying
-- Postgres backend connection (and therefore the same session) across
-- separate statements on what `asyncpg` presents as one logical
-- connection. A real row, updated via one single, atomic
-- `UPDATE ... WHERE ... RETURNING` statement, has no such dependency --
-- every statement here is already a genuinely self-contained,
-- single-statement transaction, exactly what transaction-pooling mode
-- is designed to serve correctly.
CREATE TABLE email_ingestion_job_lock (
    singleton   BOOLEAN PRIMARY KEY DEFAULT true CHECK (singleton),
    running     BOOLEAN NOT NULL DEFAULT false,
    started_at  TIMESTAMPTZ NULL
);

INSERT INTO email_ingestion_job_lock (singleton, running, started_at) VALUES (true, false, NULL);
