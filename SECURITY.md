# Security Policy

Quorum handles real personal data — email content, calendar details,
financial records — and has a dedicated security layer: trace
scrubbing and account deletion (`backend/src/quorum_backend/security/`,
see `IMPL_22`), and per-memory transparency and deletion
(`security/memory_transparency.py`, see `MOBILE_19`).

## Reporting a vulnerability

If you find a real security issue, do not open a public GitHub issue.
Contact the repository owner directly. Include:

- What you found and how to reproduce it
- What real impact it could have (data exposure, unauthorized action
  execution, authentication bypass)
- Any suggested fix, if you have one

## Scope

The Gate's verification layer, authentication (`auth/`), and the
security module (`security/`) are the highest-priority areas — these
are the CRITICAL-review-tier parts of this codebase per
`.claude/CLAUDE.md`.