// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Zero Flutter dependencies — plain Dart, `dart test` is
// the real verification.
//
// REAL, NEW (the redesign's own real You-tab promotion work) -- closes
// the approved redesign plan's own named gap: "'You' stops being a flat
// settings list. Career Pipeline, Finance, Calendar, Search, Waiting On
// get real, visually distinct preview cards... showing one live real
// number... not generic grey ListTile rows with identical icons."

import 'package:quorum_mobile/db/database.dart';

/// Pure, real counting logic -- the one real number this file computes
/// itself (the other four preview numbers all come from the already-
/// real `WeekSummaryData`, fetched once by `you_screen.dart` and reused
/// here, never re-derived). A real half-open window `[now, now+days)`,
/// matching `calendar_sync_test.dart`'s own already-hand-verified
/// half-open boundary convention for this exact table.
int countEventsWithinDays(List<CalendarMirrorData> events, DateTime now, int days) {
  final until = now.add(Duration(days: days));
  return events.where((event) => !event.startTime.isBefore(now) && event.startTime.isBefore(until)).length;
}

/// Pure, real pluralization for the Calendar preview card.
String formatCalendarPreview(int eventsThisWeek) {
  if (eventsThisWeek == 0) return 'Nothing scheduled this week';
  return eventsThisWeek == 1 ? '1 event this week' : '$eventsThisWeek events this week';
}
