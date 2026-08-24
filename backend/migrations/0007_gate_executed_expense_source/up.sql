-- Real gap, found while building the execution layer for real,
-- Gate-approved downstream actions (DEC-128): expenses.source's real
-- CHECK constraint (migration 0001) is a closed 3-value vocabulary --
-- 'on_device', 'manual', 'extracted' -- confirmed live against the
-- real, deployed constraint (expenses_source_check) before writing
-- this migration. None of the 3 honestly describes a real expense row
-- this backend is about to start creating for the first time: one
-- written because the Gate reviewed and approved an automated
-- ActionProposal (features/retry_queue_drainer.py's own real
-- LOG_EXPENSE execution), not typed in by a person, not captured
-- on-device, and not extracted from a document/email. Picking the
-- closest existing value ('extracted') and silently hoping it's close
-- enough would be exactly the kind of "spec/schema doesn't match
-- reality, adapt silently" move CLAUDE.md Rule 4 rules out -- a real,
-- disclosed, minimal extension instead, the same precedent DEC-120's
-- own SearchItemType.application addition already established for
-- this project.
ALTER TABLE expenses DROP CONSTRAINT expenses_source_check;
ALTER TABLE expenses ADD CONSTRAINT expenses_source_check
    CHECK (source IN ('on_device', 'manual', 'extracted', 'gate_approved'));
