-- Real, ready-to-run SQL for scheduling `POST /internal/spend-alert`
-- (Phase 2, `DEC-133`) via pg_cron/pg_net.
--
-- **REAL, LIVE, CONFIRMED AS OF THIS SESSION (`DEC-134`):** now
-- genuinely scheduled and running unattended -- see `enable_retry_queue_
-- drain_cron.sql`'s own top-of-file comment for the full real account
-- of the extension-enablement correction and the real `timeout_
-- milliseconds` collision bug this session found and fixed, which
-- applies to this job too (`timeout_milliseconds := 30000` below).

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
        body := '{}'::jsonb,
        timeout_milliseconds := 30000
    );
    $$
);

-- Verification, once run for real:
--   1. SELECT * FROM cron.job WHERE jobname = 'spend-alert';
--   2. SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 5;
--   3. THE REAL CHECK THIS SESSION'S OWN BUG TAUGHT: also check
--      SELECT id, status_code, timed_out, error_msg FROM net._http_response
--      ORDER BY id DESC LIMIT 5; and confirm status_code = 200 for real,
--      not timed_out = true with a null status_code (see enable_retry_
--      queue_drain_cron.sql's own top-of-file comment for why).

-- To remove the real, scheduled job later:
-- SELECT cron.unschedule('spend-alert');
