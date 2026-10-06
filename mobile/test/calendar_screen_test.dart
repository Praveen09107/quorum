// Real widget tests for features/calendar/calendar_screen.dart
// (`DEC-209`, product rebuild Part C visual pass -- the glassmorphic
// agent-branded redesign). Covers the three real states this screen
// has always had: no permission, permission granted but genuinely
// empty, and a real, non-empty event list -- the redesign changed the
// widget tree, not the underlying contract.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/db/database.dart';
import 'package:quorum_mobile/features/calendar/calendar_screen.dart';
import 'package:quorum_mobile/theme/quorum_dark_theme.dart';

CalendarMirrorData _event(String title, DateTime startTime) {
  return CalendarMirrorData(
    eventId: 'evt-$title',
    title: title,
    startTime: startTime,
    endTime: startTime.add(const Duration(hours: 1)),
    sourceCalendarId: 'cal_primary',
    lastSyncedAt: startTime,
  );
}

Widget _harness(Widget child) => MaterialApp(theme: buildQuorumDarkTheme(), home: child);

void main() {
  final now = DateTime(2027, 3, 1, 9);

  testWidgets('no permission and no events renders the real, distinct denial message', (tester) async {
    await tester.pumpWidget(_harness(CalendarScreen(events: const [], permissionGranted: false, now: now)));
    await tester.pumpAndSettle();

    expect(find.textContaining('Calendar access not granted'), findsOneWidget);
    expect(find.textContaining('device Settings'), findsOneWidget);
  });

  testWidgets('permission granted but genuinely empty renders a different, honest message', (tester) async {
    await tester.pumpWidget(_harness(CalendarScreen(events: const [], permissionGranted: true, now: now)));
    await tester.pumpAndSettle();

    expect(find.textContaining('No upcoming events'), findsOneWidget);
    expect(find.textContaining('Calendar access not granted'), findsNothing);
  });

  testWidgets('a real, non-empty event list renders the agent header and every real event title', (tester) async {
    final events = [
      _event('Design review', now.add(const Duration(hours: 2))),
      _event('1:1 with manager', now.add(const Duration(days: 1))),
    ];
    await tester.pumpWidget(_harness(CalendarScreen(events: events, permissionGranted: true, now: now)));
    await tester.pumpAndSettle();

    expect(find.text('Calendar'), findsOneWidget);
    expect(find.text('Design review'), findsOneWidget);
    expect(find.text('1:1 with manager'), findsOneWidget);
    expect(find.textContaining('manageable'), findsOneWidget);
  });
}
