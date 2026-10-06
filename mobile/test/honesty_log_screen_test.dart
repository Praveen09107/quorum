// Real widget tests for features/honesty_log/honesty_log_screen.dart's
// new `onTapAction` drill-through (`DEC-201`, product rebuild).

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/features/honesty_log/honesty_log_logic.dart';
import 'package:quorum_mobile/features/honesty_log/honesty_log_screen.dart';

final _feed = HonestyFeedData(
  total: 1,
  successRate: 1.0,
  successes: [
    LoggedActionData(actionId: 'p1', timestamp: DateTime(2026, 10, 1), outcome: 'approved_unchanged', description: 'Drafted a real reply', actionType: 'create_task', stakes: 'S1', domain: 'tasks'),
  ],
  failuresAndCatches: [],
  genuinelyUncertain: [],
);

void main() {
  testWidgets('tapping a real logged action calls onTapAction with the real action', (tester) async {
    LoggedActionData? tapped;
    await tester.pumpWidget(MaterialApp(
      home: HonestyLogScreen(feed: _feed, onTapAction: (action) => tapped = action),
    ));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Drafted a real reply'));
    await tester.pumpAndSettle();

    expect(tapped?.actionId, 'p1');
  });

  testWidgets('no chevron and no tap effect on a real logged action when onTapAction is not configured, the honest-gating precedent', (tester) async {
    await tester.pumpWidget(MaterialApp(home: HonestyLogScreen(feed: _feed)));
    await tester.pumpAndSettle();

    // `DEC-205`: the "Full activity timeline" entry point is always
    // real and reachable, with its own real chevron, regardless of
    // `onTapAction` -- that gating is about individual action ROWS,
    // never about whether the Activity screen itself is reachable.
    expect(
      find.descendant(of: find.widgetWithText(ListTile, 'Drafted a real reply'), matching: find.byIcon(Icons.chevron_right)),
      findsNothing,
    );

    await tester.tap(find.text('Drafted a real reply'));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });
}
