-- DEC-176 (`QUORUM_FINAL_COMPLETION_PLAN.md` Session 9): real, live
-- storage for each real user's CURRENT FCM device token -- one row per
-- real user (`user_id PRIMARY KEY`, not a separate surrogate id),
-- matching this session's own spec text verbatim ("a new, real, small
-- table storing each real user's CURRENT FCM device token"), not a
-- multi-device history table -- a genuinely simpler, narrower real
-- shape than `sent_messages`/`interview_detection_checked_messages`,
-- deliberately: a fresh real app install/sign-in on a second real
-- device is expected to overwrite the previous real token outright
-- (the old device's token is dead the moment the new one registers),
-- never accumulate stale rows this schema would then need its own
-- cleanup job for.
CREATE TABLE device_tokens (
    user_id UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    fcm_token TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
