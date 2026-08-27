-- Real, live persistence for the Gate's own Stage A findings and
-- Stage B objections, closing the real, disclosed gap DEC-126 found:
-- `gate.review()`'s own real `GateVerdict.findings`/`.objections` have
-- always been computed, but never persisted anywhere -- used only to
-- decide the verdict, then discarded. Both are nullable: every real
-- `action_events` row inserted before this migration has neither, and
-- an S0/S1 verdict (Stage B never ran) genuinely has real findings but
-- an honestly empty real objections list, not a NULL one -- the
-- application layer, not this schema, is responsible for writing a
-- real `[]` rather than leaving the column NULL in that case.
ALTER TABLE action_events
    ADD COLUMN findings JSONB,
    ADD COLUMN objections JSONB;
