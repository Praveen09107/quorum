ALTER TABLE applications
    DROP COLUMN digest_last_attempted_at,
    DROP COLUMN digest_attempts,
    DROP COLUMN digest;
