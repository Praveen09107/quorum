// RESOLVED, real correction (`DEC-152`): this file was previously a real,
// zero-Flutter-dependency file, run via plain `dart test`. It no longer
// is -- confirmed directly, not assumed: `device_calendar` (imported
// below, needed for this session's own `_FakeCalendarPlugin`) transitively
// imports `package:flutter/material.dart`, which the standalone Dart SDK
// genuinely cannot compile (`dart test` fails to even LOAD this file with
// real Dart-SDK-vs-Flutter-SDK type errors, confirmed live). `flutter
// test` is the real command for this file now -- confirmed it loads and
// passes cleanly there instead. `pubspec.yaml`'s own dev_dependencies
// comment is corrected in the same session to stop naming this file
// among the zero-Flutter-dependency set.
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

import 'dart:collection';

import 'package:device_calendar/device_calendar.dart';
import 'package:drift/native.dart';
import 'package:test/test.dart';

import 'package:quorum_mobile/db/database.dart';
import 'package:quorum_mobile/features/calendar_sync.dart';

/// A real, hand-built double for `DeviceCalendarPlugin` -- this project
/// uses no mocking library anywhere (matching the backend's own
/// `_FakePostClient` convention, `test_action_executor.py`), so this
/// extends the real plugin class directly and overrides only the real
/// methods `syncNearTermEvents()` actually calls. `DeviceCalendarPlugin
/// .private()` is real, generative, and explicitly `@visibleForTesting`
/// -- calling it from outside the package is the documented, intended
/// use of that annotation, not a workaround.
class _FakeCalendarPlugin extends DeviceCalendarPlugin {
  _FakeCalendarPlugin({required this.permissionsAlreadyGranted, this.grantsOnRequest = false}) : super.private();

  final bool permissionsAlreadyGranted;
  final bool grantsOnRequest;
  bool requestPermissionsCalled = false;
  bool retrieveCalendarsCalled = false;

  @override
  Future<Result<bool>> hasPermissions() async {
    return Result<bool>()..data = permissionsAlreadyGranted;
  }

  @override
  Future<Result<bool>> requestPermissions() async {
    requestPermissionsCalled = true;
    return Result<bool>()..data = grantsOnRequest;
  }

  @override
  Future<Result<UnmodifiableListView<Calendar>>> retrieveCalendars() async {
    retrieveCalendarsCalled = true;
    return Result<UnmodifiableListView<Calendar>>()..data = UnmodifiableListView<Calendar>(const []);
  }
}

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
    expect(result.permissionGranted, true);

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

  group('CalendarSync.syncNearTermEvents real permission handling (DEC-152)', () {
    test('permission already granted -- never calls requestPermissions, proceeds to sync', () async {
      final plugin = _FakeCalendarPlugin(permissionsAlreadyGranted: true);
      final sync = CalendarSync(db, plugin: plugin);

      final result = await sync.syncNearTermEvents();

      expect(result.permissionGranted, true);
      expect(result.eventsSynced, 0); // the fake's retrieveCalendars returns an empty list
      expect(plugin.requestPermissionsCalled, false);
      expect(plugin.retrieveCalendarsCalled, true);
    });

    test('permission not yet granted but genuinely granted on request -- proceeds to sync', () async {
      final plugin = _FakeCalendarPlugin(permissionsAlreadyGranted: false, grantsOnRequest: true);
      final sync = CalendarSync(db, plugin: plugin);

      final result = await sync.syncNearTermEvents();

      expect(result.permissionGranted, true);
      expect(plugin.requestPermissionsCalled, true);
      expect(plugin.retrieveCalendarsCalled, true);
    });

    test('permission genuinely denied, even after requesting -- refuses before any real calendar read', () async {
      // A real, disclosed fix this session's own review of the pre-existing
      // code found: `Result<bool>.isSuccess` is true even when `data` is
      // `false` (a real, non-null, denied answer) -- this test would pass
      // on a naive `if (result.isSuccess)` check even though permission was
      // genuinely denied, which is exactly the bug this test exists to
      // catch.
      final plugin = _FakeCalendarPlugin(permissionsAlreadyGranted: false, grantsOnRequest: false);
      final sync = CalendarSync(db, plugin: plugin);

      final result = await sync.syncNearTermEvents();

      expect(result.permissionGranted, false);
      expect(result.eventsSynced, 0);
      expect(plugin.requestPermissionsCalled, true);
      expect(plugin.retrieveCalendarsCalled, false); // genuinely never reached a real calendar read
    });
  });
}

DateTime _t(int year, int month, int day, [int hour = 0, int minute = 0, int second = 0]) {
  return DateTime(year, month, day, hour, minute, second);
}
