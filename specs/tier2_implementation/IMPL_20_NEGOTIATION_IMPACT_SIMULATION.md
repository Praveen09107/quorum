# IMPL_20: NEGOTIATION — IMPACT SIMULATION
## The literal proof of "the numbers are reproducible, only the narration is generative"

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §8.4, `QUORUM_DATA_CONTRACTS.md` §1.8

**Prerequisites:** `IMPL_19`.

**Review tier:** STANDARD. Pure arithmetic, zero LLM calls, zero external side effects — the same category as `IMPL_18`'s trigger.

**A note on this session's context:** this was built immediately after a live re-verification pass found a real gap — `DEC-004` had been referenced by name in three later documents but was never actually written into `DECISIONS_LOG.md`. That's now fixed (see the log directly). This session holds to the identical standard as everything before that finding — a fresh problem discovered doesn't lower the bar for what comes next, if anything it's a reason to hold it more carefully.

**What this session creates:** `backend/negotiation/impact_simulator.py` — `DomainSnapshot`, `OptionEffect`, `apply_effect()`, `compute_deltas()`, `simulate_all_options()`.

**Out of scope:** producing the real `OptionEffect` values for actual synthesized options — that mapping is domain-specific work for whichever session wires the full negotiation subgraph together (`IMPL_21`). This session only proves the computation itself is correct, deterministic, and non-mutating.

---

## FILE 1: `backend/negotiation/impact_simulator.py` (real, complete — see file)

**The specific sentence this module exists to make literally true, not just aspirationally true:** *"the numbers are reproducible; only the narration is generative."* `test_the_same_inputs_always_produce_the_same_deltas_across_many_runs` doesn't check this twice — it runs the same computation 50 times and asserts every single result is identical. A two-run check could pass by coincidence on non-deterministic code; fifty runs is a meaningfully stronger claim.

**A real safety property, proven not assumed:** `test_apply_effect_never_mutates_the_original_baseline` confirms the real domain snapshot passed in is provably untouched after computing an option's effect against it — load-bearing, since real negotiation code needs to compute multiple options against the *same* baseline without one option's computation corrupting the baseline for the next.

**The honest "do nothing" case, not silently special-cased:** `test_do_nothing_option_produces_all_unchanged_deltas` confirms declining to act produces real, computed zero-change deltas — the same code path as every other option, not an exception carved out that could hide a bug.

## FILE 2: real tests (6/6 passing — see file)

---

## VERIFICATION STEPS

**Step 1:** `ruff check backend` → `All checks passed!` — **verified live.**
**Step 2:** `PYTHONPATH=backend pytest backend/tests/test_negotiation_impact_simulator.py -v` → `6 passed` — **verified live.**
**Step 3 (whole-suite confirmation):** `PYTHONPATH=backend pytest backend/tests -q` → Expected: **133 passed** (127 prior + 6 new) — **verified live, this run.**

---

## WHEN ALL VERIFICATIONS PASS

```bash
git add -A
git commit -m "IMPL-20: Negotiation impact simulation. Deterministic, non-mutating, proven reproducible across 50 real runs. 6/6 tests passing, 133/133 total suite."
```

**Update `STATUS_INDEX.md`** — impact simulation real; only subgraph wiring (`IMPL_21`) remains before negotiation — the project's headline feature — is fully complete.

**Append to `DECISIONS_LOG.md`:** the 50-run reproducibility proof and the non-mutation guarantee.

---

*Document version: 1.0 — `IMPL_21` wires all four negotiation pieces (`IMPL_18`–`IMPL_20`) into one real LangGraph subgraph.*
