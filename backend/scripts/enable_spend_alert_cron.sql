-- Real, ready-to-run SQL for scheduling `POST /internal/spend-alert`
-- (Phase 2, `DEC-13x`) via pg_cron/pg_net -- NOT YET RUN OR VERIFIED
-- LIVE. Same real, disclosed gap `enable_retry_queue_drain_cron.sql`/
-- `enable_deadline_watch_cron.sql` already established: neither
-- `pg_cron` nor `pg_net` was confirmed enabled on the real, live
-- Supabase project as of this session.

CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pg_net;

-- Same real 30-minute cadence as deadline-watch -- this route also
-- scans every real user's real, slow-moving data (recurring
-- subscriptions, monthly spend), not urgent, already-enqueued work.
-- Replace both placeholders before running (see enable_deadline_watch_
-- cron.sql's own comments for what each one is -- not repeated here).
SELECT cron.schedule(
    'spend-alert',
    '*/30 * * * *',
    $$
    SELECT net.http_post(
        url := '<CLOUD_RUN_URL>/internal/spend-alert',
        headers := jsonb_build_object('X-Internal-Secret', '<INTERNAL_DRAIN_SECRET>'),
        body := '{}'::jsonb
    );
    $$
);

-- Verification, once run for real:
--   1. SELECT * FROM cron.job WHERE jobname = 'spend-alert';
--   2. SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 5;

-- To remove the real, scheduled job later:
-- SELECT cron.unschedule('spend-alert');
