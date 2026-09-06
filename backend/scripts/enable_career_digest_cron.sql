-- Real, ready-to-run SQL for scheduling `POST /internal/career-digest`
-- (Phase 6, `DEC-147`) via pg_cron/pg_net.
--
-- NOT YET SCHEDULED LIVE as of this file's own first commit -- at that
-- time, this job spent real Gemini calls (`make_gemini_compile_digest_
-- call`) against the SAME real, disclosed, fluctuating free-tier quota
-- `/internal/backfill-negotiation-detail` already, actively drew on
-- (confirmed directly against the real, live `cron.job` table, not
-- assumed -- see the real, disclosed correction that sat atop
-- `enable_backfill_negotiation_detail_cron.sql`, `DEC-147`), so
-- scheduling THIS one too meant two real, autonomous consumers on one
-- real, shared, fluctuating quota, not one competing against an
-- already-idle slot.
--
-- **REAL, DISCLOSED RESOLUTION, `DEC-166`:** `QUORUM_FINAL_COMPLETION_
-- PLAN.md` Session 1's real AI-provider rebalancing moved BOTH this
-- job's own real summarization call (`make_groq_compile_digest_call`)
-- AND `/internal/backfill-negotiation-detail`'s own real position/
-- synthesis calls off Gemini onto Groq -- the original real quota-
-- conflict this comment describes no longer applies, since neither job
-- draws on Gemini's real 20-request/day free-tier budget any more.
-- Still not scheduled live as of `DEC-166` -- resolving the original
-- blocker is not the same as a new, deliberate decision to enable it,
-- which stays Preethish's own call to make.
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
--      GROQ_API_KEY isn't configured on the live Cloud Run service --
--      check that before assuming this route itself is broken.

-- To remove the real, scheduled job later:
-- SELECT cron.unschedule('career-digest');
