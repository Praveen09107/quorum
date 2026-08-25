-- Real, ready-to-run SQL for scheduling `POST /internal/deadline-watch`
-- (Phase 2, `DEC-13x`) via pg_cron/pg_net -- NOT YET RUN OR VERIFIED LIVE.
--
-- HONEST DISCLOSURE, same real gap `enable_retry_queue_drain_cron.sql`
-- (`DEC-127`) already disclosed and this script has not independently
-- re-verified since: neither `pg_cron` nor `pg_net` was confirmed enabled
-- on the real, live Supabase project as of that session. Enabling them
-- needs Preethish's own real, manual action in the Supabase dashboard's
-- Database -> Extensions panel; no CLI or service-role SQL connection
-- this environment has can flip that toggle. This script is real and
-- correct SQL, ready to run once the extensions are enabled (and once
-- `enable_retry_queue_drain_cron.sql` -- or this script -- has already
-- run `CREATE EXTENSION IF NOT EXISTS` for both), but genuinely
-- UNVERIFIED live -- run it, then verify with the two checks at the
-- bottom, don't assume it works from reading it alone.

-- Step 1: enable both extensions (safe to repeat even if
-- enable_retry_queue_drain_cron.sql already ran this).
CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pg_net;

-- Step 2: schedule a real, live call to the real, deployed backend's own
-- /internal/deadline-watch every 30 minutes -- deliberately less
-- frequent than drain-retry-queue's 5-minute cadence: this route scans
-- every real user's real, slow-moving data (task deadlines, monthly
-- spend), not urgent, already-enqueued work, so a real, live conflict
-- genuinely doesn't need 5-minute-scale detection latency. Replace both
-- placeholders before running:
--   <CLOUD_RUN_URL>            -- the real, live Cloud Run URL, e.g.
--                                 https://quorum-backend-649581407643.asia-south1.run.app
--   <INTERNAL_DRAIN_SECRET>    -- the real value of INTERNAL_DRAIN_SECRET
--                                 from backend/.env on this machine --
--                                 the same real, shared secret every
--                                 /internal/* route uses, never commit
--                                 the real value into this or any other
--                                 tracked file.
SELECT cron.schedule(
    'deadline-watch',
    '*/30 * * * *',
    $$
    SELECT net.http_post(
        url := '<CLOUD_RUN_URL>/internal/deadline-watch',
        headers := jsonb_build_object('X-Internal-Secret', '<INTERNAL_DRAIN_SECRET>'),
        body := '{}'::jsonb
    );
    $$
);

-- Verification, once run for real:
--   1. SELECT * FROM cron.job WHERE jobname = 'deadline-watch';
--      -- expect exactly one real row, schedule = '*/30 * * * *'.
--   2. SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 5;
--      -- expect real rows appearing every ~30 minutes, status = 'succeeded'.
--      A real 401 status in net's own response body here means the
--      secret placeholder above wasn't actually replaced correctly --
--      check that before assuming the endpoint itself is broken.
--   3. The real, whole-system proof: seed a real, genuine conflict (a
--      real task due tomorrow needing more hours than available, a real
--      month-to-date spend past half the monthly budget) against a real
--      account, wait one real ~30-minute interval, then confirm a real
--      `negotiations` row now exists for that account WITHOUT anyone
--      having called the route or run a script by hand -- the real,
--      final proof this project's own whole-system checkpoint discipline
--      (`.claude/CLAUDE.md`) requires before calling Phase 2 done.

-- To remove the real, scheduled job later:
-- SELECT cron.unschedule('deadline-watch');
