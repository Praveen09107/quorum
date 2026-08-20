DROP INDEX IF EXISTS idx_note_embeddings_source;
DROP INDEX IF EXISTS idx_note_embeddings_user_id;
ALTER TABLE note_embeddings DROP COLUMN IF EXISTS source_id;
ALTER TABLE note_embeddings DROP COLUMN IF EXISTS source_type;
ALTER TABLE note_embeddings ALTER COLUMN embedding TYPE VECTOR(1024);
