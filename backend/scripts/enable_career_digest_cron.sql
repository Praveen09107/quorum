-- Real, ready-to-run SQL for scheduling `POST /internal/career-digest`
-- (Phase 6, `DEC-147`) via pg_cron/pg_net.
--
-- NOT YET SCHEDULED LIVE as of this file's own first commit -- this
-- job spends real Gemini calls (`make_gemini_compile_digest_call`)
-- against the SAME real, disclosed, fluctuating free-tier quota
-- `/internal/backfill-negotiation-detail` already competes for
-- (`STATUS_INDEX.md` item #21), and that job's own `enable_backfill_
-- negotiation_detail_cron.sql` was, for the identical reason, left
-- deliberately unscheduled pending Preethish's own confirmation.
-- Written correctly now so enabling it later is a one-line `psql`/pool
-- command, not a new design decision made under time pressure.
--
-- Offset chosen to avoid every other real job's own schedule (`:00`/
-- `:30` -- deadline-watch/spend-alert; `*/5` -- drain-retry-queue;
-- `:12`/`:42` -- backfill-negotiation-detail; `:07`/`:22`/`:37`/`:52`
-- -- email-ingestion): `:17`/`:47`, matching nothing above.
--
-- `timeout_milliseconds := 60000` -- the same real margin `backfill-
-- negotiation-detail` uses for the same class of work (one real,
-- sequential Tavily-then-Gemini round trip, `DEFAULT_BATCH_SIZE = 1`).

CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pg_net;

-- Replace both placeholders before running (see enable_deadline_watch_
-- cron.sql's own comments for what each one is -- not repeated here).
SELECT cron.schedule(
    'career-digest',
    '17,47 * * * *',
    $$
    SELECT net.http_post(
        url := '<CLOUD_RUN_URL>/internal/career-digest',
        headers := jsonb_build_object('X-Internal-Secret', '<INTERNAL_DRAIN_SECRET>'),
        body := '{}'::jsonb,
        timeout_milliseconds := 60000
    );
    $$
);

-- Verification, once run for real:
--   1. SELECT * FROM cron.job WHERE jobname = 'career-digest';
--   2. SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 5;
--   3. SELECT id, status_code, timed_out, error_msg FROM net._http_response
--      ORDER BY id DESC LIMIT 5; and confirm status_code = 200 for real,
--      not timed_out = true with a null status_code.
--   4. A real 503 in that same response body means TAVILY_API_KEY or
--      GEMINI_API_KEY isn't configured on the live Cloud Run service --
--      check that before assuming this route itself is broken.

-- To remove the real, scheduled job later:
-- SELECT cron.unschedule('career-digest');
