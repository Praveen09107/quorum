-- Reverses `0021_action_events_gate_timeline`.
--
-- HONEST WARNING, stated rather than left implicit: this is genuinely
-- destructive. Dropping these columns permanently discards every real
-- recorded Gate timeline, every real `revision_count`, and every real
-- pre-revision payload. None of that is reconstructible afterward --
-- the timeline is a measurement of a moment that has passed, and the
-- pre-revision payload is the only copy of a value `gate.review()`
-- itself discards. Unlike a dropped constraint, this cannot be undone
-- by re-applying the up migration.
--
-- Wrapped in an explicit transaction for the same reason as `up.sql`:
-- CI applies migration files with a plain `psql -f`, no
-- `--single-transaction`, so an un-wrapped multi-statement file can
-- commit partially and leave the table in a state matching neither
-- direction.
BEGIN;

ALTER TABLE action_events DROP CONSTRAINT IF EXISTS action_events_revision_count_check;
ALTER TABLE action_events DROP COLUMN IF EXISTS pre_revision_payload;
ALTER TABLE action_events DROP COLUMN IF EXISTS revision_count;
ALTER TABLE action_events DROP COLUMN IF EXISTS gate_timeline;

COMMIT;
