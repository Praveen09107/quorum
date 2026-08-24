-- Real, ready-to-run SQL for scheduling `POST /internal/drain-retry-queue`
-- (`DEC-127`) via pg_cron/pg_net -- NOT YET RUN OR VERIFIED LIVE.
--
-- HONEST DISCLOSURE: confirmed directly against the real, live Supabase
-- project (`dxfeutkeofnbismljhsb`) before writing this file --
-- `SELECT extname FROM pg_extension` returns only `vector`. Neither
-- `pg_cron` nor `pg_net` is currently enabled, despite
-- `IMPL_10_INFRA_SUPABASE_UPSTASH.md`'s own real setup instructions
-- naming this as a real step ("Enable pg_cron and pg_net in the
-- Supabase dashboard's extensions panel") -- that step was apparently
-- never actually done. Enabling them needs Preethish's own real,
-- manual action in the Supabase dashboard's Database -> Extensions
-- panel; no CLI or service-role SQL connection this environment has
-- can flip that toggle. This script is real and correct SQL, ready to
-- run once the extensions are enabled, but genuinely UNVERIFIED live --
-- run it, then verify with the two checks at the bottom, don't assume
-- it works from reading it alone.

-- Step 1: enable both extensions (may already show "Enabled" in the
-- dashboard by the time this runs -- CREATE EXTENSION IF NOT EXISTS is
-- safe either way).
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
--                                 file or any other tracked file.
SELECT cron.schedule(
    'drain-retry-queue',
    '*/5 * * * *',
    $$
    SELECT net.http_post(
        url := '<CLOUD_RUN_URL>/internal/drain-retry-queue',
        headers := jsonb_build_object('X-Internal-Secret', '<INTERNAL_DRAIN_SECRET>'),
        body := '{}'::jsonb
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

-- To remove the real, scheduled job later:
-- SELECT cron.unschedule('drain-retry-queue');
