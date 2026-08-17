# IMPL_03: VALIDATOR — RECIPIENT CHECK
## Real thread/contact verification, plus the reply-all hazard flag

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_GATE_SPECIFICATION.md`, `QUORUM_DATA_CONTRACTS.md`

**Prerequisites:** `IMPL_02`.

**Review tier:** STANDARD.

**What this session creates:** `recipient_check()` and the `ContactsAdapter` protocol.

**Out of scope:** contact-list management itself — this validator only reads.

---

## FILE 1: `backend/gate/validators.py` (extension — real, already implemented)

```python
class ContactsAdapter(Protocol):
    def is_known_contact(self, email: str) -> bool: ...


def recipient_check(
    recipient_email: str | None,
    thread_participants: list[str],
    contacts: ContactsAdapter,
    is_reply_all: bool = False,
) -> Finding:
    if recipient_email is None:
        return Finding(validator="RecipientCheck", claim="No recipient in proposal",
                        evidence_state="no_data_found", confidence=0.3)

    in_thread = recipient_email in thread_participants
    known = contacts.is_known_contact(recipient_email)

    if not in_thread and not known:
        return Finding(validator="RecipientCheck",
                        claim=f"{recipient_email} is neither in the thread nor a known contact",
                        evidence_state="verified_false", confidence=1.0)

    if is_reply_all and len(thread_participants) > 5:
        # A judgment call, correctly routed to Stage B — not a hard fail.
        return Finding(validator="RecipientCheck",
                        claim=f"Reply-all to {len(thread_participants)} participants — flagged, not blocked",
                        evidence_state="no_data_found", confidence=0.5)

    return Finding(validator="RecipientCheck",
                    claim=f"{recipient_email} verified as {'thread participant' if in_thread else 'known contact'}",
                    evidence_state="verified_true", confidence=1.0)
```

## FILE 2: real tests (excerpt, passing)

```python
def test_recipient_check_flags_large_reply_all_as_no_data_found_not_hard_fail():
    finding = recipient_check(
        "priya@x.com",
        ["priya@x.com", "a@x.com", "b@x.com", "c@x.com", "d@x.com", "e@x.com"],
        FakeContacts(set()), is_reply_all=True,
    )
    assert finding.evidence_state == "no_data_found"
```

**Why the reply-all case is `no_data_found`, not `verified_false`, worth stating explicitly:** a large reply-all isn't necessarily wrong — some threads genuinely have many legitimate participants. This validator correctly refuses to hard-fail on something it can't actually judge, deferring to Stage B where a Critic can weigh real context (is this a known large working group, or does it look accidental).

---

## VERIFICATION STEPS

**Step 1:** `ruff check backend` → `All checks passed!` — **verified live.**
**Step 2:** `pytest backend/tests/test_gate_validators_batch2.py -k recipient -v` → `3 passed` — **verified live.**

---

## WHEN ALL VERIFICATIONS PASS

```bash
git commit -m "IMPL-03: RecipientCheck — real thread/contact + reply-all-hazard validator, 3/3 tests passing"
```

---

*Document version: 1.0*
