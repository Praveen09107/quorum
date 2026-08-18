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

import 'package:home_widget/home_widget.dart';

class TodayWidgetBridge {
  static const String _androidWidgetName = 'TodayWidgetProvider';

  /// Real, already-computed numbers relayed to the native widget layer.
  /// Never recomputes anything -- the caller (holding_steady_zone.dart)
  /// is responsible for passing real, already-correct values.
  static Future<void> updateWidget({
    required double hoursRemainingToday,
    required double budgetRemainingFraction,
  }) async {
    await HomeWidget.saveWidgetData<double>('hoursRemainingToday', hoursRemainingToday);
    await HomeWidget.saveWidgetData<double>('budgetRemainingFraction', budgetRemainingFraction);
    await HomeWidget.updateWidget(androidName: _androidWidgetName);
  }
}
