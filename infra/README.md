# Infrastructure

Deployment configuration for Cloud Run, Supabase, and the deferred
CI stages named in `DEC-003`. Templates and provisioning notes only —
never real credentials (those go in GitHub Actions secrets or a real
`.env`, never here).

- `docker/` — local dev orchestration (moved from repo root, no
  content change).
- `cloud_run/` — the real Cloud Run service definition, filled in
  once a real project exists (see `STATUS_INDEX.md` open item 3).
- `supabase/` — provisioning steps.
- `github_actions/` — the deferred deploy-cutover CI stage, ready to
  activate once a real deploy target exists.