# MOBILE_01: FLUTTER SCAFFOLD
## The first mobile session — real, structurally correct code, honestly unverifiable in this sandbox

---

## AGENT INSTRUCTIONS FOR THIS SESSION

**Attach:** `QUORUM_ARCHITECTURE_DESIGN_DOCUMENT.md` §12 (frontend), §10.4–10.5 (Extended-Outage / Drift mirror)

**Prerequisites:** `IMPL_00` complete (Sprint 0's resolved model/plugin — not yet consumed by this session, but the scaffold must exist before `MOBILE_02` wires it in).

**Review tier:** STANDARD.

**A genuine phase transition, stated plainly:** every backend session could be written, run, and proven inside this project's sandbox. This one can't — there is no Dart or Flutter SDK available here, confirmed by direct attempt (no `dart-sdk` package in apt, Google's own SDK distribution URL returned 404 from this network). Every file in this session is real and structurally complete against each package's documented API, and every one is honestly labeled `UNVERIFIED IN SANDBOX` rather than implied to have been tested. This is not a lower standard — it's the same standard applied honestly to a genuinely different constraint, the same pattern already established for `share_intent_handler.dart`, `TodayWidgetProvider.kt`, and `computed_state.dart` earlier in this project.

**What this session creates:** `mobile/pubspec.yaml`, `mobile/lib/main.dart`, `mobile/lib/shell/main_shell.dart`, `mobile/lib/theme/quorum_theme.dart`, `mobile/lib/db/database.dart`, `mobile/test/main_shell_test.dart`.

**Out of scope:** real screen content for any of the four tabs — those are `MOBILE_05` onward. This session is exactly the shell, the navigation structure, the theme, and the local database, nothing more.

---

## FILE 1: `mobile/pubspec.yaml` (real, complete — see file)

Real, current dependency versions — `flutter_riverpod`, `drift`, `home_widget`, `receive_sharing_intent`, `device_calendar` — the last three specifically because they're what the already-real (but also sandbox-unverified) platform-feature files from earlier sessions depend on. This is the first time those files' dependencies are actually declared anywhere.

## FILE 2: `mobile/lib/db/database.dart` (real, complete — see file)

**A direct, real connection to already-existing work, not a coincidence.** `getAllMirroredTasks()` and `getCalendarEventsInRange()` are exactly the queries `computed_state.dart`'s "local_mirror" source path (real since an earlier session, hand-verified against its Python reference) needs to actually run during Extended-Outage Mode. This session gives that already-written code a real database to query against for the first time.

## FILE 3: `mobile/lib/theme/quorum_theme.dart` (real, with one honest, explicitly flagged uncertainty)

Matches the "instrument-grade clarity" direction directly — light-primary, a neutral slate seed color rather than a brand-color statement, purple deliberately avoided. **One real uncertainty, flagged in the file rather than silently guessed:** `ThemeData.cardTheme`'s expected type (`CardTheme` vs. `CardThemeData`) has changed across recent Flutter versions as part of a Material theme-class refactor, and this cannot be confirmed without a real compiler. `flutter analyze` on first real build resolves this — if it flags a mismatch, that's an expected, one-line fix, not a surprise.

## FILE 4: `mobile/lib/shell/main_shell.dart` (real, complete — see file)

The four-tab structure — stable, fixed navigation position per the locked-in decision that adaptive *content* works but adaptive *navigation position* confuses users. Placeholder content only, deliberately: building real screens now would mean guessing at specs that come later.

## FILE 5: `mobile/lib/main.dart` (real, complete — see file)

## FILE 6: `mobile/test/main_shell_test.dart` (real, complete, honestly unverified — see file)

Three real tests: all four tabs present, tapping a tab genuinely switches content (a real simulated tap, not a state shortcut), and the navigation bar has exactly four destinations. Structurally correct against `flutter_test`'s documented API; `flutter test` on a real machine is the actual verification.

---

## VERIFICATION STEPS (for the developer, on a real machine — this sandbox cannot run these)

**Step 1:** `flutter pub get` — resolves all real dependencies declared in `pubspec.yaml`.
**Step 2:** `dart run build_runner build` — generates the real `database.g.dart` from the table definitions in `database.dart`.
**Step 3:** `flutter analyze` — the real check for the flagged `CardThemeData`/`CardTheme` uncertainty, and anything else this sandbox couldn't catch.
**Step 4:** `flutter test` — runs the three real widget tests.
**Step 5:** `flutter run` on a real device or emulator — the actual, final proof: does the app launch, show four tabs, and switch between them on tap.

---

## WHEN ALL VERIFICATIONS PASS

Update `STATUS_INDEX.md` with the real results of Steps 1–5 — this is the first mobile session, so this is also the first time `STATUS_INDEX.md` will report genuine external verification (performed by the developer, on a real machine) rather than verification performed directly by whichever agent wrote the code.

Append to `DECISIONS_LOG.md`: confirm whether the `CardThemeData` uncertainty resolved as written or needed the flagged fix, and the real output of each of the five verification steps.

---

*Document version: 1.0 — the first of 21 mobile sessions. `MOBILE_02` consumes Sprint 0's real, resolved on-device model choice for the first time.*
