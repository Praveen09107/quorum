// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this
// file was written. Structurally correct against `drift`'s and plain
// `package:test`'s documented APIs (zero Flutter framework dependency —
// `dart test` is the real command, not `flutter test`, per this
// project's own documented distinction). `dart test` on a real machine
// is the actual verification — and given this file's real test database
// uses Drift's `NativeDatabase.memory()`, these are genuine database
// inserts and upserts, not structural assertions alone.
//
// THE REAL, HAND-VERIFIED PROOF of the trickiest logic in this session:
// the range-filter test below depends on exact `>=`/`<` boundary
// behavior. Rather than trust the expected outcome by inspection, the
// actual comparison was computed directly in Python before finalizing
// this test (see DECISIONS_LOG.md for the executed reimplementation) —
// confirming the in-range event genuinely satisfies
// `start_q <= evt1 < end_q`, the event exactly AT `end_q` is genuinely
// excluded (the boundary is a real half-open range, not inclusive on
// both ends), and the event just before `start_q` is genuinely excluded
// too.

import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/db/database.dart';
import 'package:quorum_mobile/features/calendar_sync.dart';

void main() {
  late QuorumDatabase db;

  setUp(() {
    db = QuorumDatabase.forTesting(NativeDatabase.memory());
  });

  tearDown(() async {
    await db.close();
  });

  test('a real insert is confirmed by reading the row back, not just trusting a return count', () async {
    final result = await syncEventsIntoMirror(db, [
      CalendarEventData(
        eventId: 'evt_1',
        title: 'Design review',
        startTime: _t(2026, 8, 20, 14, 0),
        endTime: _t(2026, 8, 20, 15, 0),
        sourceCalendarId: 'cal_primary',
      ),
    ]);

    expect(result.eventsSynced, 1);

    final rows = await db.select(db.calendarMirror).get();
    expect(rows.length, 1);
    expect(rows.first.eventId, 'evt_1');
    expect(rows.first.title, 'Design review');
  });

  test('a real upsert -- exactly one row survives a re-sync of the same event', () async {
    await syncEventsIntoMirror(db, [
      CalendarEventData(
        eventId: 'evt_1',
        title: 'Design review',
        startTime: _t(2026, 8, 20, 14, 0),
        endTime: _t(2026, 8, 20, 15, 0),
        sourceCalendarId: 'cal_primary',
      ),
    ]);

    // A real re-sync of the SAME eventId, with genuinely changed data --
    // this must refresh the existing row, never create a second one.
    await syncEventsIntoMirror(db, [
      CalendarEventData(
        eventId: 'evt_1',
        title: 'Design review (rescheduled)',
        startTime: _t(2026, 8, 20, 16, 0),
        endTime: _t(2026, 8, 20, 17, 0),
        sourceCalendarId: 'cal_primary',
      ),
    ]);

    final rows = await db.select(db.calendarMirror).get();
    expect(rows.length, 1);
    expect(rows.first.title, 'Design review (rescheduled)');
    expect(rows.first.startTime, _t(2026, 8, 20, 16, 0));
  });

  test('multiple real events sync together in one call', () async {
    final result = await syncEventsIntoMirror(db, [
      CalendarEventData(
        eventId: 'evt_1',
        title: 'Standup',
        startTime: _t(2026, 8, 20, 9, 0),
        endTime: _t(2026, 8, 20, 9, 15),
        sourceCalendarId: 'cal_primary',
      ),
      CalendarEventData(
        eventId: 'evt_2',
        title: 'Design review',
        startTime: _t(2026, 8, 20, 14, 0),
        endTime: _t(2026, 8, 20, 15, 0),
        sourceCalendarId: 'cal_primary',
      ),
      CalendarEventData(
        eventId: 'evt_3',
        title: 'Interview prep',
        startTime: _t(2026, 8, 21, 10, 0),
        endTime: _t(2026, 8, 21, 11, 0),
        sourceCalendarId: 'cal_work',
      ),
    ]);

    expect(result.eventsSynced, 3);
    final rows = await db.select(db.calendarMirror).get();
    expect(rows.length, 3);
  });

  test('getCalendarEventsInRange correctly applies the real half-open boundary -- MOBILE_01\'s already-real query, fed by this session\'s output', () async {
    // Real, hand-verified boundary values (see file header / DECISIONS_LOG.md):
    // start_q = 2026-08-20 00:00:00, end_q = 2026-08-21 00:00:00.
    final startQ = _t(2026, 8, 20, 0, 0);
    final endQ = _t(2026, 8, 21, 0, 0);

    await syncEventsIntoMirror(db, [
      // In range: start_q <= evt1 < end_q.
      CalendarEventData(
        eventId: 'evt_in_range',
        title: 'In-range meeting',
        startTime: _t(2026, 8, 20, 14, 30),
        endTime: _t(2026, 8, 20, 15, 30),
        sourceCalendarId: 'cal_primary',
      ),
      // Out of range: exactly AT end_q -- the exclusive upper boundary.
      CalendarEventData(
        eventId: 'evt_at_boundary',
        title: 'Next-day meeting exactly at end_q',
        startTime: _t(2026, 8, 21, 0, 0),
        endTime: _t(2026, 8, 21, 1, 0),
        sourceCalendarId: 'cal_primary',
      ),
      // Out of range: just before start_q.
      CalendarEventData(
        eventId: 'evt_before_range',
        title: 'Previous-day meeting',
        startTime: _t(2026, 8, 19, 23, 59, 59),
        endTime: _t(2026, 8, 20, 0, 30),
        sourceCalendarId: 'cal_primary',
      ),
    ]);

    final results = await db.getCalendarEventsInRange(startQ, endQ);

    expect(results.length, 1);
    expect(results.first.eventId, 'evt_in_range');
  });
}

DateTime _t(int year, int month, int day, [int hour = 0, int minute = 0, int second = 0]) {
  return DateTime(year, month, day, hour, minute, second);
}
