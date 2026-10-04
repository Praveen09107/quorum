-- Reverses `0019_rejected_by_user_outcome/up.sql`.
--
-- REAL, DISCLOSED FIX (CRITICAL-tier cross-model review, LOW finding):
-- the original version of this file dropped the wider constraint and
-- re-added the narrower one with no transaction wrapper and no regard
-- for real, already-existing `rejected_by_user` rows -- CI's plain
-- `psql -f` runner (confirmed against `.github/workflows/ci.yml`) has
-- no `--single-transaction`, so the DROP could commit and the ADD then
-- fail against real existing data, leaving the table with no outcome
-- CHECK constraint at all. Any such row is now defensively remapped to
-- `caught_by_gate` first -- not a perfect semantic match, but the
-- closest existing honest meaning for "a human did not let this
-- execute," and this path only runs on a deliberate rollback, never in
-- normal operation.
BEGIN;
UPDATE action_events SET outcome = 'caught_by_gate' WHERE outcome = 'rejected_by_user';
ALTER TABLE action_events DROP CONSTRAINT action_events_outcome_check;
ALTER TABLE action_events
    ADD CONSTRAINT action_events_outcome_check
    CHECK (outcome = ANY (ARRAY['approved_unchanged', 'corrected_by_user', 'caught_by_gate', 'uncertain_no_data']));
COMMIT;
