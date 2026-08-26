-- Real, encrypted-at-rest storage for a user's Google `access_token`/
-- `refresh_token` -- closes the real, disclosed gap `auth/google_oauth.
-- py`'s own top-of-file docstring has named since it was first written:
-- Google's own tokens were deliberately never persisted, which blocked
-- any later, independent Gmail/Calendar API call (Phase 3,
-- `QUORUM_PRODUCTION_COMPLETION_PLAN.md`).
--
-- One real row per real Quorum user (`user_id` is both PK and FK) --
-- this project ties exactly one real Google account to one real Quorum
-- account, confirmed against how `/auth/token` itself works (one real
-- `id_token.sub` per sign-in, upserted onto one real `users` row).
--
-- `ON DELETE CASCADE`: this row is genuinely part of a user's own real
-- account, the same real ownership `security/supabase_deletion_store.
-- py`'s own docstring already establishes for `tasks`/`expenses`/etc.
-- A REAL, DISCLOSED SEQUENCING REQUIREMENT this cascade creates, closed
-- in the same real session: `revoke_oauth_tokens()` must run and
-- genuinely call Google's real `/revoke` endpoint BEFORE `purge_
-- postgres_rows()` deletes the real `users` row -- once that row is
-- gone, this cascade silently deletes this table's own row too, and
-- there would be nothing left to send to Google. `security/
-- account_deletion.py::delete_account()` reordered accordingly.
--
-- Encrypted at the APPLICATION level (Python `cryptography.fernet`,
-- keyed off a real, new `GOOGLE_TOKEN_ENCRYPTION_KEY` secret in
-- `core/config.py`), deliberately NOT via Postgres `pgcrypto`'s own
-- `pgp_sym_encrypt`/`pgp_sym_decrypt` SQL functions -- pgcrypto would
-- require passing the raw real encryption key into every query as a
-- bind parameter, a real, avoidable risk of that key ending up in a
-- real query log or `pg_stat_statements` entry. Only ciphertext ever
-- reaches Postgres.
CREATE TABLE google_oauth_tokens (
    user_id                  UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    encrypted_access_token   TEXT NOT NULL,
    encrypted_refresh_token  TEXT NOT NULL,
    access_token_expires_at  TIMESTAMPTZ NOT NULL,
    -- Google's own real, authoritative, space-separated scope string
    -- from the token response -- a user can decline part of what was
    -- requested, so this is what was actually granted, never assumed
    -- to equal what the consent screen asked for.
    granted_scopes           TEXT NOT NULL,
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);
