-- Real schema for GET /today's real needs_you_now and in_motion zones
-- (QUORUM_DATA_CONTRACTS.md §5.4, specified since DEC-026/DEC-028, never
-- implemented -- the real gap found and closed here, DEC-119).

-- action_events already carries every real column needs_you_now
-- requires (proposal_id, action_type, stakes, payload, created_at,
-- resolved_at) -- confirmed directly against 0001_initial_schema/up.sql
-- before writing this migration. The one real, missing piece: no
-- user_id column, the same disclosed per-user-scoping gap already
-- carried by /trust_digest since DEC-101. Closed here for real, from
-- this table's first real consumer (GET /today) onward -- unlike
-- /tasks, /career_pipeline, and /finance/subscriptions, this one never
-- ships unscoped and needs no later retrofit (DEC-110's own lesson,
-- applied up front this time).
ALTER TABLE action_events ADD COLUMN user_id UUID NOT NULL;
CREATE INDEX idx_action_events_user_id ON action_events (user_id);

-- A genuinely new table -- no real persistence for a negotiation's own
-- state exists anywhere in this backend yet. The negotiation subgraph
-- (backend/src/quorum_backend/negotiation/) computes a full negotiation
-- in memory, per request, and has never itself written a real row
-- anywhere. This table is real, minimal, and deliberately sized for
-- both this session's real read need (GET /today's in_motion zone,
-- matching ActiveNegotiationSummary exactly: negotiation_id,
-- conflicted_domains, started_at) and the one real, already-specified
-- endpoint that will need to write to it later
-- (POST /negotiations/{negotiation_id}/choose, QUORUM_DATA_CONTRACTS.md
-- §5.6, specified since DEC-046's audit, still genuinely unbuilt) --
-- resolved_at and chosen_option_id exist now so that endpoint doesn't
-- need its own migration when it's eventually built.
CREATE TABLE negotiations (
    negotiation_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID NOT NULL,
    conflicted_domains   TEXT[] NOT NULL,
    started_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at          TIMESTAMPTZ,
    chosen_option_id     TEXT
);
CREATE INDEX idx_negotiations_user_id ON negotiations (user_id);
