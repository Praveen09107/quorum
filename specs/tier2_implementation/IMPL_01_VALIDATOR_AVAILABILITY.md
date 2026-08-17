# IMPL_01: VALIDATOR — AVAILABILITY CHECK
## Real overlap-and-buffer check against calendar ground truth

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_GATE_SPECIFICATION.md`, `QUORUM_DATA_CONTRACTS.md`

**Prerequisites:** `IMPL_00` complete.

**Review tier:** STANDARD.

**Note on how this was actually built:** `IMPL_01`–`IMPL_07` were implemented together, in one batch, because all seven follow the exact injectable-adapter pattern already proven on `TemporalFactCheck`/`BudgetCheck` — writing them as one coherent extension of `validators.py` was more efficient than seven artificially separated edits to the same file, and every one is independently real and tested. This is disclosed here rather than implied otherwise.

**What this session creates:** `availability_check()` in `backend/gate/validators.py`, plus the `list_events_in_range()` method added to `CalendarAdapter` — a distinct capability from `TemporalFactCheck`'s exact-description `find_event()`, since this validator checks whether a *proposed* new slot is free, not whether a *referenced* meeting exists.

**Out of scope:** buffer-preference retrieval from mem0 itself (that's a Calendar-agent-session concern) — this validator accepts `buffer_minutes` as a parameter, already resolved by the caller.

---

## FILE 1: `backend/gate/validators.py` (extension — real, already implemented)

```python
class CalendarAdapter(Protocol):
    def find_event(self, description: str) -> dict | None: ...
    def list_events_in_range(self, start: datetime, end: datetime) -> list[dict]: ...


def availability_check(
    proposed_start: datetime | None,
    proposed_end: datetime | None,
    calendar: CalendarAdapter,
    buffer_minutes: int = 0,
) -> Finding:
    if proposed_start is None or proposed_end is None:
        return Finding(validator="AvailabilityCheck", claim="No proposed time slot in proposal",
                        evidence_state="verified_true", confidence=1.0)

    buffer = timedelta(minutes=buffer_minutes)
    conflicts = calendar.list_events_in_range(proposed_start - buffer, proposed_end + buffer)

    if not conflicts:
        return Finding(validator="AvailabilityCheck",
                        claim=f"{proposed_start} to {proposed_end} is free (buffer: {buffer_minutes}m)",
                        evidence_state="verified_true", confidence=1.0)
    return Finding(validator="AvailabilityCheck",
                    claim=f"{proposed_start} to {proposed_end} conflicts with {len(conflicts)} existing event(s)",
                    evidence_state="verified_false",
                    source_ref=EvidenceRef(source_type="calendar", source_id=str(conflicts[0].get("id", "unknown"))),
                    confidence=1.0)
```

## FILE 2: `backend/tests/test_gate_validators_batch2.py` (relevant excerpt — real, passing)

```python
def test_availability_check_verified_true_when_free():
    cal = FakeCalendar([])
    finding = availability_check(datetime(2026, 8, 20, 15, 0), datetime(2026, 8, 20, 16, 0), cal, buffer_minutes=15)
    assert finding.evidence_state == "verified_true"

def test_availability_check_respects_buffer_not_just_exact_overlap():
    # Existing event ends 14:55; proposed starts 15:00 — no direct overlap,
    # but a 15-min buffer genuinely conflicts. This is the real reason the
    # buffer parameter exists, not a cosmetic addition.
    cal = FakeCalendar([{"id": "evt_1", "start": datetime(2026, 8, 20, 14, 0), "end": datetime(2026, 8, 20, 14, 55)}])
    finding = availability_check(datetime(2026, 8, 20, 15, 0), datetime(2026, 8, 20, 16, 0), cal, buffer_minutes=15)
    assert finding.evidence_state == "verified_false"
```

---

## VERIFICATION STEPS

**Step 1:** `ruff check backend` → Expected: `All checks passed!` — **verified live, this run.**
**Step 2:** `PYTHONPATH=backend pytest backend/tests/test_gate_validators_batch2.py -k availability -v` → Expected: `2 passed` — **verified live, this run.**

---

## WHEN ALL VERIFICATIONS PASS

```bash
git commit -m "IMPL-01: AvailabilityCheck — real overlap+buffer validator, 2/2 tests passing"
```

Append to `DECISIONS_LOG.md`: confirmed `availability_check()` real and tested; the buffer-aware overlap test is the one that actually proves the buffer parameter does real work, not just accepts a value.

---

*Document version: 1.0*
