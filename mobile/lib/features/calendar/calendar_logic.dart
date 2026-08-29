// This file's job is DISPLAY FORMATTING AND ORDERING ONLY (the same
// discipline `waiting_on_logic.dart` already establishes) -- it operates
// directly on Drift's own generated `CalendarMirrorData` (from
// `db/database.dart`'s real `CalendarMirror` table), deliberately not
// wrapping it in a parallel display type: unlike `WaitingOnItem` (built
// from a raw HTTP JSON payload with no existing Dart shape to reuse),
// `CalendarMirrorData` already IS the real, natural shape here, generated
// directly from the real table `calendar_sync.dart` writes into.
//
// RESOLVED, a real, disclosed correction (Meeting-Load Defense session):
// this docstring previously claimed "dart test genuinely works for this
// file's own tests," reasoning only that `drift` itself has no Flutter
// import -- a real, unverified claim, never actually run before being
// stated confidently. Directly verified now, and it's wrong: `db/
// database.dart` (imported here for `CalendarMirrorData`) itself imports
// `package:sqlite3_flutter_libs`/`package:path_provider`, both real
// Flutter plugin packages despite the former's name -- confirmed live,
// `dart test` fails to even load this file with the same real Dart-SDK-
// vs-Flutter-SDK errors `calendar_sync_test.dart`'s own header already
// documents for the identical underlying reason. `flutter test` is the
// real, confirmed-working command for this file too.
//
// No `intl` package dependency exists anywhere in this project
// (confirmed by direct search before writing this file) -- every date/
// time format elsewhere in this codebase (`finance_logic.dart`'s
// `formatCurrency`/`formatInterval`) is hand-rolled plain Dart, so this
// file follows the same established convention rather than introducing
// a new dependency for two small formatting functions.

import 'package:quorum_mobile/db/database.dart';

/// Soonest-first -- the natural real ordering for a list of upcoming
/// events, the opposite of `waiting_on_logic.dart`'s own "oldest first"
/// (waiting-on staleness gets worse with age; an upcoming event's own
/// urgency is about which one happens SOONEST). Returns a genuine copy;
/// the input list is never mutated.
List<CalendarMirrorData> sortByStartTime(List<CalendarMirrorData> events) {
  final sorted = List<CalendarMirrorData>.from(events);
  sorted.sort((a, b) => a.startTime.compareTo(b.startTime));
  return sorted;
}

const List<String> _weekdayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const List<String> _monthNames = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

/// A real, calendar-DAY comparison (year/month/day only) -- never a
/// 24-hour-duration comparison, which would wrongly call a meeting at
/// 11pm tonight and one at 1am tomorrow "the same day away" or vice
/// versa depending on the current moment. Made public (Meeting-Load
/// Defense) -- `meeting_load_logic.dart` reuses this exact real
/// day-boundary rule to group real synced events by calendar day,
/// never a second, parallel definition of "same day."
bool isSameCalendarDay(DateTime a, DateTime b) {
  return a.year == b.year && a.month == b.month && a.day == b.day;
}

/// "Today" / "Tomorrow" for the two real, common near-term cases, else a
/// real, unambiguous "Wed, Aug 26" -- never a bare "Aug 26" (a weekday
/// name is genuinely more useful for near-term planning) and never a
/// relative "in 3 days" past tomorrow (ambiguous once a week or more
/// away, and this project's own `waiting_on_logic.dart` already
/// establishes the same "don't manufacture false precision" restraint
/// for its own staleness labels).
String formatEventDayLabel(DateTime start, DateTime now) {
  final today = DateTime(now.year, now.month, now.day);
  final tomorrow = today.add(const Duration(days: 1));
  if (isSameCalendarDay(start, today)) return 'Today';
  if (isSameCalendarDay(start, tomorrow)) return 'Tomorrow';
  final weekday = _weekdayNames[start.weekday - 1];
  final month = _monthNames[start.month - 1];
  return '$weekday, $month ${start.day}';
}

/// A real, hand-rolled 12-hour clock format ("2:00 PM", "12:00 AM" for
/// real midnight, "12:00 PM" for real noon -- the two real edge cases a
/// naive `hour % 12` gets wrong if not handled explicitly, hand-verified
/// here: `hour=0` -> `12`, `hour=12` -> `12`, everything else -> `hour %
/// 12`).
String _formatClockTime(DateTime time) {
  final hour24 = time.hour;
  final period = hour24 < 12 ? 'AM' : 'PM';
  final hour12 = hour24 == 0 || hour24 == 12 ? 12 : hour24 % 12;
  final minute = time.minute.toString().padLeft(2, '0');
  return '$hour12:$minute $period';
}

/// "2:00 PM – 3:00 PM" -- the real, full display string for one event's
/// own time range, reusing `_formatClockTime` for both ends.
String formatEventTimeRange(DateTime start, DateTime end) {
  return '${_formatClockTime(start)} – ${_formatClockTime(end)}';
}
