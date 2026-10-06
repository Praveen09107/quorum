// Real widget tests for features/activity/activity_screen.dart
// (`DEC-205`, product rebuild).

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/features/activity/activity_screen.dart';
import 'package:quorum_mobile/features/honesty_log/honesty_log_logic.dart';

LoggedActionData _action({
  required String id,
  required DateTime timestamp,
  String outcome = 'approved_unchanged',
  String stakes = 'S1',
  String? domain = 'tasks',
  String description = 'A real, distinctive action',
}) {
  return LoggedActionData(
    actionId: id, timestamp: timestamp, outcome: outcome, description: description,
    actionType: 'create_task', stakes: stakes, domain: domain,
  );
}

Widget _harness(HonestyFeedData feed, {void Function(LoggedActionData)? onTapAction}) {
  return MaterialApp(home: ActivityScreen(feed: feed, onTapAction: onTapAction));
}

void main() {
  testWidgets('renders every real action across all three buckets, grouped by day', (tester) async {
    final feed = HonestyFeedData(
      total: 2,
      successRate: 1.0,
      successes: [_action(id: 's1', timestamp: DateTime.now(), description: 'A real success')],
      failuresAndCatches: [_action(id: 'f1', timestamp: DateTime.now(), description: 'A real catch')],
      genuinelyUncertain: const [],
    );

    await tester.pumpWidget(_harness(feed));
    await tester.pumpAndSettle();

    expect(find.text('Today'), findsOneWidget);
    expect(find.text('A real success'), findsOneWidget);
    expect(find.text('A real catch'), findsOneWidget);
  });

  testWidgets('an honestly empty feed shows a real, honest empty message', (tester) async {
    const feed = HonestyFeedData(total: 0, successRate: null, successes: [], failuresAndCatches: [], genuinelyUncertain: []);

    await tester.pumpWidget(_harness(feed));
    await tester.pumpAndSettle();

    expect(find.text('Nothing real has happened yet.'), findsOneWidget);
  });

  testWidgets('selecting a real domain filter chip hides non-matching rows', (tester) async {
    final feed = HonestyFeedData(
      total: 2,
      successRate: 1.0,
      successes: [
        _action(id: 's1', timestamp: DateTime.now(), domain: 'tasks', description: 'A real task action'),
        _action(id: 's2', timestamp: DateTime.now(), domain: 'email', description: 'A real email action'),
      ],
      failuresAndCatches: const [],
      genuinelyUncertain: const [],
    );

    await tester.pumpWidget(_harness(feed));
    await tester.pumpAndSettle();

    expect(find.text('A real task action'), findsOneWidget);
    expect(find.text('A real email action'), findsOneWidget);

    await tester.tap(find.text('Email').first);
    await tester.pumpAndSettle();

    expect(find.text('A real email action'), findsOneWidget);
    expect(find.text('A real task action'), findsNothing);
  });

  testWidgets('a real filter combination that matches nothing shows the honest "no match" message', (tester) async {
    final feed = HonestyFeedData(
      total: 1,
      successRate: 1.0,
      successes: [_action(id: 's1', timestamp: DateTime.now(), domain: 'tasks', stakes: 'S1')],
      failuresAndCatches: const [],
      genuinelyUncertain: const [],
    );

    await tester.pumpWidget(_harness(feed));
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('S3'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('S3'));
    await tester.pumpAndSettle();

    expect(find.text('No real activity matches these filters.'), findsOneWidget);
  });

  testWidgets('the clear-filters action reappears real, unfiltered rows', (tester) async {
    final feed = HonestyFeedData(
      total: 1,
      successRate: 1.0,
      successes: [_action(id: 's1', timestamp: DateTime.now(), domain: 'tasks', description: 'A real task action')],
      failuresAndCatches: const [],
      genuinelyUncertain: const [],
    );

    await tester.pumpWidget(_harness(feed));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Email').first);
    await tester.pumpAndSettle();
    expect(find.text('No real activity matches these filters.'), findsOneWidget);

    await tester.tap(find.byIcon(Icons.filter_alt_off_outlined));
    await tester.pumpAndSettle();

    expect(find.text('A real task action'), findsOneWidget);
  });

  testWidgets('tapping a real row calls onTapAction with that real action', (tester) async {
    LoggedActionData? tapped;
    final feed = HonestyFeedData(
      total: 1,
      successRate: 1.0,
      successes: [_action(id: 's1', timestamp: DateTime.now(), description: 'A real tappable action')],
      failuresAndCatches: const [],
      genuinelyUncertain: const [],
    );

    await tester.pumpWidget(_harness(feed, onTapAction: (action) => tapped = action));
    await tester.pumpAndSettle();

    await tester.tap(find.text('A real tappable action'));
    await tester.pumpAndSettle();

    expect(tapped?.actionId, 's1');
  });
}
