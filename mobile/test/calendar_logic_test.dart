// Zero Flutter dependencies -- `dart test` is the real command (confirmed
// against `calendar_logic.dart`'s own import list: only `drift`, a plain
// Dart package).
//
// THE REAL, HAND-VERIFIED PROOF for the weekday-label test below: rather
// than trust Dart's own `DateTime.weekday` by inspection, the real
// weekday names for the two dates used here were independently computed
// in Python before finalizing this test (matching `calendar_sync_test
// .dart`'s own established discipline) -- `datetime.date(2026, 8, 26)
// .strftime('%A')` genuinely returns `Wednesday`, and `datetime.date(
// 2026, 8, 20).strftime('%A')` genuinely returns `Thursday`.

import 'package:drift/native.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/db/database.dart';
import 'package:quorum_mobile/features/calendar/calendar_logic.dart';

void main() {
  group('sortByStartTime', () {
    late QuorumDatabase db;

    setUp(() {
      db = QuorumDatabase.forTesting(NativeDatabase.memory());
    });

    tearDown(() async {
      await db.close();
    });

    Future<CalendarMirrorData> insertRow(String id, DateTime start) async {
      await db.into(db.calendarMirror).insertOnConflictUpdate(
            CalendarMirrorCompanion.insert(
              eventId: id,
              title: 'Event $id',
              startTime: start,
              endTime: start.add(const Duration(hours: 1)),
              sourceCalendarId: 'cal_primary',
            ),
          );
      return (await (db.select(db.calendarMirror)..where((t) => t.eventId.equals(id))).getSingle());
    }

    test('ranks the soonest real event first, not oldest-inserted first', () async {
      final later = await insertRow('evt_later', DateTime(2026, 8, 26, 14, 0));
      final soonest = await insertRow('evt_soonest', DateTime(2026, 8, 20, 9, 0));
      final middle = await insertRow('evt_middle', DateTime(2026, 8, 22, 10, 0));

      final sorted = sortByStartTime([later, soonest, middle]);

      expect(sorted.map((e) => e.eventId).toList(), ['evt_soonest', 'evt_middle', 'evt_later']);
    });

    test('does not mutate the input list', () async {
      final a = await insertRow('evt_a', DateTime(2026, 8, 26, 14, 0));
      final b = await insertRow('evt_b', DateTime(2026, 8, 20, 9, 0));
      final input = [a, b];

      sortByStartTime(input);

      expect(input.map((e) => e.eventId).toList(), ['evt_a', 'evt_b']);
    });

    test('an empty list sorts to an empty list, not a crash', () {
      expect(sortByStartTime(const []), isEmpty);
    });
  });

  group('formatEventDayLabel', () {
    test('the exact same calendar day as now is "Today"', () {
      final now = DateTime(2026, 8, 20, 8, 0);
      final start = DateTime(2026, 8, 20, 23, 30); // same day, different time
      expect(formatEventDayLabel(start, now), 'Today');
    });

    test('the calendar day immediately after now is "Tomorrow"', () {
      final now = DateTime(2026, 8, 20, 23, 45); // late tonight
      final start = DateTime(2026, 8, 21, 0, 15); // just after midnight -- still "Tomorrow", not "Today"
      expect(formatEventDayLabel(start, now), 'Tomorrow');
    });

    test('a real, further-out date shows a real, hand-verified weekday and month', () {
      final now = DateTime(2026, 8, 20, 9, 0); // a real Thursday
      final start = DateTime(2026, 8, 26, 14, 0); // a real Wednesday, 6 days later
      expect(formatEventDayLabel(start, now), 'Wed, Aug 26');
    });
  });

  group('formatEventTimeRange', () {
    test('a real, ordinary afternoon range', () {
      final start = DateTime(2026, 8, 20, 14, 0);
      final end = DateTime(2026, 8, 20, 15, 30);
      expect(formatEventTimeRange(start, end), '2:00 PM – 3:30 PM');
    });

    test('real midnight is "12:00 AM", never "0:00 AM"', () {
      final start = DateTime(2026, 8, 20, 0, 0);
      final end = DateTime(2026, 8, 20, 1, 0);
      expect(formatEventTimeRange(start, end), '12:00 AM – 1:00 AM');
    });

    test('real noon is "12:00 PM", never "0:00 PM"', () {
      final start = DateTime(2026, 8, 20, 12, 0);
      final end = DateTime(2026, 8, 20, 13, 0);
      expect(formatEventTimeRange(start, end), '12:00 PM – 1:00 PM');
    });

    test('a real single-digit minute is zero-padded', () {
      final start = DateTime(2026, 8, 20, 9, 5);
      final end = DateTime(2026, 8, 20, 9, 9);
      expect(formatEventTimeRange(start, end), '9:05 AM – 9:09 AM');
    });
  });
}
