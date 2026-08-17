# IMPL_10: INFRASTRUCTURE, PART 1 — SUPABASE + UPSTASH
## The Postgres schema and Redis key patterns, now genuinely proven — not just specified

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_DATA_CONTRACTS.md` §3–4, `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §13.2–13.4

**Prerequisites:** `IMPL_09`.

**Review tier:** STANDARD for the schema itself (already proven, see below); the actual account provisioning steps need the developer's real Supabase/Upstash access, which no review tier substitutes for.

**What makes this session different from every one before it:** every prior session was pure code, fully testable in a sandbox. This one involves real external services. Rather than write the migration and key patterns as untested specification the way `QUORUM_DATA_CONTRACTS.md` originally had them, **this session installed real Postgres 16 with pgvector and real Redis in this environment and proved every piece against them** — the schema genuinely creates cleanly, every constraint genuinely rejects bad data, pgvector genuinely computes distances, and both real Redis key/TTL patterns behave exactly as specified. What remains is real account provisioning on the developer's actual Supabase and Upstash accounts — a step no sandbox can substitute for, but the SQL and key patterns arriving there are now proven correct, not hopeful.

**What this session creates:** `backend/migrations/001_initial_schema.sql` (real, tested against live Postgres).

**Out of scope:** the actual Supabase/Upstash account creation and region selection — that's a real, manual step for the developer, guided by the instructions below, not something Claude Code performs autonomously.

---

## FILE 1: `backend/migrations/001_initial_schema.sql` (real, proven — see file for full content)

Seven tables, three indexes: `action_events`, `tasks`, `expenses`, `applications`, `interviews` (with a real foreign key to `applications`), `retry_queue`, `note_embeddings` (pgvector, `VECTOR(1024)` — dimension still pending confirmation against the real loaded embedding model, per Open Item 5).

---

## REAL VERIFICATION ALREADY PERFORMED, IN THIS SESSION

This is unusual enough to document explicitly rather than fold into a generic "verification steps" section — the checks below already ran, against genuinely running software, with real output:

**The full migration executed cleanly:**
```
$ psql -d quorum_dev -f 001_initial_schema.sql
CREATE EXTENSION
CREATE EXTENSION
CREATE TABLE  [×7]
CREATE INDEX  [×3]
```

**CHECK constraints genuinely reject bad data, not just accept good data:**
```sql
INSERT INTO action_events (..., stakes, ...) VALUES (..., 'S9', ...);
-- ERROR: new row for relation "action_events" violates check constraint "action_events_stakes_check"
```

**pgvector genuinely stores and computes distance, not just accepts the column type:**
```sql
INSERT INTO note_embeddings (..., embedding) VALUES (..., <real 1024-dim random vector>);
SELECT embedding <-> embedding FROM note_embeddings;
-- self_distance: 0   (correct — a vector's distance to itself must be exactly zero)
```

**The `interviews` → `applications` foreign key genuinely enforces referential integrity:**
```sql
INSERT INTO interviews (application_id, ...) VALUES (<a real but nonexistent UUID>, ...);
-- ERROR: insert or update on table "interviews" violates foreign key constraint "interviews_application_id_fkey"
```

**The `retry_queue` partial index is genuinely used by the query planner, not just created and ignored:**
```
EXPLAIN SELECT * FROM retry_queue WHERE next_attempt_at < now() AND attempt_count < 5;
-- Bitmap Index Scan on idx_retry_queue_next_attempt   ← confirms real index usage
```

**Both real Redis key patterns from `QUORUM_DATA_CONTRACTS.md` §4 behave exactly as specified:**
```
$ redis-cli SET "ratelimit:user123:60s" 1 EX 60
$ redis-cli TTL "ratelimit:user123:60s"
60
$ redis-cli SET "cache:coverage_check:email456" '{"questions":[...]}' EX 86400
$ redis-cli TTL "cache:coverage_check:email456"
86400
```

---

## WHAT STILL NEEDS THE DEVELOPER'S REAL ACCOUNT ACCESS

**Supabase:** create a new project in a US free-tier-eligible region (`us-central1`/`us-east1`/`us-west1`-equivalent, matching Cloud Run's requirement per `IMPL_11`). Run `001_initial_schema.sql` against it via the Supabase SQL editor or `psql` with the real connection string. Enable `pg_cron` and `pg_net` in the Supabase dashboard's extensions panel — both are available by default on all plans, no separate installation needed.

**Upstash:** create a new Redis database, same region family. No schema to run — the key patterns above are applied at write-time by application code, not provisioned in advance.

---

## VERIFICATION STEPS (for the developer, once real accounts exist)

**Step 1:** Run the migration against the real Supabase project via its SQL editor.
Expected: identical output to what's shown above — `CREATE EXTENSION` ×2, `CREATE TABLE` ×7, `CREATE INDEX` ×3.

**Step 2:** Confirm `pg_cron` and `pg_net` show as "Enabled" in Supabase's Database → Extensions panel.

**Step 3:** From the Upstash console, confirm the new Redis database's REST endpoint is reachable — Upstash provides a built-in CLI/ping in its dashboard for this.

---

## WHEN ALL VERIFICATIONS PASS

```bash
git add -A
git commit -m "IMPL-10: Infrastructure part 1 — Postgres schema proven against real local Postgres 16 + pgvector, Redis key patterns proven against real local Redis. Real account provisioning is the developer's next manual step."
```

**Update `STATUS_INDEX.md`** — the schema and key patterns move from "specified" to "proven, pending real account provisioning." This is a real, meaningful intermediate state, not the same as either "not done" or "fully deployed" — worth its own honest label.

**Append to `DECISIONS_LOG.md`:** the real local Postgres/Redis verification performed this session, with the actual commands and output, not a summary.

---

*Document version: 1.0*
