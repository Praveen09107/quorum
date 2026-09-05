# Credential rotation checklist -- Preethish-only, cannot be run from this environment

Closes the "how" half of `STATUS_INDEX.md` item #17. This environment has no
browser/signup access to any of these providers' dashboards and no local CLI
for Supabase/Upstash, so every step below is a real, manual action only
Preethish can take. This file is the precise, ready-to-execute checklist;
nothing in it has been run.

**A real, disclosed reason to prioritize this now, found this session, not
just general hygiene:** while checking the live Cloud Run configuration
(`gcloud run services describe`) to write this checklist accurately, a
command that should have queried env var *names* only instead printed the
real, live *values* of several of the secrets below to this session's own
terminal output and transcript. Nothing was sent anywhere external and no
one else saw it, but those values are now sitting in this machine's local
session history, which is a real, concrete reason (not just prudent
hygiene) to treat `GROQ_API_KEY`, `TAVILY_API_KEY`, `SUPABASE_SERVICE_KEY`,
`UPSTASH_REDIS_REST_TOKEN`, `LANGFUSE_PUBLIC_KEY`, and `LANGFUSE_SECRET_KEY`
as the priority order below. No real secret value appears anywhere in this
file.

## Before you start

- After rotating ANY of these, the live Cloud Run service needs the new
  value before the app can use it -- each item below says exactly which of
  two real mechanisms applies:
  - **Secret Manager-backed** (`GEMINI_API_KEY`, `GOOGLE_OAUTH_CLIENT_SECRET`,
    plus `JWT_SIGNING_KEY`/`SUPABASE_URL`/`GOOGLE_TOKEN_ENCRYPTION_KEY`/
    `INTERNAL_DRAIN_SECRET`, not in scope here since they aren't named in
    item #17): add a new secret **version**, Cloud Run already points at
    `key: latest` so the next real revision picks it up automatically --
    no `gcloud run services update` needed, just a new revision (redeploy,
    or `gcloud run services update quorum-backend --region=asia-south1 --project=quorum-505909 --no-traffic` then route traffic once healthy, matching `DEC-160`/`161`'s own established rollout discipline).
  - **Plain env var** (`SUPABASE_SERVICE_KEY`, `UPSTASH_REDIS_REST_TOKEN`,
    `GROQ_API_KEY`, `TAVILY_API_KEY`, `LANGFUSE_PUBLIC_KEY`,
    `LANGFUSE_SECRET_KEY` -- confirmed live, this is every remaining item
    #17 name): `gcloud run services update quorum-backend --region=asia-south1 --project=quorum-505909 --update-env-vars=VAR_NAME=<new-value>` --
    this alone creates a new revision and serves it immediately, no
    separate traffic-routing step needed for an env-var-only change.
- Also update the matching key in `backend/.env` (local dev) after each
  rotation, so a fresh local run doesn't silently use the old value.
- Test each provider's new key against a real, live call before moving to
  the next one (a quick `curl`/local backend run against that one feature),
  not just "saved in the console" -- matches this project's own "prove the
  real thing" discipline.

## 1. `GROQ_API_KEY` (priority -- see note above)

1. https://console.groq.com/keys -- sign in, revoke the current key, create a new one.
2. `gcloud run services update quorum-backend --region=asia-south1 --project=quorum-505909 --update-env-vars=GROQ_API_KEY=<new-value>`
3. Update `backend/.env`.
4. Verify: any Gate Stage B call (Critic runs on Groq) -- e.g. trigger a real negotiation-detail backfill and confirm it still produces real Critic objections.

## 2. `TAVILY_API_KEY` (priority -- see note above)

1. https://app.tavily.com/ -- sign in, Overview/API Keys, generate a new key, delete the old one.
2. `gcloud run services update quorum-backend --region=asia-south1 --project=quorum-505909 --update-env-vars=TAVILY_API_KEY=<new-value>`
3. Update `backend/.env`.
4. Verify: `POST /internal/career-digest` with a real, eligible application still returns real, non-zero `source_count`.

## 3. `SUPABASE_SERVICE_KEY` (priority -- see note above)

1. https://supabase.com/dashboard/project/dxfeutkeofnbismljhsb/settings/api-keys -- roll/regenerate the service role key. **Careful: this is a genuinely different value from `SUPABASE_URL`** (the Postgres connection string in Secret Manager) -- rotating this one doesn't touch that one.
2. `gcloud run services update quorum-backend --region=asia-south1 --project=quorum-505909 --update-env-vars=SUPABASE_SERVICE_KEY=<new-value>`
3. Update `backend/.env`.
4. Verify: whatever real feature actually calls the Supabase client with this key (not the direct Postgres pool, which uses `SUPABASE_URL`) -- confirm which real call site this is before testing (`grep -rn SUPABASE_SERVICE_KEY backend/src`) rather than assuming.

## 4. `UPSTASH_REDIS_REST_TOKEN` (priority -- see note above)

1. https://console.upstash.com/ -- open the `equipped-doe-118069` database, Details tab, reset/regenerate the REST token.
2. `gcloud run services update quorum-backend --region=asia-south1 --project=quorum-505909 --update-env-vars=UPSTASH_REDIS_REST_TOKEN=<new-value>`
3. Update `backend/.env`.
4. Verify: a real rate-limited endpoint still enforces its limit correctly after rotation.

## 5. `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` (priority -- see note above; rotate together, they're a pair)

1. https://cloud.langfuse.com/ -- Settings → API Keys on the real Quorum project, create a new key pair, delete the old one.
2. `gcloud run services update quorum-backend --region=asia-south1 --project=quorum-505909 --update-env-vars=LANGFUSE_PUBLIC_KEY=<new-value>,LANGFUSE_SECRET_KEY=<new-value>`
3. Update `backend/.env` (both keys).
4. Verify: trigger any real Gate call and confirm a new real trace appears in the Langfuse dashboard afterward.

## 6. `GEMINI_API_KEY` (Secret Manager-backed -- lower urgency, not part of this session's plaintext-exposure incident)

1. https://aistudio.google.com/apikey -- sign in, delete the current key, create a new one.
2. `gcloud secrets versions add gemini-api-key --project=quorum-505909 --data-file=- ` (paste the new key, then Ctrl+D / Ctrl+Z+Enter) -- Cloud Run already reads `key: latest`, so the **next new revision** picks it up. Trigger one (e.g. re-run the CI/CD pipeline, or `gcloud run services update quorum-backend --region=asia-south1 --project=quorum-505909 --no-traffic` then route traffic once its own `/health` is confirmed, matching `DEC-160`/`161`'s established rollout discipline).
3. Update `backend/.env`.
4. Verify: a real Gate Judge call (Gemini) still succeeds.

## 7. `GOOGLE_OAUTH_CLIENT_SECRET` (Secret Manager-backed -- lower urgency, not part of this session's plaintext-exposure incident)

1. https://console.cloud.google.com/apis/credentials?project=quorum-505909 -- open the real OAuth client (`649581407643-...`), reset the client secret. **Caution, real and disclosed:** this invalidates every currently-issued refresh token for every real user who has ever granted Gmail/Calendar access (including the sandbox test account) -- re-authorization (a real, one-time browser consent flow) will be needed afterward for each. Confirm this is an acceptable real interruption before rotating, or schedule it deliberately rather than doing it as a routine sweep.
2. `gcloud secrets versions add google-oauth-client-secret --project=quorum-505909 --data-file=-`
3. Trigger a new revision (same as `GEMINI_API_KEY` above).
4. Update `backend/.env`.
5. Re-authorize the sandbox Google account (`quorum.dev.sandbox@gmail.com`) through the real, live OAuth flow.
6. Verify: a real Gmail/Calendar-touching feature still works end to end after re-auth.

## Related, separate, also Preethish-only real action

`backend/scripts/enable_career_digest_cron.sql` is real and ready but not
yet run -- enabling it is a genuinely separate action (Supabase dashboard,
SQL editor, not a credential rotation) but shares the same "needs
Preethish's own console access" shape as everything above; worth doing in
the same sitting if convenient.
