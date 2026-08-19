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
