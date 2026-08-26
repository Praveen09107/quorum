-- Real, ready-to-run SQL for scheduling `POST /internal/email-
-- ingestion` (Phase 4, `DEC-140`) via pg_cron/pg_net.
--
-- SCHEDULE: `7,22,37,52 * * * *` -- fires every 15 minutes, the upper
-- end of `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §9.1's own real,
-- specified "polling; 5-15 min interval" for email specifically (the
-- other three real, live jobs poll cheaper, all-local-DB signals more
-- often; this one makes real, potentially slow, external Gmail calls
-- per user, so the less frequent end of the spec's own range is the
-- right real choice). None of `7,22,37,52` is a multiple of 5 (so this
-- job never coincides with `drain-retry-queue`'s own `*/5` marks or
-- `deadline-watch`/`spend-alert`'s own `:00`/`:30` marks), and neither
-- is `12`/`42` (`backfill-negotiation-detail`'s own marks) -- the same
-- real, disclosed timeout-collision lesson `DEC-134`/`DEC-135` already
-- established, applied here before this job is ever run live for the
-- first time, not discovered the hard way after.
--
-- TIMEOUT: `timeout_milliseconds := 270000` (270s) -- comfortably
-- above this job's own real, internal `EMAIL_INGESTION_BATCH_DEADLINE_
-- SECONDS = 240` (`features/email_ingestion.py`), so `pg_net` itself
-- never kills the real HTTP request before this job's own clean,
-- honest early-stop logic gets a real chance to return a real, partial
-- response first.
--
-- REAL CONCURRENCY SAFETY, already built and tested (`DEC-140`): this
-- job claims the singleton `email_ingestion_job_lock` row (migration
-- `0012`) before doing any real work -- a real, overlapping `pg_net`
-- fire (this job's own real batch still running past its own next
-- scheduled tick) is a real, honest, zero-cost no-op
-- (`already_running: true` in the response body), never a second,
-- wasteful concurrent Gmail poll.

CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pg_net;

-- Replace both placeholders before running (see enable_deadline_watch_
-- cron.sql's own comments for what each one is -- not repeated here).
SELECT cron.schedule(
    'email-ingestion',
    '7,22,37,52 * * * *',
    $$
    SELECT net.http_post(
        url := '<CLOUD_RUN_URL>/internal/email-ingestion',
        headers := jsonb_build_object('X-Internal-Secret', '<INTERNAL_DRAIN_SECRET>'),
        body := '{}'::jsonb,
        timeout_milliseconds := 270000
    );
    $$
);

-- Verification, once run for real:
--   1. SELECT * FROM cron.job WHERE jobname = 'email-ingestion';
--   2. SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 5;
--   3. THE REAL CHECK `DEC-134`'s own session taught: 'succeeded' in
--      job_run_details is NOT sufficient on its own -- also check
--      SELECT id, status_code, timed_out, error_msg FROM net._http_response
--      ORDER BY id DESC LIMIT 5; and confirm status_code = 200 for real,
--      not timed_out = true with a null status_code.
--   4. A real 503 in that same response body means Google OAuth isn't
--      fully configured on the live Cloud Run service -- check that
--      before assuming this route itself is broken.
--   5. A real `"already_running": true` in the response body is a real,
--      honest no-op (a previous real run was still in flight), not an
--      error -- see this file's own "REAL CONCURRENCY SAFETY" note above.

-- To remove the real, scheduled job later:
-- SELECT cron.unschedule('email-ingestion');
