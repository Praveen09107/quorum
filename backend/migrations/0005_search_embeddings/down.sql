-- Honest limitation, confirmed live rather than assumed: this reversal
-- is genuinely usable only while note_embeddings holds no rows whose
-- vectors are 768-dimensional. With real rows present, the final
-- ALTER fails LOUD ("expected 1024 dimensions, not 768") rather than
-- silently truncating -- which is the correct failure mode, but does
-- mean this down migration is a development-time convenience, not a
-- real production rollback path once embeddings exist. Reverting for
-- real after that point means accepting the loss of every stored
-- vector (they would all need regenerating from `content` anyway,
-- since 1024 was never a real dimension any model here produced).

DROP INDEX IF EXISTS idx_note_embeddings_vector;
DROP INDEX IF EXISTS idx_note_embeddings_source;
DROP INDEX IF EXISTS idx_note_embeddings_user_id;
ALTER TABLE note_embeddings DROP COLUMN IF EXISTS source_id;
ALTER TABLE note_embeddings DROP COLUMN IF EXISTS source_type;
ALTER TABLE note_embeddings ALTER COLUMN embedding TYPE VECTOR(1024);
