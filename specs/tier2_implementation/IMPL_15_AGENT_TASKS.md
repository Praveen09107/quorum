# IMPL_15: AGENT — TASKS
## Third real LangGraph node, same proven pattern

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §9.3

**Prerequisites:** `IMPL_14`.

**Review tier:** STANDARD.

**Inherits, without re-deriving:** per DEC-013, this agent does not self-check `deadline_conflict_check()` before proposing — that stays Stage A's job. Predictive Risk (`predictive_risk.py`, already real) is a proactive, scheduling-layer concern, not embedded here — same reasoning as Meeting-Load Defense for Calendar.

**What this session creates:** `backend/agents/tasks_agent.py`; extends `DOMAIN_TOOL_MAP` with `tasks.create`, `tasks.update`, `tasks.read`.

**Out of scope:** the real Tasks-DB writes themselves — injected/deferred, same pattern as every prior agent.

---

## FILE 1: `backend/agents/tasks_agent.py` (real, complete — see file)

**The real decision this agent makes:** create versus update, based on whether an existing task is actually referenced — `existing_task_id` present or absent, not inferred from anything fuzzier.

**Proven, not assumed:** `test_both_task_actions_correctly_route_to_s1_via_the_real_router` confirms both `CREATE_TASK` and `UPDATE_TASK` genuinely resolve to S1 through the real Router — the same integration-proof pattern established in `IMPL_14`, applied again rather than treated as a one-off.

## FILE 2: real tests (5/5 passing — see file)

---

## VERIFICATION STEPS

**Step 1:** `ruff check backend` → `All checks passed!` — **verified live.**
**Step 2:** `PYTHONPATH=backend pytest backend/tests/test_tasks_agent.py -v` → `5 passed` — **verified live.**
**Step 3:** `PYTHONPATH=backend pytest backend/tests -q` — full count confirmed together with `IMPL_16` below, since both were built and verified in the same real session.

---

## WHEN ALL VERIFICATIONS PASS

```bash
git add -A
git commit -m "IMPL-15: Agent — Tasks. Third real LangGraph node. Create/update distinction confirmed S1 via the real Router. 5/5 tests passing."
```

**Update `STATUS_INDEX.md` and `DECISIONS_LOG.md`** — see the combined entry covering both `IMPL_15` and `IMPL_16`.

---

*Document version: 1.0*
