-- Real, live schema addition -- closes HIGH-1/HIGH-2 in the CRITICAL-
-- tier review of PR #20 (DEC-135): without a real, per-negotiation
-- attempt record, `features/negotiation_detail_backfill.py`'s own
-- candidate query (`ORDER BY started_at LIMIT n`) permanently re-picks
-- the SAME oldest bare negotiations forever -- a real, live-proven
-- head-of-line block for a negotiation whose situation has since
-- resolved (zero Gemini cost per retry, but starves every other real
-- user's genuine conflict from ever being detailed), and unbounded real
-- Gemini quota burn for a negotiation that durably fails every attempt.
--
-- `detail_backfill_last_attempted_at` lets candidate selection order by
-- "least recently attempted" (round-robin) instead of `started_at`, so
-- no small, fixed set of rows can dominate every real batch forever.
-- `detail_backfill_attempts` lets candidate selection exclude a
-- negotiation once it has durably failed a real, bounded number of
-- times, capping real Gemini quota waste on a negotiation that will
-- never succeed rather than retrying it every cron tick indefinitely.

ALTER TABLE negotiations ADD COLUMN detail_backfill_attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE negotiations ADD COLUMN detail_backfill_last_attempted_at TIMESTAMPTZ NULL;
