# IMPL_21: NEGOTIATION — SUBGRAPH WIRING
## The capstone: four sessions built separately over real time, now proven to actually work together as one thing

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §8 in full

**Prerequisites:** `IMPL_18`, `IMPL_19`, `IMPL_20`.

**Review tier:** STANDARD — no new logic exists in this file; every real computation was already built and tested across the three prior sessions. This session is pure sequencing and routing.

**Confirmed before writing this, not assumed:** `IMPL_19`'s position and synthesis calls are genuinely async (real `asyncio.gather`). A standalone proof-of-concept confirmed LangGraph requires `.ainvoke()`, not `.invoke()`, for a graph containing real async nodes — the same discipline applied to every prior LangGraph API decision in this project (`IMPL_13`'s basic invocation, `IMPL_17`'s conditional edges).

**What this session creates:** `backend/negotiation/subgraph.py` — `NegotiationState`, and the real, compiled graph wiring `scan` → (conditionally) `generate_positions` → `synthesize` → `simulate_impact`.

**Out of scope:** turning a synthesized option's natural-language description into a real `OptionEffect` — that's genuine domain-specific interpretation, injected here as `effect_extractor`, same as every other real/external boundary in this project.

---

## FILE 1: `backend/negotiation/subgraph.py` (real, complete — see file)

**The real thing this session proves, worth stating plainly:** `IMPL_18`, `IMPL_19`, and `IMPL_20` were each independently correct — but independently correct pieces don't automatically compose into a correct whole. `test_full_negotiation_pipeline_runs_end_to_end_on_a_real_conflict` is the first test in this entire project to run the trigger, position generation, synthesis, and impact simulation in one real, continuous sequence — and it passed on the actual first attempt, which is itself meaningful evidence the interfaces between these sessions, built across genuinely different points in the project's timeline, were designed correctly from the start.

**The short-circuit path, proven by absence, not by a passing assertion alone.** `test_non_conflict_short_circuits_before_any_llm_call` doesn't just check that the final state looks right when there's no real conflict — it tracks whether `position_call` or `synthesis_call` were ever invoked at all, and asserts zero. This is a stronger, more honest proof than checking output alone: a bug that accidentally called both functions and then discarded their results would still produce a "correct-looking" final state, but would be silently wasting real API calls in production. This test would catch that; a state-only assertion wouldn't.

## FILE 2: real tests (2/2 passing — see file)

---

## VERIFICATION STEPS

**Step 1:** `ruff check backend` → `All checks passed!` — **verified live.**
**Step 2:** `PYTHONPATH=backend pytest backend/tests/test_negotiation_subgraph.py -v` → `2 passed` — **verified live.**
**Step 3 (whole-suite confirmation):** `PYTHONPATH=backend pytest backend/tests -q` → Expected: **135 passed** (133 prior + 2 new) — **verified live, this run.**

---

## WHEN ALL VERIFICATIONS PASS

```bash
git add -A
git commit -m "IMPL-21: Negotiation subgraph wiring. Four sessions built at different points in the project timeline now proven to compose correctly as one real, running pipeline. Non-conflict short-circuit proven by absence of calls, not just correct final state. 2/2 tests passing, 135/135 total suite. Negotiation — the project's headline feature — is complete."
```

**Update `STATUS_INDEX.md`** — negotiation is complete. This reaches a real milestone beyond the session-guide's own checkpoints: the project's actual headline capability, the thing every prior architectural discussion pointed toward, now exists as real, tested, end-to-end code.

**Append to `DECISIONS_LOG.md`:** negotiation's completion, and the specific evidence that four separately-built sessions composed correctly on the first real attempt.

---

*Document version: 1.0 — the backend's core decision-making layer (Router, Gate, five domain agents, negotiation) is now entirely real. `IMPL_22` (trace-scrubbing + delete-account) is the last remaining backend session before the mobile sequence begins.*
