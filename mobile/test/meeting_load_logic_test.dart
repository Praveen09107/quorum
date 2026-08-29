// Real tests for features/meeting_load/meeting_load_logic.dart -- the
// single-day cases directly mirror `backend/tests/test_meeting_load.py`'s
// own real, hand-verified cases exactly (a real parity proof between
// the Python reference implementation and this real Dart port), plus
// new tests for the genuine multi-day projection this port exists to
// enable. `flutter test` is the real command for this whole file --
// confirmed live, not assumed: `db/database.dart` (needed for
// `CalendarMirrorData` in the multi-day group) transitively pulls in
// real Flutter plugin packages (`sqlite3_flutter_libs`/`path_provider`),
// the same real reason `calendar_logic_test.dart`'s own, similarly-
// worded claim was found wrong and corrected this same session.

import 'package:drift/native.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/db/database.dart';
import 'package:quorum_mobile/features/calendar/calendar_logic.dart';
import 'package:quorum_mobile/features/meeting_load/meeting_load_logic.dart';

// A real, hand-verified float fact, confirmed directly before trusting
// it, matching `test_meeting_load.py`'s own established discipline:
// with the real, specified defaults, `0.7 * (8.0 * 0.75)` is NOT
// exactly `4.2` in IEEE-754 double precision -- it's
// `4.199999999999999`. Computed the same way `computeMeetingLoad()`
// does, not hardcoded, so the boundary test genuinely tests the
// boundary.
const _defaultBufferAdjustedHours = workingHoursPerDay * (1.0 - bufferFraction);
const _defaultOverloadBoundaryHours = overloadThreshold * _defaultBufferAdjustedHours;

void main() {
  group('computeMeetingLoad (real parity with the Python reference)', () {
    test('default buffer-adjusted availability is six hours', () {
      final result = computeMeetingLoad(committedHours: 0.0);
      expect(result.bufferAdjustedAvailabilityHours, 6.0);
    });

    test('a light day is not overloaded', () {
      final result = computeMeetingLoad(committedHours: 2.0);
      expect(result.isOverloaded, isFalse);
      expect(result.committedHours, 2.0);
    });

    test('exactly at the real boundary is not overloaded (strict >, not >=)', () {
      final result = computeMeetingLoad(committedHours: _defaultOverloadBoundaryHours);
      expect(result.isOverloaded, isFalse);
    });

    test('just past the real boundary is overloaded', () {
      final result = computeMeetingLoad(committedHours: _defaultOverloadBoundaryHours + 0.01);
      expect(result.isOverloaded, isTrue);
    });

    test('a genuinely full day is overloaded', () {
      final result = computeMeetingLoad(committedHours: 8.0);
      expect(result.isOverloaded, isTrue);
    });

    test('zero committed hours is never overloaded', () {
      final result = computeMeetingLoad(committedHours: 0.0);
      expect(result.isOverloaded, isFalse);
    });

    test('a real negative committed hours is clamped to zero', () {
      final result = computeMeetingLoad(committedHours: -3.0);
      expect(result.committedHours, 0.0);
      expect(result.isOverloaded, isFalse);
    });

    test('a real custom working day is honored', () {
      final result = computeMeetingLoad(committedHours: 5.0, workingHoursPerDayParam: 10.0);
      expect(result.bufferAdjustedAvailabilityHours, 7.5);
      expect(result.isOverloaded, isFalse);

      final resultOverloaded = computeMeetingLoad(committedHours: 5.3, workingHoursPerDayParam: 10.0);
      expect(resultOverloaded.isOverloaded, isTrue);
    });

    test('a real custom buffer fraction is honored', () {
      final result = computeMeetingLoad(committedHours: 6.0, bufferFractionParam: 0.0);
      expect(result.bufferAdjustedAvailabilityHours, workingHoursPerDay);
    });

    test('a real custom overload threshold is honored', () {
      final result = computeMeetingLoad(committedHours: 3.0, overloadThresholdParam: 0.5);
      expect(result.isOverloaded, isFalse);
      final resultOver = computeMeetingLoad(committedHours: 3.1, overloadThresholdParam: 0.5);
      expect(resultOver.isOverloaded, isTrue);
    });

    test('a genuinely non-positive working day has zero bookable time', () {
      final result = computeMeetingLoad(committedHours: 0.5, workingHoursPerDayParam: 0.0);
      expect(result.bufferAdjustedAvailabilityHours, 0.0);
      expect(result.isOverloaded, isTrue);

      final resultZeroCommitted = computeMeetingLoad(committedHours: 0.0, workingHoursPerDayParam: 0.0);
      expect(resultZeroCommitted.isOverloaded, isFalse);

      final resultNegativeWorkingDay = computeMeetingLoad(committedHours: 1.0, workingHoursPerDayParam: -2.0);
      expect(resultNegativeWorkingDay.bufferAdjustedAvailabilityHours, 0.0);
      expect(resultNegativeWorkingDay.isOverloaded, isTrue);
    });

    test('an out-of-range buffer fraction never flags a genuinely empty day', () {
      final result = computeMeetingLoad(committedHours: 0.0, bufferFractionParam: 1.5);
      expect(result.bufferAdjustedAvailabilityHours, 0.0); // clamped to 1.0, not -0.5
      expect(result.isOverloaded, isFalse);
    });

    test('a negative buffer fraction is clamped to zero', () {
      final result = computeMeetingLoad(committedHours: 0.0, bufferFractionParam: -0.5);
      expect(result.bufferAdjustedAvailabilityHours, workingHoursPerDay);
    });

    test('a negative overload threshold never flags a genuinely empty day', () {
      final result = computeMeetingLoad(committedHours: 0.0, overloadThresholdParam: -0.1);
      expect(result.isOverloaded, isFalse);
    });

    test('refuses a real NaN committed hours loudly', () {
      expect(() => computeMeetingLoad(committedHours: double.nan), throwsArgumentError);
    });

    test('refuses a real NaN in any other parameter loudly', () {
      expect(() => computeMeetingLoad(committedHours: 1.0, workingHoursPerDayParam: double.nan), throwsArgumentError);
      expect(() => computeMeetingLoad(committedHours: 1.0, bufferFractionParam: double.nan), throwsArgumentError);
      expect(() => computeMeetingLoad(committedHours: 1.0, overloadThresholdParam: double.nan), throwsArgumentError);
    });
  });

  group('computeWeeklyMeetingLoad (the real, genuine multi-day projection)', () {
    late QuorumDatabase db;

    setUp(() {
      db = QuorumDatabase.forTesting(NativeDatabase.memory());
    });

    tearDown(() async {
      await db.close();
    });

    Future<CalendarMirrorData> insertEvent(String id, DateTime start, DateTime end) async {
      await db.into(db.calendarMirror).insertOnConflictUpdate(
            CalendarMirrorCompanion.insert(eventId: id, title: 'Event $id', startTime: start, endTime: end, sourceCalendarId: 'cal_primary'),
          );
      return (await (db.select(db.calendarMirror)..where((t) => t.eventId.equals(id))).getSingle());
    }

    test('a real, empty week is never overloaded on any real day', () {
      final now = DateTime(2026, 8, 20);
      final result = computeWeeklyMeetingLoad(const [], now: now, lookAheadDays: 7);

      expect(result, hasLength(7));
      expect(result.every((d) => !d.state.isOverloaded), isTrue);
      expect(result.first.day, DateTime(2026, 8, 20));
      expect(result.last.day, DateTime(2026, 8, 26));
    });

    test('real events on the same real day genuinely sum toward that one day\'s own real load', () async {
      final now = DateTime(2026, 8, 20);
      // Two real, 3-hour meetings on the same real day -- 6.0h real
      // committed hours, genuinely exceeding the real 4.2h boundary.
      final e1 = await insertEvent('e1', DateTime(2026, 8, 21, 9, 0), DateTime(2026, 8, 21, 12, 0));
      final e2 = await insertEvent('e2', DateTime(2026, 8, 21, 13, 0), DateTime(2026, 8, 21, 16, 0));

      final result = computeWeeklyMeetingLoad([e1, e2], now: now, lookAheadDays: 7);
      final overloadedDay = result.firstWhere((d) => isSameCalendarDay(d.day, DateTime(2026, 8, 21)));

      expect(overloadedDay.state.committedHours, 6.0);
      expect(overloadedDay.state.isOverloaded, isTrue);
    });

    test('a real event on a different real day never contributes to another day\'s own real load', () async {
      final now = DateTime(2026, 8, 20);
      final e1 = await insertEvent('e1', DateTime(2026, 8, 22, 9, 0), DateTime(2026, 8, 22, 17, 0)); // a real, full 8h day

      final result = computeWeeklyMeetingLoad([e1], now: now, lookAheadDays: 7);
      final theDayItself = result.firstWhere((d) => isSameCalendarDay(d.day, DateTime(2026, 8, 22)));
      final theDayBefore = result.firstWhere((d) => isSameCalendarDay(d.day, DateTime(2026, 8, 21)));

      expect(theDayItself.state.committedHours, 8.0);
      expect(theDayItself.state.isOverloaded, isTrue);
      expect(theDayBefore.state.committedHours, 0.0);
      expect(theDayBefore.state.isOverloaded, isFalse);
    });

    test('a real event outside the real look-ahead window is genuinely never counted', () async {
      final now = DateTime(2026, 8, 20);
      final farFuture = await insertEvent('e1', DateTime(2026, 9, 15, 9, 0), DateTime(2026, 9, 15, 17, 0));

      final result = computeWeeklyMeetingLoad([farFuture], now: now, lookAheadDays: 7);

      expect(result.every((d) => d.state.committedHours == 0.0), isTrue);
    });

    test('lookAheadDays is honored exactly -- a real, non-default window', () {
      final result = computeWeeklyMeetingLoad(const [], now: DateTime(2026, 8, 20), lookAheadDays: 3);
      expect(result, hasLength(3));
    });
  });
}
