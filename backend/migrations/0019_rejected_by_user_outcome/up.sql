-- Real, live redesign work: the new `POST /actions/{proposal_id}/approve`
-- and `POST /actions/{proposal_id}/reject` routes (`features/
-- action_approval.py`) close a real, previously-undiscovered gap -- no
-- backend route anywhere has ever let a real, signed-in user actually
-- approve or reject a pending action_events row. A real human REJECTING
-- a Gate-approved action is a genuinely different fact from the Gate's
-- own `caught_by_gate` (the Gate caught nothing here -- a human
-- overrode its approval), and `trust_digest.py`'s own real success-rate
-- count would be corrupted by conflating the two. The real, live
-- constraint name confirmed directly against the deployed database
-- before writing this (`action_events_outcome_check`), not guessed.
--
-- REAL, DISCLOSED FIX (CRITICAL-tier cross-model review, LOW finding):
-- wrapped in an explicit transaction. CI applies each migration file
-- via a plain `psql -f` with no `--single-transaction` (confirmed
-- directly against `.github/workflows/ci.yml`), so an un-wrapped
-- multi-statement file risks the DROP committing before a later ADD
-- fails, leaving the real table with no CHECK constraint at all.
BEGIN;
ALTER TABLE action_events DROP CONSTRAINT action_events_outcome_check;
ALTER TABLE action_events
    ADD CONSTRAINT action_events_outcome_check
    CHECK (outcome = ANY (ARRAY['approved_unchanged', 'corrected_by_user', 'caught_by_gate', 'uncertain_no_data', 'rejected_by_user']));
COMMIT;
