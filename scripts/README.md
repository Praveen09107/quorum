# Scripts

- `setup_dev_env.ps1` — real, working local setup for backend + mobile.
- `run_migrations.ps1` — not yet created; depends on a real migration
  tool decision not yet made.
- `seed_demo_dataset.py` — **RESOLVED, `DEC-122`.** Real, working, run
  once against the real Supabase database — corrects this line's own
  stale "not yet created" placeholder. Python, not PowerShell (needs
  real async DB access and the backend's own real negotiation-subgraph
  code, not shell scripting) — run via `PYTHONPATH=src ../.venv/Scripts/
  python.exe ../scripts/seed_demo_dataset.py` from `backend/`. Seeds
  tasks/expenses/applications/interviews/action_events/a negotiation row
  under the one real (non-test) account this database has, refusing to
  run twice without `--force`. Email/Calendar activity appears through
  real `action_events` rows (no dedicated table for either exists in
  this schema) rather than fabricated tables. `--with-negotiation-
  detail` runs the real Gemini-backed negotiation content generation
  separately, gated behind its own real free-tier quota.
