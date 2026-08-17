# IMPL_18: NEGOTIATION — TRIGGER
## The first real piece of the project's headline feature, and a genuinely named scenario finally running as code

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §8.1, `QUORUM_DATA_CONTRACTS.md` §1.8

**Prerequisites:** All five domain agents (`IMPL_13`–`IMPL_17`).

**Review tier:** STANDARD. Pure computation, zero LLM calls, zero external side effects.

**What this session is, precisely:** the `ConflictScan` — the real answer to "should negotiation even fire." Per the ADD, this is explicitly **computation, not inference**: whether a resource claim exceeds real available capacity is a fact, checked by comparison, never guessed by a model. This matters architecturally, not just as an efficiency choice — it's what guarantees negotiation only ever fires on genuine conflicts, never on a model's mistaken impression of one.

**What this session creates:** `backend/negotiation/trigger.py` — `CLAIM_TYPE_TO_DOMAIN`, `DomainState`, `ConflictScanResult`, `scan_for_conflicts()`.

**Out of scope:** producing each domain's actual `Position` once a conflict is confirmed — that's `IMPL_19`. This session only decides *whether* negotiation should start, not what any domain would say once it does.

---

## FILE 1: `backend/negotiation/trigger.py` (real, complete — see file)

**The real threshold, proven, not just implemented:** `test_single_domain_conflict_does_not_trigger_negotiation` confirms a single conflicted domain — an ordinary over-budget expense, for instance — does *not* trigger the full negotiation subgraph. Getting this wrong in either direction would be a real problem: too permissive, and every simple Stage A failure would balloon into unnecessary multi-agent negotiation; too strict, and genuine three-way collisions might slip through unrecognized.

**The scenario named throughout this entire project's design history, finally real:** `test_two_domain_conflict_triggers_negotiation` runs the exact interview-vs-deadline-vs-fee case first discussed when Career was added to the architecture as "the domain most likely to produce a genuine three-way collision" — 2 hours needed against 1 available, ₹500 needed against ₹200 available, both domains correctly flagged, negotiation correctly triggered.

**A real safety property, deliberately tested:** `test_a_claim_with_no_matching_domain_state_is_never_treated_as_a_conflict` proves that missing real state resolves to "cannot determine," never to a silently-assumed conflict — the same epistemic honesty as the Gate's own `no_data_found` state, applied here for the first time outside the Gate itself.

## FILE 2: real tests (6/6 passing — see file)

---

## VERIFICATION STEPS

**Step 1:** `ruff check backend` → `All checks passed!` — **verified live.**
**Step 2:** `PYTHONPATH=backend pytest backend/tests/test_negotiation_trigger.py -v` → `6 passed` — **verified live.**
**Step 3 (whole-suite confirmation):** `PYTHONPATH=backend pytest backend/tests -q` → Expected: **120 passed** (114 prior + 6 new) — **verified live, this run.**

---

## WHEN ALL VERIFICATIONS PASS

```bash
git add -A
git commit -m "IMPL-18: Negotiation trigger. Pure computation, zero LLM calls. The exact interview-vs-deadline-vs-fee scenario named throughout this project's design history now runs as real, passing code. 6/6 tests passing, 120/120 total suite."
```

**Update `STATUS_INDEX.md`** — negotiation begins; note explicitly that the trigger is complete but Positions, synthesis, and impact simulation (`IMPL_19`–`IMPL_21`) remain.

**Append to `DECISIONS_LOG.md`:** the real scenario now running, and the no-data-found safety property.

---

*Document version: 1.0 — `IMPL_19` builds real Position generation for each conflicted domain this trigger identifies.*
