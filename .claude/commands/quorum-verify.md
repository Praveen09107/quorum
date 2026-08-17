Run the real Quorum verification suite for whatever this session touched. Report genuine, live output for every applicable step — never state a result without having actually run the command that produces it.

**If this session touched backend code:**
```bash
ruff check backend
```
Report the real output. If it's not clean, this session is not complete per Rule 2 in `CLAUDE.md` — fix it here, don't defer it.

```bash
PYTHONPATH=backend pytest backend/tests -q
```
(If Phase 0's structural migration has been applied, this becomes `pytest backend/tests -q` from inside `backend/`, using the installed `quorum-backend` package instead of `PYTHONPATH` — confirm which state is real before choosing the command, per `/quorum-session-start`'s environment check.)

Report the real pass count. Compare it against what `specs/tier3_verification/STATUS_INDEX.md` currently states. If this session added real tests, the new count should be higher by exactly the number of real new tests added — not "roughly higher." If it's a pure refactor (like a Phase 0 migration step), the count should be identical. Investigate any mismatch before reporting success.

**If this session touched mobile code:**
State plainly that `dart test` and `flutter analyze` need to run on a real machine with a real Flutter/Dart SDK — per `CLAUDE.md`'s "Common commands" note, this has never been possible in the original development sandbox this project was designed in. If a real SDK is available in the current environment, run both and report genuine output. If not, say so explicitly rather than skipping the mention — an unverified mobile change should never be reported as complete without this caveat.

**Always, regardless of what was touched:**
- Confirm `specs/tier3_verification/STATUS_INDEX.md` was updated to reflect this session's real, verified result — not what was planned, what actually happened.
- If this session found or fixed anything worth a future session knowing (a real gap, a stale claim, a genuine design decision), confirm a new entry was appended to `specs/tier3_verification/DECISIONS_LOG.md` — re-view the whole file after editing, per that file's own stated discipline, not just the section you touched.

Report a final summary: what was verified, with real output; what couldn't be verified in this environment and why; and whether `STATUS_INDEX.md`/`DECISIONS_LOG.md` are current as of this session's real result.
