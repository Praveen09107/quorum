-- Real, ready-to-run SQL for scheduling `POST /internal/deadline-watch`
-- (Phase 2, `DEC-132`) via pg_cron/pg_net.
--
-- **REAL, LIVE, CONFIRMED AS OF THIS SESSION (`DEC-134`):** now
-- genuinely scheduled and running unattended -- see `enable_retry_queue_
-- drain_cron.sql`'s own top-of-file comment for the full real account
-- of the extension-enablement correction and the real `timeout_
-- milliseconds` collision bug this session found and fixed, which
-- applies to this job too (`timeout_milliseconds := 30000` below).

-- Step 1: enable both extensions (safe to repeat).
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
        body := '{}'::jsonb,
        timeout_milliseconds := 30000
    );
    $$
);

-- Verification, once run for real:
--   1. SELECT * FROM cron.job WHERE jobname = 'deadline-watch';
--      -- expect exactly one real row, schedule = '*/30 * * * *'.
--   2. SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 5;
--      -- expect real rows appearing every ~30 minutes, status = 'succeeded'.
--   3. THE REAL CHECK THIS SESSION'S OWN BUG TAUGHT: 'succeeded' in
--      job_run_details is NOT sufficient on its own -- also check
--      SELECT id, status_code, timed_out, error_msg FROM net._http_response
--      ORDER BY id DESC LIMIT 5; and confirm status_code = 200 for real,
--      not timed_out = true with a null status_code (see enable_retry_
--      queue_drain_cron.sql's own top-of-file comment for the full real
--      account of why this matters).
--   4. The real, whole-system proof: seed a real, genuine conflict (a
--      real task due tomorrow needing more hours than available, a real
--      month-to-date spend past half the monthly budget) against a real
--      account, wait one real ~30-minute interval, then confirm a real
--      `negotiations` row now exists for that account WITHOUT anyone
--      having called the route or run a script by hand -- the real,
--      final proof this project's own whole-system checkpoint discipline
--      (`.claude/CLAUDE.md`) requires before calling Phase 2 done.

-- To remove the real, scheduled job later:
-- SELECT cron.unschedule('deadline-watch');
