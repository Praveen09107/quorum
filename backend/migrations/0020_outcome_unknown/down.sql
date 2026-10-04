-- Reverses `0020_outcome_unknown/up.sql`. Any real row already carrying
-- `outcome_unknown` is defensively remapped to `uncertain_no_data`
-- first (the closest honest existing meaning: a real terminal state
-- where the real outcome genuinely could not be confirmed) so the
-- narrower CHECK constraint below can never fail against real,
-- already-existing data -- the same real failure mode this migration's
-- own `up.sql` docstring explains for `0019`. Wrapped in a transaction
-- for the same reason: CI's plain `psql -f` has no `--single-
-- transaction`, so an un-wrapped multi-statement file could commit the
-- DROP and then fail the ADD, leaving no constraint at all.
BEGIN;
UPDATE action_events SET outcome = 'uncertain_no_data' WHERE outcome = 'outcome_unknown';
ALTER TABLE action_events DROP CONSTRAINT action_events_outcome_check;
ALTER TABLE action_events
    ADD CONSTRAINT action_events_outcome_check
    CHECK (outcome = ANY (ARRAY['approved_unchanged', 'corrected_by_user', 'caught_by_gate', 'uncertain_no_data', 'rejected_by_user']));
COMMIT;
