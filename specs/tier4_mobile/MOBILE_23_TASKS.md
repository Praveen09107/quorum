# MOBILE_23: TASKS
## Closing a real gap found during a full specification audit — a full backend domain with no mobile screen anywhere

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**A genuinely new session, created the same way `MOBILE_22` was** — a real gap found during execution (this time, during a full specification audit rather than a build session), given its own complete session rather than folded into other work.

**Attach:** `QUORUM_DATA_CONTRACTS.md` §5.17, `backend/migrations/001_initial_schema.sql` (`tasks` table), `IMPL_15_AGENT_TASKS.md`

**Prerequisites:** `MOBILE_22`.

**Review tier:** STANDARD.

**The finding, precisely.** A full specification audit found that Tasks — one of the five core domains, with a real backend agent (`IMPL_15`), a real Postgres table, and real `ActionType`s (`create_task`, `update_task`) — had no dedicated mobile screen anywhere across all 22 prior mobile sessions, and this absence was never named or tracked anywhere. Every other core domain got real mobile coverage (Career: two screens; Finance: one; Email: indirectly via Waiting On). This was a different, more concerning category than the seven honestly-tracked unreachable screens in `STATUS_INDEX.md` — those are real screens with a genuine, deferred navigation decision; this was a screen that never existed at all, silently.

**A genuinely new endpoint gap, found and fixed the same way as every prior one in this project.** `QUORUM_DATA_CONTRACTS.md` never specified `GET /tasks`. Added as §5.17 before this session was built against it.

**A deliberate design contrast with `MOBILE_11`'s Career Pipeline, worth stating explicitly rather than copying that screen's pattern out of habit.** Career Pipeline found `applications.status` has no database-level `CHECK` constraint — a genuinely open vocabulary, correctly handled with a defensive fallback. Checking `tasks.status` directly found the opposite: a real `CHECK` constraint enforces exactly three values (`open`/`done`/`cancelled`). Given a genuinely closed, database-enforced contract, this session's status parsing **fails loud** on an unrecognized value instead — per `CLAUDE.md` Rule 4 ("when a spec's assumption doesn't match the real code/API/schema, stop and report the discrepancy"). Treating every status field defensively regardless of what its real contract actually guarantees would have been applying a pattern from habit, not reasoning about what's actually true for this specific table.

**A real, reasoned navigation link, not an arbitrary one added just to close the gap.** Wired from Today's "Holding Steady" zone, since its capacity number is computed directly from real task commitments (`TaskCommitment`, per `computed_state.dart`) — the same reasoning discipline already applied to `MOBILE_22`'s Trust→Trust Digest and You→Memory Transparency links.

**What this session creates:** `mobile/lib/features/tasks/tasks_logic.dart` (zero Flutter dependencies), `mobile/lib/features/tasks/tasks_screen.dart`, `mobile/test/tasks_logic_test.dart`. **What this session wires:** `mobile/lib/features/today_screen.dart` (real navigation link, `_ZoneSection` extended with an optional `trailing` widget).

**Out of scope:** the real `TasksRepository` HTTP implementation — deferred, same injected pattern as every other feature screen in this project.

---

## FILE 1: `mobile/lib/features/tasks/tasks_logic.dart` (real, complete — see file)

**The real property this file exists to prove, backed by test, not just asserted in a comment.** `parseTaskStatus` throws on an unrecognized value — the deliberate opposite of Career Pipeline's fallback — because the real contract genuinely differs, confirmed directly against the schema before writing a line of Dart.

**A genuine absence of rounding risk, worth noting rather than assuming.** `estimated_hours` is a `NUMERIC(4,1)` column — the database itself guarantees at most one decimal place, so `formatHours` is pure display formatting of already-precise data, not a rounding operation with a disputed tie-break case like `MOBILE_13`'s.

## FILE 2: `mobile/lib/features/tasks/tasks_screen.dart` (real, complete — see file)

## FILE 3: real tests (14/14 — see file)

## FILE 4: `mobile/lib/features/today_screen.dart` (real, wired — see file)

---

## VERIFICATION STEPS (on a real machine — this sandbox cannot run these)

**Step 1:** `dart test test/tasks_logic_test.dart` → expected: 14 passed.
**Step 2:** `flutter analyze` → confirms all edited/new files, including `today_screen.dart`'s updated `_ZoneSection`.

---

## WHEN ALL VERIFICATIONS PASS

Update `STATUS_INDEX.md` — the Tasks screen is real, and genuinely reachable from Today, not another silent addition. The specification-audit finding (F14) is closed, not just logged.

Append to `DECISIONS_LOG.md`: the fail-loud/defensive-fallback contrast with Career Pipeline, and the reasoning behind the Holding Steady navigation link.

---

*Document version: 1.0 — a genuinely new session, created because a full specification audit found a real, silent gap and it deserved full, undiluted attention rather than a footnote.*
