// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against `home_widget` ^0.6.0's
// documented API surface; `flutter analyze` on a real machine is the
// actual verification.
//
// A SIGNIFICANT, DISCLOSED DISCREPANCY: this file does not exist
// anywhere in this repository's real history before this session — see
// `mobile/lib/features/share_intent_logic.dart`'s header comment for the
// full, shared disclosure (neither this bridge nor `share_intent_
// handler.dart` was ever built here before now, despite both being
// referenced as if they already existed).
//
// Real, minimal wrapper -- writes the already-computed Today numbers
// (from `computed_state.dart`, proven identical for live and local-
// mirror sources since `MOBILE_06`) to real, native widget storage, then
// asks the OS to redraw the home-screen widget. This bridge never
// computes anything itself -- it only relays real, already-correct
// numbers outward.
//
// `TodayWidgetProvider` is the real, named Android widget provider class
// this bridge targets -- the native (Kotlin) counterpart is out of
// scope for this Dart-side session, same injected/external-boundary
// pattern as every other real platform integration in this project.

import 'dart:developer' as developer;

import 'package:home_widget/home_widget.dart';

class TodayWidgetBridge {
  static const String _androidWidgetName = 'TodayWidgetProvider';

  /// Real, already-computed numbers relayed to the native widget layer.
  /// Never recomputes anything -- the caller (holding_steady_zone.dart)
  /// is responsible for passing real, already-correct values.
  ///
  /// RESOLVED, a real, disclosed bug found live on a real device for the
  /// first time this file was ever actually run (`QUORUM_FINAL_
  /// COMPLETION_PLAN.md`'s own whole-system checkpoint, first genuine
  /// on-device session since `DEC-171`): this file's own header comment
  /// already, correctly disclosed that the native Android `AppWidget
  /// Provider` counterpart was out of scope when this bridge was
  /// written -- confirmed, by direct search, still genuinely absent from
  /// `android/app/src/main/AndroidManifest.xml` and the whole Android
  /// project (no `<receiver>`, no provider class, no widget layout XML).
  /// What was NOT disclosed, and only became visible on a real device,
  /// is what happens when `HomeWidget.updateWidget()` is called against
  /// a real, missing native provider: a real, live `PlatformException`
  /// (`ClassNotFoundException` for `TodayWidgetProvider`), unhandled,
  /// fired from `holding_steady_zone.dart`'s own real `initState`/
  /// `didUpdateWidget` calls -- meaning every real view of the Today
  /// screen logged an unhandled exception, not a graceful no-op, for a
  /// feature this project has always, correctly treated as a real,
  /// separate, deferred scope boundary. Caught here, at the bridge
  /// itself (not each call site, so any future real caller inherits the
  /// same graceful behavior): a missing native counterpart is an
  /// EXPECTED, not exceptional, real state until a future session
  /// actually builds the native widget provider -- logged for real
  /// visibility during development, never surfaced to the user or left
  /// as an unhandled exception in production.
  static Future<void> updateWidget({
    required double hoursRemainingToday,
    required double budgetRemainingFraction,
  }) async {
    try {
      await HomeWidget.saveWidgetData<double>('hoursRemainingToday', hoursRemainingToday);
      await HomeWidget.saveWidgetData<double>('budgetRemainingFraction', budgetRemainingFraction);
      await HomeWidget.updateWidget(androidName: _androidWidgetName);
    } catch (e) {
      // A real, expected failure mode until the native `TodayWidgetProvider`
      // is actually built (a real, disclosed, separate scope item) --
      // never rethrown, never surfaced to the user.
      developer.log('TodayWidgetBridge.updateWidget failed (native widget provider not yet built): $e', name: 'TodayWidgetBridge');
    }
  }
}
