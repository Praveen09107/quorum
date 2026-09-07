-- DEC-169 (`QUORUM_FINAL_COMPLETION_PLAN.md` Session 3): real, live
-- tracking so a real received Gmail message is ever classified for
-- interview signal AT MOST ONCE -- confirmed by direct search before
-- designing this, no existing real table tracks arbitrary received
-- messages at all (`sent_messages`, migration 0011, is sent-only, a
-- genuinely different real semantics: recipient/subject/sent_at/
-- replied_at, none of which fit a received message being checked for
-- a real, one-time classification).
--
-- Without this, `features/interview_detection.py`'s own real Groq
-- classification call would re-run against the SAME real message on
-- every single real poll cycle for as long as that message stays
-- within `email_ingestion.py::MAX_MESSAGES_PER_POLL`'s own real
-- "most recent N inbox messages" window (real, live, confirmed:
-- every real poll re-fetches `in:inbox -in:sent` fresh, with no
-- concept of "already seen" for this specific real purpose) -- a real,
-- avoidable, repeated cost directly contradicting this same session's
-- own earlier work (`DEC-165`/`166`) relieving exactly this class of
-- uncoordinated, redundant LLM-call pressure.
--
-- `PRIMARY KEY (user_id, message_id)` makes marking a message checked
-- a real, idempotent `ON CONFLICT DO NOTHING` -- re-marking the same
-- real message twice (a real, live retry after a mid-batch failure) is
-- a harmless no-op, never a duplicate row or a constraint error
-- surfacing as an unrelated real bug.
CREATE TABLE interview_detection_checked_messages (
    user_id     UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    message_id  TEXT NOT NULL,
    checked_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, message_id)
);
