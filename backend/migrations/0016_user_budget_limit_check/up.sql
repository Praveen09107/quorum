-- DEC-148 review (MEDIUM M3): `0015`'s new column had no database-level
-- constraint at all -- the app-layer check in `action_executor.py` was
-- its only defense, and that check alone was found incomplete (BLOCKER
-- B1, since fixed). `tasks.status`'s real, closed-set CHECK is this
-- project's own established precedent (CLAUDE.md: "a database CHECK
-- constraint... parse it fail-loud") for exactly this kind of
-- structural, not-just-app-layer defense.
--
-- Live-verified before writing this, not assumed: Postgres genuinely
-- sorts `NaN` as greater than every other `double precision` value,
-- INCLUDING `Infinity` itself (`SELECT 'NaN'::double precision <
-- 'Infinity'::double precision` returns `false`, confirmed live against
-- the real Supabase database). A bare `> 0` check alone would let `NaN`
-- through (`NaN > 0` is real, live `true`) -- the compound form below
-- is what actually rejects it, along with `0`, every negative value,
-- and both `Infinity`/`-Infinity`.
ALTER TABLE users
    ADD CONSTRAINT users_monthly_budget_limit_finite_positive
    CHECK (monthly_budget_limit > 0 AND monthly_budget_limit < 'Infinity'::double precision);
