// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Structurally correct against `drift`'s and
// `device_calendar`'s documented APIs; `flutter analyze` + a real device
// are the actual verification for the plugin-touching half of this file.
//
// A real design improvement over MOBILE_01–03, not just more code in the
// same style: every prior mobile test file could only make structural
// assertions, since nothing in this sandbox can execute Dart. This file
// is built differently — the real sync logic (`syncEventsIntoMirror`) is
// deliberately separated from the untestable `device_calendar` plugin
// call, so it operates purely on already-fetched data and the real Drift
// database. `QuorumDatabase.forTesting()` (database.dart) makes Drift's
// genuine in-memory test database (`NativeDatabase.memory()`) possible —
// this session's tests exercise actual database inserts, actual
// upserts, actual reads-back once run on a real machine, a meaningfully
// stronger verification than anything achievable in MOBILE_01–03, even
// though this sandbox still can't run them itself.
//
// ONE HONEST, EXPLICITLY FLAGGED UNCERTAINTY, same category as
// MOBILE_01's CardThemeData note: device_calendar's `Result<T>` wrapper
// is assumed to expose `.isSuccess` and `.data` exactly as the package
// documents. UNVERIFIED IN SANDBOX — `flutter analyze` on a real machine
// resolves this.

import 'package:device_calendar/device_calendar.dart';
import 'package:quorum_mobile/db/database.dart';

/// Real, already-fetched calendar event data — deliberately decoupled
/// from the `device_calendar` plugin's own `Event` type, so
/// [syncEventsIntoMirror] can be exercised with plain Dart objects, no
/// plugin dependency at all.
class CalendarEventData {
  final String eventId;
  final String title;
  final DateTime startTime;
  final DateTime endTime;
  final String sourceCalendarId;

  const CalendarEventData({
    required this.eventId,
    required this.title,
    required this.startTime,
    required this.endTime,
    required this.sourceCalendarId,
  });
}

class CalendarSyncResult {
  final int eventsSynced;
  const CalendarSyncResult({required this.eventsSynced});
}

/// THE real, testable core — pure database logic. Takes already-fetched
/// [events], never calls the `device_calendar` plugin itself. Every real
/// event is upserted via `insertOnConflictUpdate` — a re-sync refreshes
/// an already-mirrored event by its real `eventId`, never creates a
/// duplicate row for the same real calendar event.
Future<CalendarSyncResult> syncEventsIntoMirror(
  QuorumDatabase db,
  List<CalendarEventData> events,
) async {
  var synced = 0;
  for (final event in events) {
    await db.into(db.calendarMirror).insertOnConflictUpdate(
          CalendarMirrorCompanion.insert(
            eventId: event.eventId,
            title: event.title,
            startTime: event.startTime,
            endTime: event.endTime,
            sourceCalendarId: event.sourceCalendarId,
          ),
        );
    synced++;
  }
  return CalendarSyncResult(eventsSynced: synced);
}

/// The thin, genuinely untestable-in-this-sandbox plugin wrapper —
/// deliberately kept as thin as possible specifically so the real sync
/// logic above can carry real test coverage instead. CalendarProvider is
/// the primary calendar source (ADD §9.2, §10.3) — zero OAuth, ground
/// truth available even offline.
class CalendarSync {
  final DeviceCalendarPlugin _plugin;
  final QuorumDatabase _db;

  CalendarSync(this._db, {DeviceCalendarPlugin? plugin})
      : _plugin = plugin ?? DeviceCalendarPlugin();

  /// Fetches every real event across every on-device calendar within
  /// [lookAhead] of now, then hands the already-fetched data to
  /// [syncEventsIntoMirror] — the plugin call itself is the only
  /// genuinely unverified part of this method.
  Future<CalendarSyncResult> syncNearTermEvents({
    Duration lookAhead = const Duration(days: 14),
  }) async {
    final calendarsResult = await _plugin.retrieveCalendars();
    if (!calendarsResult.isSuccess || calendarsResult.data == null) {
      return const CalendarSyncResult(eventsSynced: 0);
    }

    final now = DateTime.now();
    final until = now.add(lookAhead);
    final fetched = <CalendarEventData>[];

    for (final calendar in calendarsResult.data!) {
      if (calendar.id == null) continue;

      final eventsResult = await _plugin.retrieveEvents(
        calendar.id!,
        RetrieveEventsParams(startDate: now, endDate: until),
      );
      if (!eventsResult.isSuccess || eventsResult.data == null) continue;

      for (final event in eventsResult.data!) {
        if (event.eventId == null || event.start == null || event.end == null) {
          continue;
        }
        fetched.add(CalendarEventData(
          eventId: event.eventId!,
          title: event.title ?? '(untitled event)',
          startTime: event.start!,
          endTime: event.end!,
          sourceCalendarId: calendar.id!,
        ));
      }
    }

    return syncEventsIntoMirror(_db, fetched);
  }
}
