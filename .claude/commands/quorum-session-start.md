Run the real Quorum pre-session checklist before writing any code. Do not skip a step because it seems obviously fine — confirm each one directly.

**1. Environment confirmation**
- Run `pwd` and confirm the working directory is the real Quorum project root.
- Run `git status` and `git branch --show-current` — report both. If there are uncommitted changes from a prior session, stop and ask before proceeding, don't silently build on top of unreviewed work.
- Confirm which backend layout is actually on disk right now: does `backend/src/quorum_backend/` exist (the target state), or is it still the flat `backend/` layout (the current real state as of `CLAUDE.md`'s last update)? State which one plainly — this determines every import path for the rest of the session.

**2. Read `.claude/CLAUDE.md` in full if it hasn't been read yet this session** (it should already be auto-loaded, but confirm with `/memory` if there's any doubt).

**3. Read `specs/tier3_verification/STATUS_INDEX.md` in full.** This is the real, current source of truth — never assume a prior session's claim about status without checking this file fresh.

**4. Identify which session document this work maps to.** If it's an `IMPL_XX` or `MOBILE_XX` session, find it under `specs/tier2_implementation/` or `specs/tier4_mobile/` and read it completely — every file section and the verification section — before touching anything. If it's Phase 0–6 work per `specs/tier1_foundation/QUORUM_IMPLEMENTATION_STRATEGY.md`, read that phase's section in full, plus the specific open item(s) in `STATUS_INDEX.md` it closes.

**5. Cross-reference check.** For every file this session is about to touch or create, confirm: does it already exist from an earlier session? If so, read the existing file before editing — never assume its current content matches what an old spec described.

**6. Dependency check.** Do this session's imports actually exist yet, at the real paths they're imported from? Check directly, don't assume.

**7. State a one-paragraph plan before writing anything**, naming the specific files this session will touch and the specific verification command(s) that will prove it's done. If any of Rules 1–6 in `CLAUDE.md` are especially relevant to this session (Rule 6's CRITICAL review requirement, in particular), name that explicitly in the plan.

Only after all seven steps are genuinely complete — not assumed complete — begin the actual work.
