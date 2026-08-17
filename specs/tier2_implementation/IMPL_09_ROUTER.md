# IMPL_09: ROUTER
## Stakes lookup + rule-based complexity classification — real, tested, and one genuine design correction made along the way

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_MASTER_REFERENCE.md` §1, `QUORUM_CONFIGURATION_CONSTANTS.md` §1 and §3

**Prerequisites:** `IMPL_08`.

**Review tier:** STANDARD. Stakes is a hardcoded lookup with no judgment involved; complexity is a cold-start heuristic explicitly designed to be replaced later — neither touches Gate internals, security, or a real external action.

**A real design correction, found while implementing, not assumed away:** the ADD's complexity section names "temporal/financial content" as a signal. Read literally, that would classify Sprint 0's own test prompt — *"spent 450 on groceries at DMart"* — as higher complexity than C0, directly contradicting Sprint 0's own use of that exact sentence as an on-device-appropriate extraction example. The fix: the real distinguishing signal isn't the presence of financial or temporal content, it's whether the action's correctness depends on **cross-referencing existing state** (a calendar conflict, a budget ceiling) versus simply recording a new fact. `requires_cross_reference` replaces the looser framing. This is written up explicitly in `router.py`'s own module docstring, not silently changed.

**What this session creates:** `backend/router.py` — `STAKES_TABLE`, `get_stakes()`, `Complexity`, `ComplexitySignals`, `compute_complexity()`.

**Out of scope:** the trained classical-ML complexity classifier that eventually replaces these cold-start rules — that's real future work, gated on real replay data existing, not this session's job. Also out of scope: extracting the actual `ComplexitySignals` values from a real proposal (domain detection, cross-reference detection) — this session takes signals as already-computed input; producing them is each domain agent's job.

---

## FILE 1: `backend/router.py` (real, complete — see file for full content)

Key properties, each independently tested:

- **Stakes has no default, proven not just claimed.** `test_stakes_lookup_raises_loudly_on_an_unmapped_type_never_defaults` constructs a fake unmapped type and asserts `get_stakes` actually raises — this is the concrete proof behind `QUORUM_CONFIGURATION_CONSTANTS.md` §1's rule that an unmapped action type is a bug, not a silently-defaulted case.
- **Exhaustive coverage, checked against the real enum.** `test_stakes_lookup_covers_every_real_action_type` iterates `ActionType` itself, not a hardcoded sample — if a future session adds a new `ActionType` without a matching stakes entry, this test fails immediately, on the next run, not whenever someone happens to notice.
- **The corrected complexity signal, proven against the exact case that motivated it.** `test_expense_logging_is_c0_not_raised_by_financial_content_alone` uses Sprint 0's literal test sentence and asserts `C0`; `test_meeting_move_request_is_c1_because_it_needs_calendar_lookup` is the deliberate contrast case — same domain count, similar text length, different `requires_cross_reference` value, different correct answer. Together they prove the signal is doing real, meaningful work, not just present in the schema.

## FILE 2: `backend/tests/test_router.py` (real, complete — 9/9 passing)

---

## VERIFICATION STEPS

**Step 1:** `ruff check backend` → Expected: `All checks passed!` — **verified live, this run.**
**Step 2:** `PYTHONPATH=backend pytest backend/tests/test_router.py -v` → Expected: `9 passed` — **verified live, this run.**
**Step 3 (whole-suite confirmation):** `PYTHONPATH=backend pytest backend/tests -q` → Expected: **67 passed** (58 prior + 9 new) — **verified live, this run.**

---

## WHEN ALL VERIFICATIONS PASS

```bash
git add -A
git commit -m "IMPL-09: Router — real stakes lookup + complexity classification, 9/9 tests passing, 67/67 total suite. Corrected the financial-content complexity signal after finding it contradicted Sprint 0's own test set."
```

**Update `STATUS_INDEX.md` only** — per the correction made after `IMPL_08`, the frozen `QUORUM_GATE_SPECIFICATION.md` is not touched for a Router-only change, and `QUORUM_MASTER_REFERENCE.md`'s Real Code Index gains one line for `router.py`.

**Append to `DECISIONS_LOG.md`:** the `requires_cross_reference` correction and why it was necessary, plus the real test count.

---

*Document version: 1.0*
