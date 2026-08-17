# Supabase Provisioning

No live Supabase project exists yet — see
`specs/tier3_verification/STATUS_INDEX.md` open items.

## When ready to provision

1. Create a real Supabase project.
2. Run the real migration: `backend/migrations/0001_initial_schema/up.sql`
3. Enable `pgvector` for `note_embeddings` — confirm the real output
   vector dimension against the loaded Qwen3-Embedding-0.6B model
   before writing it into any migration (see the ADD's real, still-open
   item on this).
4. Add the real project ref and service key to GitHub Actions secrets
   — never commit them here.