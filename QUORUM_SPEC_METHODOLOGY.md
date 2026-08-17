# QUORUM — Spec Creation Methodology

## What this document is

The rules for how every implementation spec gets written, what it must contain, and how a session actually runs — for the whole life of the project, not just the first one. This is the "how" companion to `CLAUDE.md`'s "what must never be violated." Read this once in full before writing the first spec; after that, the reusable template in Part 2 is what you'll actually use every time.

---

## Part 1 — The Tier Structure

```
quorum/
├── CLAUDE.md                              # operating contract, loaded every session
├── QUORUM_SPEC_METHODOLOGY.md             # this document
├── QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md # the system architecture reference — corrected here: this
│                                           # was missing from this map entirely despite living at the
│                                           # same root level as the two files above it
│
└── specs/
    ├── tier0_agent_guide/
    │   └── SESSION_GUIDE.md                   # ordered list of sessions, one line each, dependency order
    │
    ├── tier1_foundation/                      # frozen — amended, never edited directly
    │   ├── QUORUM_MASTER_REFERENCE.md             # architecture overview, topology, the seven layers
    │   ├── QUORUM_DATA_CONTRACTS.md               # every schema/payload crossing a boundary
    │   ├── QUORUM_CONFIGURATION_CONSTANTS.md      # every hardcoded number: ports, thresholds, weights, TTLs
    │   └── QUORUM_GATE_SPECIFICATION.md           # the Gate in full — elevated to its own foundation doc,
    │                                               # not filed as one domain among five, because it's the thesis
    │
    ├── tier2_implementation/                  # per-session backend build specs
    │   └── IMPL_NN_<name>.md
    │
    ├── tier3_verification/
    │   ├── DECISIONS_LOG.md                       # append-only record of what actually happened
    │   ├── STATUS_INDEX.md                        # "what's actually built right now" pointer doc
    │   ├── TESTING_STRATEGY.md                    # added later in the real project — corrected here,
    │   └── VERIFICATION_STANDARDS.md              # this tree previously showed only the first two files
    │
    └── tier4_mobile/                          # per-session Flutter build specs
        └── MOBILE_NN_<name>.md
```

**`tier1_amendments/` and `tier5_historical/` were never actually created**, across the entire real project — confirmed during a full staleness audit. Real corrections happened many times (`DEC-006`'s five fixes, `DEC-009`'s router correction, and others); `DECISIONS_LOG.md` adequately absorbed the role these directories were meant to serve, and the bootstrap trigger for creating them was never actually met in practice. If a future session genuinely needs them, create them then — this note isn't a commitment that they must exist, just an honest correction that the original "not created yet" framing implied they eventually would be, and they weren't.

**The authority rule, unchanged from AEGIS:** `tier3_verification` always wins. If `DECISIONS_LOG.md` disagrees with `tier1_foundation`, the foundation doc was the plan and the log is what actually happened.

**`STATUS_INDEX.md` exists so `CLAUDE.md` never has to hold live status.** `CLAUDE.md` is read every session — stale status there is a guaranteed, repeated lie. It just points here.

---

## Part 2 — The Reusable Implementation Spec Template

Every session doc, backend or mobile, follows this skeleton exactly. This is the load-bearing artifact of the whole methodology — get this right once, and every future spec is mechanical to write correctly.

```markdown
# IMPL_NN (or MOBILE_NN): SESSION TITLE
## One-line description of what this session builds

---

## AGENT INSTRUCTIONS FOR THIS SESSION

You are implementing Session NN: <name>.

**Attach:** <the 3-4 specific foundation docs this session actually needs — never the whole spec corpus>

**Prerequisites:** Session(s) X complete. <any runtime dependency — e.g. "Supabase project provisioned">

**Review tier:** <STANDARD (fresh-context review) | CRITICAL (cross-model review — Gate/security/auth/
secrets/real-action-path code only, per CLAUDE.md Rule 6)>

**What this session creates:**
- `path/to/file_one.py` — one-line purpose
- `path/to/file_two.py` — one-line purpose
- `tests/unit/test_file_one.py` — what it tests

**Out of scope for this session:** <explicit — what a reasonable agent might be tempted to also build,
named specifically so it doesn't happen silently>

**<Any load-bearing formula/contract, restated inline even though it also lives in tier1>**

---

## FILE 1: path/to/file_one.py

<complete, exact, runnable code — never pseudocode, never "// implement this here">

## FILE 2: tests/unit/test_file_one.py

<complete test file>

---

## VERIFICATION STEPS

**Step 1:** <what you're checking>
`<exact runnable command>`
Expected: `<exact literal expected output, not "should work">`

**Step 2:** <next check — live, against the real system, not just static analysis>
...

---

## WHEN ALL VERIFICATIONS PASS

```bash
git add -A
git commit -m "IMPL-NN: <session title> — <what was verified, specifically>"
```

Append to `DECISIONS_LOG.md`:
- What was confirmed, with the real command/output
- Any deviation from the spec, and why
- **If Review tier = CRITICAL: which model reviewed it, and what the review found**
```

**Why every piece of this shape is here, not decorative:**

- **Real, complete code — never placeholders.** This is what makes "no invented architecture" enforceable. `IMPL_01` should pin exact dependency versions, not ranges — the same discipline AEGIS proved matters.
- **Tests live in the same document as the implementation.** Forces correctness thinking (boundary values, edge cases) at spec-writing time, not deferred to whoever implements.
- **Literal expected output, every verification step.** A pattern-match, not a judgment call — this is what makes "verified" a checkable claim instead of a vibe.
- **"Out of scope," stated explicitly.** New addition versus AEGIS's original template, adopted from the current field's own best practice: bounding the agent's exploration prevents the "read hundreds of files, fill the context" failure mode, and prevents good-idea scope creep from happening silently.
- **"Review tier," stated explicitly in every spec.** This is the mechanism that makes Rule 6 real rather than aspirational — the spec itself declares whether fresh-context or cross-model review applies, so it's never a judgment call made under time pressure mid-session.
- **The commit message and decisions-log update are part of the spec itself.** This is what produces a real audit trail instead of just code.

---

## Part 3 — The Session Workflow

```bash
# 1. Branch
git checkout main && git status   # confirm clean before branching
git checkout -b session/build-NN-short-name
```

```
# 2. Environment check — stop and report if anything's wrong, don't proceed on an
#    unconfirmed environment
Confirm: correct working directory, correct branch, required services reachable,
correct runtime version.
```

```
# 3. Spec-reading discipline — no writing in between passes
Pass 1 — full read, no writing. Every file section, the verification section, every
IMPORTANT/CRITICAL callout.
Pass 2 — cross-reference: does each file this session touches already exist from an
earlier session?
Pass 3 — dependency check: do this session's imports actually exist yet? If not —
stop, don't guess whether sessions are out of order or an earlier one is incomplete.
```

```
# 4. Implement exactly what the spec (as corrected by DECISIONS_LOG) says. Nothing
#    extra — a good idea out of scope becomes a logged OPEN item, not silent work.
```

```
# 5. Verify — every step in the spec, live, not "looks right"
```

```
# 6. Review — per the spec's declared Review tier
STANDARD: fresh-context subagent reviews the diff, sees only the code and the
criteria, reports gaps.
CRITICAL: the review subagent runs on a different model family than the one that
implemented the session. Do not skip this substitution for CRITICAL-tier work —
a fresh context on the same model is not the same strength of independence.
```

```bash
# 7. Commit, merge — only after the full verification gate passes
git add -A && git commit -m "IMPL-NN: <specific>"
git checkout main && git merge session/build-NN-short-name
# Push to a shared remote is a separate, explicit decision — never done by default.
```

---

## Part 4 — Mapping Onto Claude Code's Actual Surfaces

This is the one deliberate platform-level upgrade versus AEGIS's original command-only approach — Claude Code now has four surfaces with a clear ownership rule: enforceable rules → hooks; contextual knowledge → skills; delegation boundaries → subagents; always-on guidance → `CLAUDE.md`.

| AEGIS pattern | Quorum's surface | Why |
|---|---|---|
| `/aegis-verify` (a command, skippable) | **A hook**, firing on any commit/merge attempt | Enforcement should not depend on the agent remembering to invoke it |
| `/aegis-session-start` (a command) | **A skill** — the 3-pass spec-reading discipline | Contextual knowledge, loaded when a session actually starts, not always-resident |
| `/aegis-retrofit-check` | **A skill** — diagnostic-first check before modifying existing code | Same reasoning — knowledge needed some sessions, not every session |
| `/aegis-report-blocker` | **Stays a command** | A deliberately-invoked prompt template, not an enforcement rule |
| Fresh-context review | **A subagent**, standard for all sessions | Isolated context, own tools, reports back without the implementer's reasoning biasing it |
| Cross-model review (new, Quorum-specific) | **A subagent explicitly configured to a different model** for CRITICAL-tier sessions | The one genuine methodology upgrade beyond platform mapping — see `CLAUDE.md` Rule 6 |

---

## Part 4.5 — The Blocker Report Template (specified, never yet triggered — a real gap, not hypothetical)

Checked against this project's real history: this discipline has never actually fired, because no genuine spec-vs-reality contradiction has come up yet in anything built so far — every real bug found was self-correctable within the same session. Given a real template now, so the first genuine trigger doesn't require improvising the format under pressure:

```markdown
## Blocker Report — [Session/Task]

### 1. What was attempted, in order
[Real, specific sequence of steps taken]

### 2. The exact discrepancy found
[Real file content vs. real spec content, quoted precisely — not summarized]

### 3. What was already ruled out
[e.g., "not a stale-copy issue — confirmed via X"]

### 4. Best guess at cause (explicitly labeled as a guess)
[Reasoning, clearly flagged as speculation, not asserted as fact]

### What I need from you:
[A specific, answerable question with the real trade-off named — never "what should I do"]
```

## Part 4.6 — Cross-Model Review, Corrected (a real mechanism gap, found on review, not present in AEGIS since AEGIS never had this rule)

`CLAUDE.md` Rule 6 originally stated cross-model review is mandatory for Gate-touching code, without specifying *how* — Claude Code has no built-in mechanism to hand a diff to a genuinely different model family for review. Corrected into two tiers:

- **Automatable, every CRITICAL-tier session:** a fresh-context Claude subagent reviews the diff, *and* live verification against the real system wherever one exists (a real Gemini/Groq call, a real Postgres query) — a disagreeing live system is a more genuine independent check than same-family re-review, and directly implements AEGIS's own Part 7 principle ("live systems over static reading") as the actual independence mechanism.
- **Manual, reserved for specific high-stakes moments** — merging the real Gate orchestration function itself, not every Gate-adjacent change: the developer manually pastes the diff into a genuinely different model's interface for a second read. A deliberate, occasional practice, not a blanket rule that was never actually achievable as originally stated.

## Part 4.7 — Git Discipline (specified from Sprint 0, not practiced once — corrected going forward, not retroactively)

Checked directly against the real repo: zero commits, zero session branches exist, despite the Gate schemas, prompts, validators, and twelve feature modules all being real and tested. This is the exact failure mode Part 9 of the AEGIS original warns about — work that looks fine because it IS fine, but built without the mechanical safety net that catches the next mistake that ISN'T self-evidently fine. **Every session from this point forward gets its own branch per Part 3 of this document, without exception** — this session's existing work stays as-is rather than being rewritten to look retroactively compliant.

## Part 4.8 — A Real, Quorum-Specific Failure Mode (this project's own first entry in AEGIS Part 11's tradition)

**The methodology documents themselves were written and delivered, but never actually integrated into the real repository.** `CLAUDE.md` and this methodology document existed only in the delivery/output location, never copied into the actual project tree — and `CLAUDE.md`'s specified location (repo root) didn't even match AEGIS's own proven `.claude/CLAUDE.md` convention. A document "delivered" is not the same claim as a document "load-bearing in the real project" — found only by directly checking the real filesystem, exactly per AEGIS's own Part 7 discipline ("grep for the exact thing you're worried about"), not by trusting that writing something thoroughly means it was actually placed correctly.

---

## Part 5 — Verification Philosophy (unchanged from the proven original, restated for Quorum)

Live systems over static reading — don't infer an endpoint works from reading the handler, call it with a real token and read the real response. Real credentials except the sandbox carve-out in `CLAUDE.md` Rule 5. A failing check is a failing session, full stop — not "mostly passes." Disclose what couldn't be verified explicitly, rather than implying success by omission. When you find a bug in your own earlier work, say so plainly — the log's credibility depends on that honesty.

**One Quorum-specific addition:** for anything in the Gate's verification chain specifically, the bar is higher than "the code runs" — confirm the *three-valued* logic is actually exercised (a test that only ever hits `verified_true` hasn't tested the Gate; it's tested the happy path).

---

## Part 6 — Worked Example: Session 00 (Illustrative — Corrected Note Below)

Applying Part 2's template to a representative first session, so this methodology is demonstrated, not just described.

**A real correction, found during a full staleness audit and worth stating plainly rather than quietly rewriting history: this worked example does not describe what the real `IMPL_00` actually became.** The plan changed at some point after this section was written — the real first backend session is `IMPL_00_SPRINT_0_MODEL_RESOLUTION.md` (empirically resolving the on-device model and Flutter plugin choice), not the repo/infrastructure skeleton described below. Nobody went back to update this worked example when the plan changed, and the same stale claim independently existed in `CLAUDE.md`'s "Current status" section (also now corrected). The example below is left as-is, because it's still a genuinely clean illustration of the template's *shape* — attach list, review tier, explicit scope, literal verification output, the commit-and-log close — even though its *content* isn't real. Read `specs/tier2_implementation/IMPL_00_SPRINT_0_MODEL_RESOLUTION.md` directly for what session 00 actually is.

```markdown
# IMPL_00: REPO AND INFRASTRUCTURE SKELETON (illustrative — see note above; not the real IMPL_00)
## Establishes the repo structure, Docker Compose skeleton, and CI pipeline — nothing else

---

## AGENT INSTRUCTIONS FOR THIS SESSION

You are implementing Session 00: Repo and Infrastructure Skeleton.

**Attach:** QUORUM_MASTER_REFERENCE.md, QUORUM_CONFIGURATION_CONSTANTS.md

**Prerequisites:** None — this is the first session.

**Review tier:** STANDARD

**What this session creates:**
- `backend/` — empty FastAPI app skeleton, `main.py` with a single `/health` route
- `docker-compose.yml` — app service only (Supabase/Upstash/Langfuse are external managed
  services, never containerized locally)
- `.github/workflows/ci.yml` — lint → unit test (placeholder suite) → build, on every push
- `.gitignore`, `pyproject.toml` with pinned real dependency versions

**Out of scope for this session:** No LangGraph, no Gate code, no domain agents, no real
Supabase connection yet — this session proves the skeleton runs and CI is green, nothing more.

---

[real, complete file contents for each file listed above]

---

## VERIFICATION STEPS

**Step 1:** Local health check
`docker compose up -d && curl -s http://localhost:8000/health`
Expected: `{"status": "ok"}`

**Step 2:** CI pipeline runs clean on push
`git push origin session/build-00-skeleton` → check GitHub Actions run
Expected: all three CI steps (lint, test, build) show green

---

## WHEN ALL VERIFICATIONS PASS

git commit -m "IMPL-00: Repo and infra skeleton — health check + CI pipeline confirmed green"

DECISIONS_LOG entry: an illustrative entry number, since this session is illustrative — the real
DEC-002 in the actual log covers something else entirely (Final Master Review Findings), not this.
```

This is the actual shape every future session takes — Session 01 onward just fills in real substance against this same skeleton.

---

*This document is itself governed by `DECISIONS_LOG.md`'s authority rule — if reality diverges from what's written here, the log wins, and this document gets corrected to match, not the other way around.*
