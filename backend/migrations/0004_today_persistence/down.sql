-- Real rollback for 0004_today_persistence/up.sql, reverse dependency
-- order.
DROP TABLE IF EXISTS negotiations;
ALTER TABLE action_events DROP COLUMN IF EXISTS user_id;
