// Real tests for features/you/you_preview_logic.dart.
//
// NOTE: `you_preview_logic.dart` imports `db/database.dart` for the real
// `CalendarMirrorData` type, so this file (like `calendar_sync_test.dart`)
// needs `flutter test`, not `dart test`, to even load.

import 'package:flutter_test/flutter_test.dart';

import 'package:quorum_mobile/db/database.dart';
import 'package:quorum_mobile/features/you/you_preview_logic.dart';

CalendarMirrorData _event(DateTime startTime) {
  return CalendarMirrorData(
    eventId: 'evt-${startTime.toIso8601String()}',
    title: 'A real test event',
    startTime: startTime,
    endTime: startTime.add(const Duration(hours: 1)),
    sourceCalendarId: 'cal_primary',
    lastSyncedAt: startTime,
  );
}

void main() {
  group('countEventsWithinDays -- the real half-open window', () {
    test('an event exactly at "now" is counted -- the real inclusive lower bound', () {
      final now = DateTime(2026, 10, 3, 9, 0);
      final events = [_event(now)];
      expect(countEventsWithinDays(events, now, 7), 1);
    });

    test('an event exactly at the upper boundary is excluded -- the real exclusive upper bound', () {
      final now = DateTime(2026, 10, 3, 9, 0);
      final events = [_event(now.add(const Duration(days: 7)))];
      expect(countEventsWithinDays(events, now, 7), 0);
    });

    test('an event one real minute before the upper boundary is counted', () {
      final now = DateTime(2026, 10, 3, 9, 0);
      final events = [_event(now.add(const Duration(days: 7, minutes: -1)))];
      expect(countEventsWithinDays(events, now, 7), 1);
    });

    test('a real past event is excluded', () {
      final now = DateTime(2026, 10, 3, 9, 0);
      final events = [_event(now.subtract(const Duration(days: 1)))];
      expect(countEventsWithinDays(events, now, 7), 0);
    });

    test('a real mix of in-window and out-of-window events counts only the real in-window ones', () {
      final now = DateTime(2026, 10, 3, 9, 0);
      final events = [
        _event(now.add(const Duration(days: 1))),
        _event(now.add(const Duration(days: 3))),
        _event(now.add(const Duration(days: 10))),
        _event(now.subtract(const Duration(days: 2))),
      ];
      expect(countEventsWithinDays(events, now, 7), 2);
    });

    test('an empty real event list counts to zero, not a crash', () {
      expect(countEventsWithinDays(const [], DateTime(2026, 10, 3), 7), 0);
    });
  });

  group('formatCalendarPreview', () {
    test('zero events gets a real, honest, positive message', () {
      expect(formatCalendarPreview(0), 'Nothing scheduled this week');
    });

    test('exactly one event uses the real singular form', () {
      expect(formatCalendarPreview(1), '1 event this week');
    });

    test('multiple events uses the real plural form', () {
      expect(formatCalendarPreview(5), '5 events this week');
    });
  });
}
