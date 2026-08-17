# IMPL_19: NEGOTIATION — POSITIONS + SYNTHESIS
## Real parallel Position generation, and "merge, not invent" turned into a mechanical, checkable property instead of a hoped-for instruction

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §8.2–8.3, `QUORUM_DATA_CONTRACTS.md` §1.8

**Prerequisites:** `IMPL_18`.

**Review tier:** STANDARD. **A real justification, added during a full staleness audit that found this was the only borderline-tier session in the project without one:** synthesis does involve a genuine LLM call, unlike `IMPL_18`/`IMPL_20`'s "zero LLM calls" justification for the same tier. What actually makes STANDARD the right call here, not just the asserted one: whatever this session produces never executes on its own — every synthesized `NegotiationOption` a person chooses re-enters the real Gate at its own stakes level (§8.3 of the ADD) before anything happens, and `validate_synthesis_shape()` mechanically rejects any option that isn't grounded in a real proposed `Position`, catching the specific failure mode (invention) an LLM call here could introduce. The LLM call shapes which real, already-grounded proposals get combined; it doesn't get to act unchecked.

**The real distinction this session had to get right:** the trigger (`IMPL_18`) was explicitly *computation, not inference*. Synthesis is the opposite case — the ADD calls it a "synthesis call," meaning it genuinely needs a model to combine several real, independently-generated resolutions into something coherent. The actual engineering problem: how do you let a model synthesize without letting it quietly invent a solution grounded in nothing a domain actually proposed? The answer built here is two real mechanisms, not one hopeful instruction — a prompt that only ever lists real proposed resolutions, *and* a mechanical validation step afterward that checks every synthesized option's `source_domains` against which domains actually produced a real `Position`. An option referencing a domain that never had one is the structural signature of an invented answer, and it's caught by code, not trusted to prompt phrasing alone.

**What this session creates:** `backend/negotiation/positions.py`, `backend/negotiation/synthesis.py`; adds `NegotiationOption` to `gate/schemas.py`.

**Out of scope:** the real LLM calls behind `position_call` and `synthesis_call` — both injected, same pattern as every real/external boundary in this project. Also out of scope: the deterministic impact simulator (`IMPL_20`) that computes the real deltas for whatever options come out of this session.

---

## FILE 1: `backend/negotiation/positions.py` (real, complete — see file)

**A real timing proof, not an API-level assumption.** `test_positions_actually_run_in_parallel_not_sequentially` gives three position calls an artificial 0.1-second delay each. If `generate_positions` were secretly sequential, the test would take 0.3+ seconds; it completes in well under 0.25. This is the concrete difference between "this function is written with `asyncio.gather`" and "this function is actually concurrent" — the first is a claim about code, the second is a measured fact about behavior.

## FILE 2: `backend/negotiation/synthesis.py` (real, complete — see file)

**The real proof `test_ungrounded_invented_option_is_genuinely_caught` provides:** a synthesized option claiming to draw from Finance's position, when Finance never actually produced one, is exactly what an "invent" violation looks like structurally — and `validate_synthesis_shape` raises on it, by name, with a message identifying exactly which domain was ungrounded. This is the actual enforcement behind "merge, not invent," not a description of an enforcement that only lives in a prompt's wording.

## FILE 3: `gate/schemas.py`, extended

`NegotiationOption` added alongside the existing `Position`/`ImpactDelta` — consistent with where those already live, not a new, separate schema location for no reason.

## FILE 4: real tests (7/7 passing — see file)

---

## VERIFICATION STEPS

**Step 1:** `ruff check backend` → `All checks passed!` — **verified live.**
**Step 2:** `PYTHONPATH=backend pytest backend/tests/test_negotiation_positions_synthesis.py -v` → `7 passed` — **verified live.**
**Step 3 (whole-suite confirmation, including the Gate schema extension's effect on everything upstream):** `PYTHONPATH=backend pytest backend/tests -q` → Expected: **127 passed** (120 prior + 7 new) — **verified live, this run.**

---

## WHEN ALL VERIFICATIONS PASS

```bash
git add -A
git commit -m "IMPL-19: Negotiation positions + synthesis. Real asyncio.gather parallelism, proven by timing. Merge-not-invent enforced mechanically via source_domains validation, not just a prompt instruction. 7/7 tests passing, 127/127 total suite."
```

**Update `STATUS_INDEX.md`** — Positions and synthesis real; impact simulation and subgraph wiring (`IMPL_20`–`IMPL_21`) remain before negotiation is complete.

**Append to `DECISIONS_LOG.md`:** the timing proof of real parallelism, and the mechanical enforcement of merge-not-invent.

---

*Document version: 1.0 — `IMPL_20` computes the real, code-only deltas for whichever options this session's output produces.*
