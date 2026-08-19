-- Real user-provisioning table -- the gap found live while scoping
-- DELETE /account (DEC-110): every real per-user domain table (tasks,
-- expenses, applications, note_embeddings) has a real UUID user_id
-- column, but nothing in this backend has ever mapped a real Google
-- `sub` onto one of these UUIDs. Without this table, no per-user query
-- anywhere in this backend can ever be correctly scoped -- confirmed
-- as the real, root cause of the disclosed per-user-scoping limitation
-- already carried by /trust_digest, /tasks, /career_pipeline, and
-- /finance/subscriptions.
--
-- Deliberately separate from the auth system's own identity concept:
-- the JWT/refresh-token layer continues using Google's raw `sub`
-- string unchanged (refresh_tokens.user_id is TEXT, confirmed against
-- the real 0002 migration -- no auth-internals change, no token
-- migration needed). This table is purely the real bridge a caller
-- looks up when it needs the internal UUID a domain table's own
-- user_id column expects.
CREATE TABLE users (
    user_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    google_sub  TEXT NOT NULL UNIQUE,
    email       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- No separate index on google_sub -- the UNIQUE constraint above
-- already creates one automatically; a second, explicit index on the
-- same column would be real, pure redundancy.
