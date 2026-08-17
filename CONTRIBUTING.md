# Contributing to Quorum

This describes the real, already-practiced development workflow, not
a generic open-source template.

## The session model

Every unit of work here is a "session," each with its own real
specification document under `specs/tier2_implementation/` (backend,
`IMPL_XX`) or `specs/tier4_mobile/` (mobile, `MOBILE_XX`). Before
writing any code:

1. Read the session's own document in full.
2. Check `specs/tier3_verification/STATUS_INDEX.md` for real current
   state — never assume a prior session's claim without checking.
3. Branch as `session/<short-name>` off `main` — this convention is
   already live in `.github/workflows/ci.yml`.

## Review tiers

Every session states its own review tier in its own document:

- **STANDARD** — the default.
- **CRITICAL** — reserved for anything touching the Gate, security,
  secrets, or a real external-action path. CRITICAL review means
  fresh-context tracing of every branch and confirmation that no code
  path can bypass an absolute rule — not just a label.

Full rules: `.claude/CLAUDE.md`.

## Before opening a pull request

- `ruff check backend` and `pytest backend/tests -q` (backend
  changes) — both must be clean, live, not assumed.
- `dart test` and `flutter analyze` (mobile changes), run on a real
  machine — this environment cannot run these.
- Update `specs/tier3_verification/STATUS_INDEX.md` and append a real
  entry to `DECISIONS_LOG.md` for anything a future session would need
  to know.

## What "done" means here

Not "written." A claim is only real once it's been run and its
output shown — see `specs/tier3_verification/VERIFICATION_STANDARDS.md`
for the full standard this project holds itself to.