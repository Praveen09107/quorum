-- Reverses `0022_action_events_artifact`.
--
-- HONEST WARNING: genuinely destructive, same as `0021`'s own
-- down.sql -- dropping this column permanently discards every real
-- recorded artifact id. A real Gmail message/draft or Calendar event
-- it pointed at still exists on Google's own servers; only this
-- backend's own record of which real id to link to is lost, and
-- cannot be reconstructed from anything else this database retains.
BEGIN;

ALTER TABLE action_events DROP COLUMN IF EXISTS artifact;

COMMIT;
