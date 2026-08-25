-- Real, honest rollback -- a plain, nullable, free-text column carries
-- no real constraint to worry about violating on drop; safe to remove
-- unconditionally, unlike migration 0007's own down.sql (which guards
-- against a real, existing CHECK-constrained value).
ALTER TABLE negotiations DROP COLUMN trigger_source;
