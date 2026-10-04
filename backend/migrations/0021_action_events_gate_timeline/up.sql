-- `DEC-189` Block B. Three real columns on `action_events`, all three
-- closing a real "the backend genuinely computes this and then throws it
-- away" gap found by a full audit of this project's own data surface.
--
-- 1. `gate_timeline` -- the real, measured execution timeline of the Gate
--    review that produced this row: every Stage A validator with its own
--    name, three-valued result, confidence and real duration; the Critic
--    and Judge with their real durations and attempt counts; and the real
--    routing summary. Produced by `gate/timeline.py`, which observes the
--    real callables `gate.review()` is handed rather than modifying
--    `review()` itself (that function is CRITICAL-tier and its safety
--    argument is structural -- see that module's own docstring).
--
--    Why this column exists at all: confirmed by direct search before
--    writing it, this backend has never had ANY timing instrumentation --
--    no `perf_counter`, no stage duration, and no Langfuse call site
--    despite Langfuse being configured in `.env`. The Gate has always
--    been a black box that returns an answer, which is a direct, concrete
--    cause of the real product complaint that drove this rebuild: the app
--    renders state and never process.
--
-- 2. `revision_count` -- already a real, computed field on `GateVerdict`
--    (`orchestration.py` sets it to 0 or 1 on every single return path)
--    and never persisted anywhere. It is the cleanest "the Gate corrected
--    itself" signal this system has, and it was being discarded at write
--    time.
--
-- 3. `pre_revision_payload` -- the payload as the Judge received it, kept
--    ONLY when the Judge genuinely revised it. `review()` builds the
--    revised proposal and nothing retains what came before, so "here is
--    what the AI wanted to send, and here is what the Gate made it
--    change" -- the single most compelling artifact this system can
--    produce, and its thesis demonstrated on real data rather than
--    described -- has never been showable.
--
-- ALL THREE ARE NULLABLE, DELIBERATELY, and this is the load-bearing
-- safety property of this migration rather than a convenience: every
-- `action_events` row already in this real, live table predates these
-- columns, and every one of them will read NULL. NULL here means
-- "genuinely not recorded," never "zero" and never "no revision" -- a
-- consumer must render an honest absence for an older row, not a
-- fabricated empty timeline that would imply the Gate ran no checks.
-- `revision_count` specifically is NOT given a `DEFAULT 0`, for exactly
-- this reason: a default would backfill every historical row with a
-- confident, unverified 0 that is indistinguishable from a real measured
-- 0, destroying the only signal that says which rows this data actually
-- exists for.
--
-- Wrapped in an explicit transaction, following migration `0019`'s own
-- CRITICAL-tier review finding: CI applies each file via a plain
-- `psql -f` with no `--single-transaction`, so an un-wrapped
-- multi-statement file can commit partially.
BEGIN;

ALTER TABLE action_events ADD COLUMN gate_timeline JSONB;
ALTER TABLE action_events ADD COLUMN revision_count INTEGER;
ALTER TABLE action_events ADD COLUMN pre_revision_payload JSONB;

-- A real, narrow sanity bound rather than a bare integer. `review()`
-- is structurally incapable of more than one revision round -- there is
-- no loop in it, which is that function's own stated correctness
-- argument -- so any value above 1 would mean that invariant had been
-- broken somewhere upstream. Constraining it here makes the database
-- refuse to record a value that would contradict the Gate's own design,
-- rather than quietly storing evidence of a bug as if it were fine.
ALTER TABLE action_events
    ADD CONSTRAINT action_events_revision_count_check
    CHECK (revision_count IS NULL OR (revision_count >= 0 AND revision_count <= 1));

COMMIT;
