-- Real, live table backing Waiting On (Phase 4, `QUORUM_PRODUCTION_
-- COMPLETION_PLAN.md`) -- closes the real gap `QUORUM_ARCHITECTURE_
-- DESIGN_DOCUMENT.md` §9.1 already names ("Waiting On... surfaces
-- sent messages with no reply past a 4-day staleness threshold") and
-- `QUORUM_DATA_CONTRACTS.md` §5.9 already specifies the real response
-- shape for (`recipient`/`subject`/`sent_at`), with `SentMessage`
-- documented there as living at `backend/features/waiting_on.py`.
--
-- One real row per real Gmail message THIS USER sent -- `message_id`/
-- `thread_id` are Gmail's own real, stable identifiers (confirmed
-- against Gmail API's real `users.messages` resource shape before
-- writing this). `UNIQUE (user_id, message_id)` makes real ingestion
-- idempotent: re-polling the same real message twice is a real,
-- harmless no-op (`ON CONFLICT DO NOTHING`), never a duplicate row.
--
-- `replied_at`: real, live ingestion sets this the moment a NEW,
-- real, RECEIVED message in the SAME real `thread_id` is detected --
-- the real signal a reply arrived. `NULL` means genuinely still
-- waiting; `find_stale_waiting_on()` (`features/waiting_on.py`) is
-- the one real, pure function that turns "still waiting" + "sent long
-- enough ago" into the real "waiting on" list a person sees.
CREATE TABLE sent_messages (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    message_id  TEXT NOT NULL,
    thread_id   TEXT NOT NULL,
    recipient   TEXT NOT NULL,
    subject     TEXT NOT NULL,
    sent_at     TIMESTAMPTZ NOT NULL,
    replied_at  TIMESTAMPTZ NULL,
    UNIQUE (user_id, message_id)
);

-- Real, live query patterns this table needs to serve fast, confirmed
-- before indexing, not guessed: `find_stale_waiting_on()`'s own real
-- WHERE clause is always `user_id = $1 AND replied_at IS NULL`; the
-- real ingestion job's own reply-detection UPDATE is always `user_id
-- = $1 AND thread_id = $2 AND replied_at IS NULL`.
CREATE INDEX idx_sent_messages_user_unreplied ON sent_messages (user_id, thread_id) WHERE replied_at IS NULL;
