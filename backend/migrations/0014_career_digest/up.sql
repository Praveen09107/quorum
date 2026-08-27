-- DEC-147: real Company Research Digest persistence (features/career_digest.py).
-- `digest` is nullable -- no backfill, no default, metadata-only ALTER,
-- same safe-migration shape as 0013's findings/objections columns.
-- `digest_attempts`/`digest_last_attempted_at` mirror negotiations'
-- `detail_backfill_attempts`/`detail_backfill_last_attempted_at`
-- (migration 0009) exactly -- the same real, CRITICAL-tier-review-
-- learned lesson (DEC-135): a durably-failing or already-tried
-- candidate must never occupy every batch of a real, bounded,
-- autonomous job forever.
ALTER TABLE applications
    ADD COLUMN digest JSONB,
    ADD COLUMN digest_attempts INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN digest_last_attempted_at TIMESTAMPTZ;
