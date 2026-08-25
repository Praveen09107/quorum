-- Real, ready-to-run SQL for scheduling `POST /internal/drain-retry-queue`
-- (`DEC-127`) via pg_cron/pg_net.
--
-- **REAL, LIVE, CONFIRMED AS OF THIS SESSION (`DEC-134`):** this job is
-- now genuinely scheduled and running unattended against the real,
-- deployed Supabase project (`dxfeutkeofnbismljhsb`) -- `SELECT * FROM
-- cron.job` shows all three real Phase 2 jobs `active = true`, and
-- `cron.job_run_details`/`net._http_response` show real, unattended
-- fires succeeding with genuine `200` responses. The earlier disclosure
-- here ("neither pg_cron nor pg_net is enabled, needs Preethish's own
-- dashboard action") was a real, corrected assumption: this session
-- found the connected service-role connection already has sufficient
-- privilege to `CREATE EXTENSION` both directly -- no dashboard toggle
-- was actually required. This script remains the real, re-runnable
-- source of truth for what's live (e.g. after a real `cron.unschedule`),
-- not a still-pending setup step.
--
-- **A REAL, LIVE BUG FOUND AND FIXED THE SAME SESSION THIS WAS FIRST
-- SCHEDULED:** all three Phase 2 cron jobs share `*/5` or `*/30` minute
-- marks, so every `:00`/`:30` real clock minute fires this job
-- simultaneously with `deadline-watch` and `spend-alert`. Cloud Run's
-- own `--concurrency=1` (deliberate, `.claude/CLAUDE.md`, never to be
-- raised) serializes those three real, simultaneous requests across at
-- most two real instances -- and `net.http_post`'s own DEFAULT
-- `timeout_milliseconds` is a hardcoded `5000`, live-proven too short:
-- the very first real, unattended 3-way collision (17:30:00 UTC) left
-- one of the three real HTTP calls `timed_out = true` in `net.
-- _http_response`, with `cron.job_run_details` still showing that job
-- as `'succeeded'` (pg_cron only confirms the async `net.http_post`
-- call was ACCEPTED, not that a real HTTP response ever came back) --
-- a systemic, permanent, silent-until-you-check gap, not a one-off,
-- since these three schedules collide every real half hour, forever.
-- Fixed here: `timeout_milliseconds := 30000` on every real call below,
-- live-verified by firing all three simultaneously by hand and
-- confirming all three now return real `200`s within the new window.
-- Cloud Run's own `--concurrency=1` was deliberately left untouched.

-- Step 1: enable both extensions (safe to repeat).
CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pg_net;

-- Step 2: schedule a real, live call to the real, deployed backend's
-- own /internal/drain-retry-queue every 5 minutes. Replace both
-- placeholders before running:
--   <CLOUD_RUN_URL>            -- the real, live Cloud Run URL, e.g.
--                                 https://quorum-backend-649581407643.asia-south1.run.app
--   <INTERNAL_DRAIN_SECRET>    -- the real value of INTERNAL_DRAIN_SECRET
--                                 from backend/.env on this machine --
--                                 never commit the real value into this
--                                 or any other tracked file.
SELECT cron.schedule(
    'drain-retry-queue',
    '*/5 * * * *',
    $$
    SELECT net.http_post(
        url := '<CLOUD_RUN_URL>/internal/drain-retry-queue',
        headers := jsonb_build_object('X-Internal-Secret', '<INTERNAL_DRAIN_SECRET>'),
        body := '{}'::jsonb,
        timeout_milliseconds := 30000
    );
    $$
);

-- Verification, once run for real:
--   1. SELECT * FROM cron.job WHERE jobname = 'drain-retry-queue';
--      -- expect exactly one real row, schedule = '*/5 * * * *'.
--   2. SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 5;
--      -- expect real rows appearing every ~5 minutes, status = 'succeeded'.
--      A real 401 status in net's own response body here means the
--      secret placeholder above wasn't actually replaced correctly --
--      check that before assuming the endpoint itself is broken.
--   3. THE REAL CHECK THIS SESSION'S OWN BUG TAUGHT: 'succeeded' in
--      job_run_details is NOT sufficient -- also check
--      SELECT id, status_code, timed_out, error_msg FROM net._http_response
--      ORDER BY id DESC LIMIT 5; and confirm status_code = 200 for real,
--      not timed_out = true with a null status_code.

-- To remove the real, scheduled job later:
-- SELECT cron.unschedule('drain-retry-queue');
