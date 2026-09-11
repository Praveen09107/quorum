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
-- references elsewhere).
--
-- REAL, DISCLOSED CORRECTION, found by this session's own standard-
-- tier review before merge: an earlier version of this comment
-- claimed `1:30` was chosen to avoid colliding with another real job's
-- own mark, per `DEC-134`'s own "never collide" discipline. That's
-- inaccurate -- `deadline-watch`/`spend-alert` already run `*/30 * * *
-- *`, so they ALREADY fire at every real `:30` mark, `1:30` included;
-- `briefing` lands squarely on that existing three-way mark, not
-- beside it. Left this way deliberately, not fixed by re-picking a
-- time: `DEC-134`'s own fix for that exact collision class
-- (`timeout_milliseconds := 30000` on all three jobs, confirmed live
-- via a direct concurrency stress test) already handles this, and a
-- once-a-day fourth arrival at an already-handled mark adds no new
-- real risk Cloud Run's own `--max-instances=2` autoscaling doesn't
-- already absorb.
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
