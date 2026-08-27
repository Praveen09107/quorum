-- DEC-148: closes the real, disclosed gap `features/today.py`'s own
-- `TODAY_MONTHLY_BUDGET_LIMIT` comment already named ("no per-user
-- budget-configuration feature exists anywhere in this app yet") --
-- the real precondition for `UPDATE_BUDGET` to ever mean anything.
--
-- DEFAULT 50000.0 matches `TODAY_MONTHLY_BUDGET_LIMIT`'s own hardcoded
-- value exactly -- every existing real user starts at today's exact
-- current behavior, no observable change for anyone until a real
-- UPDATE_BUDGET execution (or a future settings screen) explicitly
-- changes it. NOT NULL with a DEFAULT is a metadata-only ALTER on
-- Postgres 11+ (the default is stored once, not backfilled row by
-- row), the same safe-migration shape this project already relies on.
ALTER TABLE users
    ADD COLUMN monthly_budget_limit DOUBLE PRECISION NOT NULL DEFAULT 50000.0;
