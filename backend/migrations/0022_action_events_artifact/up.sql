-- `DEC-191` (product rebuild Block C). One real, nullable column:
-- `action_events.artifact` -- the structured external id(s) a real
-- Google API call returned on success (`{"message_id": ...}`,
-- `{"draft_id": ..., "message_id": ...}`, or `{"event_id": ...,
-- "html_link": ...}`), computed by `features/action_executor.py`'s
-- own `_real_gmail_post()`/`_real_gmail_draft_post()`/
-- `_real_google_calendar_post()` and, until this migration, thrown
-- away at the HTTP boundary -- the identical class of gap `DEC-189`
-- found and fixed once already for `email_recipient`/`email_action`.
--
-- WHY THIS MATTERS, concretely: without a persisted artifact id, a
-- real completed action has no way to become a real tappable link
-- into the actual Gmail message, Gmail draft, or Calendar event it
-- produced -- "it drafted this in my Gmail, let me go look at it" is
-- not buildable without this column existing first.
--
-- NULLABLE, DELIBERATELY, with no default -- the identical reasoning
-- migration `0021`'s own up.sql already gives in full for
-- `gate_timeline`/`revision_count`/`pre_revision_payload`: every real
-- row predating this migration genuinely has no recorded artifact
-- (the data was computed and discarded, not merely unobserved), and a
-- default would backfill real history with a confident, unverified
-- value indistinguishable from a real measurement. A row whose own
-- real action never calls a Google API at all (`CREATE_TASK`/
-- `LOG_EXPENSE`/...) is expected to read NULL here forever, not as a
-- gap but as the honest, permanent truth for that row.
--
-- Wrapped in an explicit transaction, following `0019`/`0020`/`0021`'s
-- own established CRITICAL-tier-review-driven precedent: CI applies
-- each migration file via a plain `psql -f` with no
-- `--single-transaction`, so an un-wrapped multi-statement file can
-- commit partially.
BEGIN;

ALTER TABLE action_events ADD COLUMN artifact JSONB;

COMMIT;
