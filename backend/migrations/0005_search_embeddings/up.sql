-- Roadmap Phase 4a (Unified Fast Search, DEC-120). Three real gaps in
-- 0001's original note_embeddings schema, closed here:
--
-- 1. `embedding VECTOR(1024)` was always a placeholder, explicitly
--    marked "dimension pending confirmation, see STATUS_INDEX.md open
--    item 5" -- never confirmed until this session, and never matching
--    any real embedding call, since nothing has ever written to this
--    table (confirmed live: zero rows, before writing this migration).
--    Corrected to 768, the real dimension core/embeddings.py actually
--    requests. See point 3 below for why 768 and not the model's own
--    3072 default -- that distinction is load-bearing, not cosmetic.
--
-- 2. No column ever existed to map an embedding row back to the real
--    content it represents (a task, an expense, an application, or a
--    logged Gate decision) -- there was no consumer needing that
--    mapping until this session. `source_type`/`source_id` close it.
--    `email` is deliberately absent from the CHECK constraint: nothing
--    in this backend produces email content yet (no Gmail integration
--    exists), so it would be a real, unused fifth value with no real
--    producer -- a future session adding one extends this constraint
--    then, not guessed at here.
--
-- 3. No ANN index existed, and at this migration's OWN first-draft
--    dimension it could never have existed. A real, disclosed
--    correction found by DEC-120's pre-merge review, before any real
--    row was written: this file originally declared VECTOR(3072)
--    (gemini-embedding-001's real, live-confirmed DEFAULT output), and
--    pgvector refuses to build HNSW or IVFFlat above 2000 dimensions
--    -- confirmed live against this very database: "column cannot have
--    more than 2000 dimensions for hnsw index". A 3072 column would
--    have silently condemned every real search to a sequential scan of
--    the user's entire corpus, permanently, with no error to signal it
--    and no cheap way back once real rows existed. Gemini's real
--    Matryoshka (MRL) truncation via `outputDimensionality` returns a
--    genuine 768-dimension vector (confirmed live), which indexes
--    cleanly -- so the HNSW index below is real and actually used.
--
-- Safe as a direct ALTER, not a nullable-then-backfill two-step:
-- note_embeddings has zero real rows as of this migration (confirmed
-- live), and no code path anywhere in this backend has ever written to
-- it before this session (only a real DELETE, in
-- security/supabase_deletion_store.py's account-purge path).

ALTER TABLE note_embeddings ALTER COLUMN embedding TYPE VECTOR(768);

ALTER TABLE note_embeddings ADD COLUMN source_type TEXT NOT NULL
    CHECK (source_type IN ('task', 'expense', 'application', 'decision'));
ALTER TABLE note_embeddings ADD COLUMN source_id UUID NOT NULL;

CREATE INDEX idx_note_embeddings_user_id ON note_embeddings (user_id);

-- One embedding per real source row -- features/search.py's lazy
-- backfill (see its own docstring for why it's lazy, not on-write)
-- relies on this being a real, enforced correctness guarantee, not
-- just a performance optimization: re-running the backfill must never
-- create a duplicate or re-embed a row that's already covered.
CREATE UNIQUE INDEX idx_note_embeddings_source ON note_embeddings (user_id, source_type, source_id);

-- Real ANN index, genuinely usable only because of point 3 above.
-- `vector_cosine_ops` matches features/search.py's own `<=>` cosine
-- distance operator exactly -- an index built for a different operator
-- class would simply never be used by that query.
CREATE INDEX idx_note_embeddings_vector ON note_embeddings
    USING hnsw (embedding vector_cosine_ops);
