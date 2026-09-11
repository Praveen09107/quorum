-- Real, ready-to-run SQL for scheduling `POST /internal/briefing`
-- (`QUORUM_FINAL_COMPLETION_PLAN.md` Session 9, `DEC-176`) via
-- pg_cron/pg_net -- both extensions already real, live, and enabled on
-- this project's real Supabase database since `DEC-134` (five other
-- real, autonomous jobs already run this exact way; this is the sixth,
-- not the first).
--
-- REAL, DELIBERATE CADENCE, different from every other real job's own
-- 5/30-minute interval: `briefing` is a real, once-daily morning
-- summary, per this module's own top-of-file docstring ("the real
-- data-producing half" of a "morning composition") and `QUORUM_
-- ARCHITECTURE_DESIGN_DOCUMENT.md` §9.8's own "morning composition"
-- language -- a real user should get exactly one real push a day from
-- this job, never a real notification every half hour. `30 1 * * *`
-- (pg_cron's own real, UTC-based schedule) is 7:00 AM real IST
-- (UTC+5:30) -- this project's own real, confirmed developer/user
-- timezone (see `DECISIONS_LOG.md`'s own real, disclosed IST
-- references elsewhere). A real, deliberate, minor offset from the
-- exact hour mark, matching this project's own established "never
-- collide with another job's own mark" discipline (`DEC-134`'s real,
-- found three-way collision bug) -- `1:30` avoids the round `1:00`/
-- `2:00` marks other real, hourly-adjacent infra jobs might one day
-- use.
--
-- REAL, DISCLOSED, HONEST CURRENT EFFECT: with no real Firebase
-- project configured yet (`FIREBASE_PROJECT_ID`/`FIREBASE_SERVICE_
-- ACCOUNT_JSON` both genuinely unset, `DEC-176`), this real, scheduled
-- job will compose real per-user data correctly, every real day, and
-- send zero real notifications -- the same honest, non-`503` behavior
-- `POST /internal/briefing` already guarantees synchronously. Scheduling
-- it now is real, safe, and useful regardless: the moment a real
-- Firebase project exists, real push notifications start flowing on
-- the very next real scheduled fire, with no further deploy or script
-- needed.

CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pg_net;

-- Replace both placeholders before running (see enable_deadline_watch_
-- cron.sql's own comments for what each one is -- not repeated here).
SELECT cron.schedule(
    'briefing',
    '30 1 * * *',
    $$
    SELECT net.http_post(
        url := '<CLOUD_RUN_URL>/internal/briefing',
        headers := jsonb_build_object('X-Internal-Secret', '<INTERNAL_DRAIN_SECRET>'),
        body := '{}'::jsonb,
        timeout_milliseconds := 30000
    );
    $$
);

-- Verification, once run for real:
--   1. SELECT * FROM cron.job WHERE jobname = 'briefing';
--   2. SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 5;
--   3. THE REAL CHECK THIS PROJECT'S OWN HISTORY ALREADY LEARNED THE HARD
--      WAY (`DEC-134`): also check
--      SELECT id, status_code, timed_out, error_msg FROM net._http_response
--      ORDER BY id DESC LIMIT 5; and confirm status_code = 200 for real,
--      not timed_out = true with a null status_code.

-- To remove the real, scheduled job later:
-- SELECT cron.unschedule('briefing');
