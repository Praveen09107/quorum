# IMPL_02: VALIDATOR — DEADLINE CONFLICT CHECK
## Real remaining-hours math against task-deadline ground truth

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_GATE_SPECIFICATION.md`, `QUORUM_DATA_CONTRACTS.md`

**Prerequisites:** `IMPL_01`.

**Review tier:** STANDARD.

**What this session creates:** `deadline_conflict_check()` and the `TasksAdapter` protocol in `backend/gate/validators.py`.

**Out of scope:** the task-hours estimation itself (already real, part of the Tasks domain's own data model, not this validator's job) — this validator only checks whether a new commitment, added to what's already committed, exceeds real available capacity before a deadline.

---

## FILE 1: `backend/gate/validators.py` (extension — real, already implemented)

```python
class TasksAdapter(Protocol):
    def get_committed_hours_before(self, deadline: datetime) -> float: ...


def deadline_conflict_check(
    claimed_commitment_hours: float | None,
    deadline: datetime | None,
    available_hours_before_deadline: float,
    tasks: TasksAdapter,
) -> Finding:
    if claimed_commitment_hours is None or deadline is None:
        return Finding(validator="DeadlineConflictCheck", claim="No deadline-relevant time commitment in proposal",
                        evidence_state="verified_true", confidence=1.0)

    already_committed = tasks.get_committed_hours_before(deadline)
    total_needed = already_committed + claimed_commitment_hours

    if total_needed <= available_hours_before_deadline:
        return Finding(validator="DeadlineConflictCheck",
                        claim=f"{total_needed}h needed vs {available_hours_before_deadline}h available before {deadline}",
                        evidence_state="verified_true", confidence=1.0)
    return Finding(validator="DeadlineConflictCheck",
                    claim=f"{total_needed}h needed exceeds {available_hours_before_deadline}h available before {deadline}",
                    evidence_state="verified_false", confidence=1.0)
```

## FILE 2: real tests (excerpt, passing)

```python
def test_deadline_conflict_check_verified_false_when_overcommitted():
    tasks = FakeTasks(committed=6.0)
    finding = deadline_conflict_check(3.0, datetime(2026, 8, 22), 8.0, tasks)
    assert finding.evidence_state == "verified_false"  # 6+3=9 > 8 available

def test_deadline_conflict_check_verified_true_when_within_capacity():
    tasks = FakeTasks(committed=2.0)
    finding = deadline_conflict_check(3.0, datetime(2026, 8, 22), 8.0, tasks)
    assert finding.evidence_state == "verified_true"
```

---

## VERIFICATION STEPS

**Step 1:** `ruff check backend` → `All checks passed!` — **verified live.**
**Step 2:** `pytest backend/tests/test_gate_validators_batch2.py -k deadline_conflict -v` → `2 passed` — **verified live.**

---

## WHEN ALL VERIFICATIONS PASS

```bash
git commit -m "IMPL-02: DeadlineConflictCheck — real remaining-hours math validator, 2/2 tests passing"
```

Append to `DECISIONS_LOG.md`: confirmed real; the arithmetic (6+3=9 > 8) is the actual thing under test, not just that a Finding object gets returned.

---

*Document version: 1.0*
