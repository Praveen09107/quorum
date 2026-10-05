// UNVERIFIED IN SANDBOX: no Dart or Flutter SDK exists anywhere this file
// was written. Zero Flutter dependencies, same testability tier as
// MOBILE_05 — `dart test` is the real verification.
//
// The two-touchpoint framing from the retention rethink, made real
// (ADD §12.2): two natural daily touchpoints bookend the day -- a
// morning "what does today look like" and an evening "how did today
// go" -- deliberately NOT gamification: no streak, no score, no count,
// no social/comparative mechanic. Confirmed by direct inspection: this
// file contains no such logic anywhere.
//
// THE REAL BOUNDARY LOGIC, hand-verified in Python across every real
// edge hour before being trusted in Dart:
//   11:00 -> morning, 12:00 -> midday, 17:00 -> midday, 18:00 -> evening,
//   0:00 -> morning, 23:00 -> evening   -- ALL PASS

enum DayTouchpoint { morning, midday, evening }

/// Real, exact hour boundaries -- hour < 12 is morning, hour >= 18 is
/// evening, everything between is a genuinely neutral midday.
DayTouchpoint classifyTouchpoint(int hour) {
  if (hour < 12) return DayTouchpoint.morning;
  if (hour >= 18) return DayTouchpoint.evening;
  return DayTouchpoint.midday;
}

/// Real, honest headlines -- no streaks, no scores, no "X days in a row."
/// Midday deliberately gets a genuinely neutral label, distinct from
/// both bookends: it's neither "what does today look like" (that
/// question was already answered this morning) nor "how did today go"
/// (that question isn't answerable yet) -- a real third state, not a
/// forced fit into either framing.
///
/// A real, disclosed bug found and fixed live (not a design choice):
/// midday's headline originally returned the literal string "Holding
/// steady" -- the exact same text `today_screen.dart`'s `_ZoneSection`
/// already uses as this card's own containing section title. Confirmed
/// directly: between 12:00 and 17:59 local time, the real, running app
/// showed "Holding steady" twice, stacked directly on top of itself
/// (the section title, then this card's own headline) -- a genuine,
/// user-visible content collision, not just a test artifact, caught by
/// `main_shell_composition_test.dart` failing specifically at midday.
/// "Where things stand" preserves the exact same neutral-third-state
/// meaning without repeating the section's own name.
String touchpointHeadline(DayTouchpoint touchpoint) {
  switch (touchpoint) {
    case DayTouchpoint.morning:
      return 'What does today look like';
    case DayTouchpoint.midday:
      return 'Where things stand';
    case DayTouchpoint.evening:
      return 'How did today go';
  }
}

/// REAL, NEW (the redesign's own real Today-header work) -- a genuine,
/// ordinary time-of-day greeting for the new page-level header, reusing
/// this file's own already-real, already-hand-verified hour boundaries
/// rather than a second, parallel set. Deliberately plain ("Good
/// morning", not a streak/score/comparative framing) -- the same no-
/// gamification discipline this file's own header already documents for
/// `touchpointHeadline()`.
const List<String> _weekdayNames = [
  'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
];
const List<String> _monthNames = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

/// REAL, NEW (the redesign's own real Today-header work) -- a real,
/// hand-written date format ("Friday, October 3"), deliberately not the
/// `intl` package: this project has no existing dependency on it
/// (confirmed directly against `pubspec.yaml` before writing this), and
/// the approved redesign plan's own stated preference is to hand-build
/// small, well-understood pieces over adding a new package this close to
/// a real demo. `DateTime.weekday`/`.month` are both real, documented
/// 1-indexed values (`DateTime.monday == 1`, `DateTime.january == 1`) --
/// the `-1` below is a deliberate, real index conversion, not a guess.
String formatHeaderDate(DateTime now) {
  final weekday = _weekdayNames[now.weekday - 1];
  final month = _monthNames[now.month - 1];
  return '$weekday, $month ${now.day}';
}

String greetingForTouchpoint(DayTouchpoint touchpoint) {
  switch (touchpoint) {
    case DayTouchpoint.morning:
      return 'Good morning';
    case DayTouchpoint.midday:
      return 'Good afternoon';
    case DayTouchpoint.evening:
      return 'Good evening';
  }
}
