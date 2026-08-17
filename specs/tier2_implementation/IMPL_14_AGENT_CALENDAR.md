# IMPL_14: AGENT — CALENDAR
## The second real LangGraph node — and a real architectural boundary made explicit rather than blurred

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §9.2 (Calendar), §14.3 (two-layer authorization)

**Prerequisites:** `IMPL_13`.

**Review tier:** STANDARD.

**A real design decision made explicit, not left implicit — worth reading before the code:** this agent does **not** call `availability_check()` (the real, already-tested Stage A validator from `IMPL_01`) before proposing an event. It would be easy to do — the validator already exists and is real. But doing so would duplicate Stage A's own job and blur the "agents propose, the Gate verifies" separation that's held consistently since the very first review of this architecture. Email's agent doesn't run `CoverageCheck` on its own drafts before proposing them; Calendar's agent shouldn't self-check availability before proposing either. Whether a slot is actually free gets checked once, in one place, by the Gate — not twice, redundantly, by both the agent and the Gate.

**A second real distinction, also made explicit:** Meeting-Load Defense (`meeting_load.py`'s `assess_day_load`, already real) is genuinely different from availability-checking — it's a **proactive** concern (flags an over-scheduled day before any specific event proposal exists), invoked by the scheduling layer, not by this reactive propose-event graph. The two functions answer different questions at different times, which is why neither lives inside the other.

**What this session creates:** `backend/agents/calendar_agent.py`; extends `DOMAIN_TOOL_MAP` in `tool_authorization.py` with Calendar's real tools.

**Out of scope:** the real `CalendarProvider`/Google Calendar API calls themselves — injected/deferred, same pattern as Email's real Gmail calls. Also out of scope: wiring `assess_day_load` into a real scheduled job — that's genuinely a `pg_cron`-triggered session, not this reactive agent's concern, per the design note above.

---

## FILE 1: `backend/agents/calendar_agent.py` (real, complete — see file)

**The core decision this agent exists to make:** local (`CREATE_CALENDAR_EVENT_LOCAL`, S2 — `CalendarProvider` writes it directly, no third-party OAuth) versus external (`CREATE_CALENDAR_EVENT_EXTERNAL`, S3 — needs the real Google Calendar API to actually invite someone outside the system).

**The real proof this decision has the right downstream consequence, not just the right label:** `test_local_event_correctly_routes_to_s2_via_the_real_router` and `test_external_event_correctly_routes_to_s3_via_the_real_router` don't just check the `ActionType` is correct — they run the resulting proposal through `IMPL_09`'s real `get_stakes()` and confirm the actual stakes classification comes out right. This is a genuine integration test between two sessions built weeks apart in the sequence, not two isolated units that happen to agree in prose.

## FILE 2: `tool_authorization.py` (extended — Calendar's real tools added)

**The boundary re-proven, not just extended.** `test_calendar_domain_still_cannot_touch_email_tools` and `test_email_domain_still_cannot_touch_calendar_tools` confirm the authorization boundary is genuinely bidirectional now that a second real domain exists — the first domain's isolation isn't just a coincidence of there being nothing else to confuse it with.

## FILE 3: real tests (8/8 passing — see file for full content)

---

## VERIFICATION STEPS

**Step 1:** `ruff check backend` → Expected: `All checks passed!` — **verified live.**
**Step 2:** `PYTHONPATH=backend pytest backend/tests/test_calendar_agent.py -v` → Expected: `8 passed` — **verified live.**
**Step 3 (whole-suite confirmation):** `PYTHONPATH=backend pytest backend/tests -q` → Expected: **96 passed** (88 prior + 8 new) — **verified live.**

---

## WHEN ALL VERIFICATIONS PASS

```bash
git add -A
git commit -m "IMPL-14: Agent — Calendar. Second real LangGraph node. Explicit architectural boundary: availability-checking stays in the Gate, not duplicated in the agent. Real integration proof against IMPL_09's router. 8/8 tests passing, 96/96 total suite."
```

**Update `STATUS_INDEX.md`** — Calendar agent moves to real; note the growing `DOMAIN_TOOL_MAP` now covers two domains, both cross-checked against each other.

**Append to `DECISIONS_LOG.md`:** the availability-check boundary decision, stated plainly enough that `IMPL_15`–`IMPL_17` (the remaining domain agents) don't have to re-derive the same reasoning independently.

---

*Document version: 1.0 — the boundary decision here applies equally to Tasks (`DeadlineConflictCheck`), Finance (`BudgetCheck`), and Career going forward: none of them should self-verify before proposing either.*
