# IMPL_17: AGENT — CAREER
## The fifth and final domain agent — and the first genuinely branching graph in this project

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §9.5

**Prerequisites:** `IMPL_16`.

**Review tier:** STANDARD.

**What makes this session genuinely different from the four before it:** Email, Calendar, Tasks, and Finance were each a single linear node — one input state, one proposal out. Career genuinely branches: it always proposes an application-status update, and *conditionally* — only when a real interview is detected with real search findings already available — it also compiles a company digest. Before writing this, the real `add_conditional_edges` API was confirmed against the actually-installed LangGraph version with a small standalone proof-of-concept graph, run both ways (branch taken, branch skipped), the same discipline applied to the basic API in `IMPL_13`.

**Inherits, without re-deriving:** the "agents propose, Gate verifies" boundary from DEC-013 — this agent has no detection pipeline of its own; classification arrives as already-resolved state from Email's ingestion, per the ADD's explicit design.

**What this session creates:** `backend/agents/career_agent.py`; extends `DOMAIN_TOOL_MAP` with `career.update_application_status`, `career.read` — completing all five domains.

**Out of scope:** the real Tavily search call itself — `search_findings` arrives as already-fetched input here, same injected-dependency pattern as every real/external boundary in this project. Email's own classification pipeline that produces `is_interview_detected` is also out of scope — that's `IMPL_13`'s territory, extended, not this session's.

---

## FILE 1: `backend/agents/career_agent.py` (real, complete — see file)

**The real branching decision, proven on both paths, not just the happy one:**
- `test_real_graph_compiles_digest_when_interview_detected_with_findings` — the branch-taken path, confirming the digest genuinely gets produced, using the already-real `compile_digest()` from `career_digest.py` (DEC-004), not reimplemented.
- `test_real_graph_skips_digest_when_no_interview_detected` — the branch-skipped path, confirming `digest` genuinely stays `None`, not just unchecked in that test.
- `test_real_graph_skips_digest_when_interview_detected_but_no_findings_yet` — a genuine edge case worth naming: detection and search are two separate real steps that can complete at different times. An interview flagged before its digest search has returned must not call `compile_digest()` on nothing. Easy to skip writing; deliberately not skipped.

## FILE 2: `tool_authorization.py`, now feature-complete for five domains

`test_full_five_domain_authorization_matrix_holds` re-runs the exhaustive matrix proof from `IMPL_16` at full scope — all five real domains, checked against each other, not just the four that existed a session ago.

## FILE 3: real tests (7/7 passing — see file)

---

## VERIFICATION STEPS

**Step 1:** `ruff check backend` → `All checks passed!` — **verified live.**
**Step 2:** `PYTHONPATH=backend pytest backend/tests/test_career_agent.py -v` → `7 passed` — **verified live.**
**Step 3 (whole-suite confirmation):** `PYTHONPATH=backend pytest backend/tests -q` → Expected: **114 passed** (107 prior + 7 new) — **verified live, this run.**

---

## WHEN ALL VERIFICATIONS PASS

```bash
git add -A
git commit -m "IMPL-17: Agent — Career. Fifth and final domain agent. First genuinely branching graph in this project, both paths proven separately including a real edge case. Five-domain authorization matrix complete. 7/7 tests passing, 114/114 total suite."
```

**Update `STATUS_INDEX.md`** — all five domain agents now real. This is a genuine milestone: **Milestone Checkpoint 2 (per `SESSION_GUIDE.md`, "all domains real") is reached** — Handbook Walkthrough 3 is now due.

**Append to `DECISIONS_LOG.md`:** the branching-graph proof, the edge case explicitly named, and the milestone reached.

---

*Document version: 1.0 — `IMPL_18` begins negotiation, which needs at least two real domains in conflict to have anything to resolve. All five now exist.*
