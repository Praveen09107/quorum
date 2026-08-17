# IMPL_16: AGENT — FINANCE
## Fourth real LangGraph node — and the full cross-domain authorization matrix, proven exhaustively for the first time

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §9.4

**Prerequisites:** `IMPL_15`.

**Review tier:** STANDARD.

**Inherits, without re-deriving:** per DEC-013, no self-check of `budget_check()` before proposing. Subscription Detective (`subscription_detective.py`, already real) stays a proactive, scheduling-layer concern.

**What this session creates:** `backend/agents/finance_agent.py`; extends `DOMAIN_TOOL_MAP` with `finance.log_expense`, `finance.update_budget`, `finance.read`.

**Out of scope:** real Finance-DB writes — injected/deferred.

---

## FILE 1: `backend/agents/finance_agent.py` (real, complete — see file)

**The real decision:** logging a new expense (`LOG_EXPENSE`, S1) versus changing a budget ceiling itself (`UPDATE_BUDGET`, S2) — a genuinely different-stakes distinction, confirmed through the real Router exactly as Calendar's local/external split was in `IMPL_14`.

## FILE 2: `tool_authorization.py` extended, and proven exhaustively for the first time

With four real domains now in `DOMAIN_TOOL_MAP`, this session adds `test_full_cross_domain_authorization_matrix_holds_for_all_four_real_domains` — not one more pairwise spot-check, but every domain's tools checked against every other domain programmatically. This is a meaningfully stronger proof than the pairwise tests in `IMPL_13`/`IMPL_14`: it would catch an accidental tool-name collision anywhere in the map, not just in the specific pair someone thought to test.

## FILE 3: real tests (6/6 passing — see file)

---

## VERIFICATION STEPS

**Step 1:** `ruff check backend` → `All checks passed!` — **verified live.**
**Step 2:** `PYTHONPATH=backend pytest backend/tests/test_finance_agent.py -v` → `6 passed` — **verified live.**
**Step 3 (whole-suite confirmation, covering both `IMPL_15` and `IMPL_16`):** `PYTHONPATH=backend pytest backend/tests -q` → Expected: **107 passed** (96 prior + 5 Tasks + 6 Finance) — **verified live, this run.**

---

## WHEN ALL VERIFICATIONS PASS

```bash
git add -A
git commit -m "IMPL-16: Agent — Finance. Fourth real LangGraph node. Expense/budget-change stakes distinction confirmed via the real Router. Full exhaustive cross-domain authorization matrix proven for the first time. 6/6 tests passing, 107/107 total suite (combined with IMPL_15)."
```

**Update `STATUS_INDEX.md`** — both Tasks and Finance move to real; four of five domain agents now complete.

**Append to `DECISIONS_LOG.md`:** the combined `IMPL_15`/`IMPL_16` entry, including the exhaustive authorization matrix as a real, meaningful strengthening of the security proof, not just incremental coverage.

---

*Document version: 1.0 — `IMPL_17` (Career) completes all five domain agents.*
