-- Real schema for auth/refresh_token.py's `RevocationStore` -- the storage
-- layer that module's own docstring named as "a separate, later
-- integration concern" (IMPL_12), now genuinely needed: Batch 10 Phase 3
-- wires real /auth/token, /auth/refresh, /auth/revoke routes against the
-- real, live database for the first time.
--
-- Columns mirror `RefreshTokenRecord` exactly (auth/refresh_token.py):
-- token_hash, family_id, user_id, issued_at, expires_at, used, revoked.
-- Only the HASH of a token is ever stored, per that module's own real
-- security property -- never the raw token value.
CREATE TABLE refresh_tokens (
    token_hash  TEXT PRIMARY KEY,
    family_id   UUID NOT NULL,
    user_id     TEXT NOT NULL,
    issued_at   TIMESTAMPTZ NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    used        BOOLEAN NOT NULL DEFAULT false,
    revoked     BOOLEAN NOT NULL DEFAULT false
);

-- revoke_family() and rotate_refresh_token()'s own family-continuity
-- lookups are both by family_id.
CREATE INDEX idx_refresh_tokens_family_id ON refresh_tokens (family_id);

-- get_family_ids_for_user() / revoke_all_for_user()'s real "sign out
-- everywhere" lookup is by user_id.
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens (user_id);
