-- Real, ready-to-run SQL for scheduling `POST /internal/backfill-
-- negotiation-detail` (Phase 2, `DEC-135`) via pg_cron/pg_net.
--
-- NOT YET SCHEDULED LIVE as of this file's own first commit -- real
-- Gemini free-tier quota is currently exhausted from this PR's own
-- CRITICAL-tier review (`STATUS_INDEX.md` item #21's own disclosed,
-- fluctuating quota, live-proven again here), so enabling this now
-- would only retry-and-fail until quota resets; a real, deliberate
-- decision to write this script correctly now and enable it once
-- quota resets and/or Preethish confirms, rather than either skip
-- writing it or enable it blind.
--
-- **A REAL, DISCLOSED CORRECTION TO THIS SESSION'S OWN ORIGINAL PLAN:**
-- the `DEC-135` log entry originally said this script would reuse
-- `DEC-134`'s exact `*/30`+`timeout_milliseconds := 30000` pattern.
-- This PR's own CRITICAL-tier review found that would have been wrong:
-- a real, measured Gemini round trip for ONE negotiation took ~28
-- seconds, so scheduling this at the same `:00`/`:30` marks as
-- `deadline-watch`/`spend-alert`/`drain-retry-queue` would reproduce
-- `DEC-134`'s own timeout-collision bug in a new, worse form (a ~28s
-- real request occupying one of only two real Cloud Run instances,
-- `--concurrency=1`, while the other three jobs queue behind it) --
-- and a 30-second timeout leaves almost no real margin over a 28-
-- second measured call. Fixed here, before ever running live:
--   1. Scheduled at `:12`/`:42` past the hour -- neither is a multiple
--      of 5, so this job NEVER coincides with drain-retry-queue's own
--      `*/5` marks, and never with deadline-watch/spend-alert's `:00`/
--      `:30` marks either.
--   2. `timeout_milliseconds := 60000` -- double the real, measured
--      worst case, real margin for a real cold start.
--   3. `features/negotiation_detail_backfill.py::DEFAULT_BATCH_SIZE`
--      is `1` (reduced from an original `3` by the same review finding)
--      -- one real negotiation, one real ~28s call, per real
--      invocation, not three run sequentially.

CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pg_net;

-- Replace both placeholders before running (see enable_deadline_watch_
-- cron.sql's own comments for what each one is -- not repeated here).
SELECT cron.schedule(
    'backfill-negotiation-detail',
    '12,42 * * * *',
    $$
    SELECT net.http_post(
        url := '<CLOUD_RUN_URL>/internal/backfill-negotiation-detail',
        headers := jsonb_build_object('X-Internal-Secret', '<INTERNAL_DRAIN_SECRET>'),
        body := '{}'::jsonb,
        timeout_milliseconds := 60000
    );
    $$
);

-- Verification, once run for real:
--   1. SELECT * FROM cron.job WHERE jobname = 'backfill-negotiation-detail';
--   2. SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 5;
--   3. THE REAL CHECK `DEC-134`'s own session taught: 'succeeded' in
--      job_run_details is NOT sufficient on its own -- also check
--      SELECT id, status_code, timed_out, error_msg FROM net._http_response
--      ORDER BY id DESC LIMIT 5; and confirm status_code = 200 for real,
--      not timed_out = true with a null status_code.
--   4. A real 503 in that same response body means GEMINI_API_KEY isn't
--      configured on the live Cloud Run service -- check that before
--      assuming this route itself is broken.

-- To remove the real, scheduled job later:
-- SELECT cron.unschedule('backfill-negotiation-detail');
