-- REAL, DISCLOSED FIX from this session's own CRITICAL-tier cross-model
-- review of `features/action_approval.py` (HIGH-2): `action_executor.
-- execute_approved_action()`'s own real, three-valued `ExecutionResult.
-- executed` can come back `None` -- its own docstring says this means
-- GENUINELY UNKNOWN (a real Gmail/Calendar call timed out or the
-- connection dropped after the request was sent but before a response
-- came back), never "did not happen." The first version of
-- `approve_pending_action()` only ever resolved the row on a truthy
-- `executed`, so a real `None` left the row unresolved and still
-- `canApprove` -- a real user could tap Approve again and genuinely
-- double-send. This value is the honest, real, distinct terminal state
-- for that case: resolved (so it can never be retried blind), but
-- never conflated with a confirmed `approved_unchanged` success. Kept
-- genuinely distinct from `uncertain_no_data`, which is a real
-- `Finding.evidence_state` concept (a validator found no evidence
-- either way) -- a materially different real fact from "we don't know
-- if a real external send actually went through."
--
-- REAL, DISCLOSED FIX (the same review's LOW finding on migration
-- `0019`'s own `down.sql`): wrapped in an explicit transaction. CI
-- applies each migration file via a plain `psql -f` with no
-- `--single-transaction` (confirmed directly against `.github/
-- workflows/ci.yml`), so an un-wrapped multi-statement file risks the
-- DROP committing before a later ADD fails, leaving the real table
-- with no CHECK constraint at all. `BEGIN`/`COMMIT` makes this file
-- atomic regardless of the runner's own default.
BEGIN;
ALTER TABLE action_events DROP CONSTRAINT action_events_outcome_check;
ALTER TABLE action_events
    ADD CONSTRAINT action_events_outcome_check
    CHECK (outcome = ANY (ARRAY['approved_unchanged', 'corrected_by_user', 'caught_by_gate', 'uncertain_no_data', 'rejected_by_user', 'outcome_unknown']));
COMMIT;
