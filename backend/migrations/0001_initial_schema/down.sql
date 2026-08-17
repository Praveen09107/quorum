-- Real rollback for 0001_initial_schema/up.sql. Genuinely new -- per
-- specs/tier1_foundation/QUORUM_PROJECT_STRUCTURE.md's own note, no
-- rollback path existed anywhere before this restructure; no literal spec
-- to copy, so this is a real, careful construction, dropping tables in
-- reverse dependency order (interviews before applications, since
-- interviews.application_id references applications).

DROP TABLE IF EXISTS retry_queue;
DROP TABLE IF EXISTS interviews;
DROP TABLE IF EXISTS note_embeddings;
DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS expenses;
DROP TABLE IF EXISTS tasks;
DROP TABLE IF EXISTS action_events;
